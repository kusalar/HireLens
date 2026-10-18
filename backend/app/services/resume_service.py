import io
import json
import uuid
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.models.resume import (
    Resume,
    ResumeParseRun,
    ResumeExtractedProfile,
    ResumeEvidence,
)
from app.models.candidate import (
    Candidate,
    CandidateSkill,
    CandidateExperience,
    CandidateEducation,
)
from app.models.entities import User, AuditLog
from app.models.enums import (
    ResumeProcessingStatus,
    VerificationStatus,
    RecruiterReviewStatus,
    ParseRunStatus,
    CandidateProfileStatus,
)
from app.models.base import utc_now
from app.repositories.resume_repo import ResumeRepository
from app.services.storage_service import (
    get_storage_provider,
    validate_resume_file,
    generate_storage_key,
)
from app.services.document_extraction_service import DocumentExtractionService
from app.services.ai_provider_service import (
    get_ai_provider,
    ResumeExtractionResult,
)
from app.schemas.resume import (
    ResumeRead,
    FileUploadResult,
    BulkUploadResponse,
    ResumeListResponse,
    ResumeDetailResponse,
    ResumeExtractedProfileRead,
    ResumeExtractedProfileUpdate,
    ResumeEvidenceRead,
    ResumeEvidenceUpdate,
    ResumeParseRunRead,
    ResumeAssociateCandidateRequest,
    CandidateMatchSuggestion,
    ResumeExtractionSchema,
)


def is_redis_available(host: str = "127.0.0.1", port: int = 6379, timeout: float = 0.05) -> bool:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        err = s.connect_ex((host, port))
        s.close()
        return err == 0
    except Exception:
        return False


class ResumeService:
    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id
        self.repo = ResumeRepository(db, agency_id)
        self.storage = get_storage_provider()
        self.extraction_service = DocumentExtractionService()
        self.ai_provider = get_ai_provider()

    def _record_audit(
        self,
        user_id: Optional[uuid.UUID],
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
        details: Optional[dict] = None,
    ):
        details_str = json.dumps(details) if isinstance(details, dict) else (str(details) if details else None)
        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            details=details_str,
        )
        self.db.add(audit)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

    def upload_single_resume(
        self,
        content: bytes,
        original_filename: str,
        current_user: User,
        reraise_validation: bool = False,
    ) -> Tuple[Optional[Resume], bool, Optional[str], Optional[uuid.UUID]]:
        """
        Validates, stores, and registers a single resume.
        Returns: (resume_obj, is_duplicate, error_message, existing_resume_id)
        """
        try:
            mime_type, ext, sha256_hash = validate_resume_file(content, original_filename)
        except HTTPException as he:
            if reraise_validation:
                raise he
            return None, False, he.detail, None
        except Exception as e:
            if reraise_validation:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            return None, False, f"Validation failure: {str(e)}", None

        # Duplicate check within agency
        existing = self.repo.get_by_sha256(sha256_hash)
        if existing:
            return existing, True, f"Duplicate file detected. Already uploaded as '{existing.original_filename}'.", existing.id

        # Generate secure storage key (never use original filename)
        storage_key, stored_filename = generate_storage_key(self.agency_id, ext)

        try:
            self.storage.save(content, storage_key)
        except Exception as e:
            return None, False, f"Failed to persist file: {str(e)}", None

        # Create Resume record
        resume = Resume(
            agency_id=self.agency_id,
            uploaded_by=current_user.id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            storage_key=storage_key,
            mime_type=mime_type,
            file_size=len(content),
            sha256_hash=sha256_hash,
            processing_status=ResumeProcessingStatus.QUEUED,
            upload_status="COMPLETED",
        )
        from sqlalchemy.exc import IntegrityError
        try:
            created_resume = self.repo.create(resume)
        except IntegrityError:
            self.db.rollback()
            try:
                self.storage.delete(storage_key)
            except Exception:
                pass
            existing = self.repo.get_by_sha256(sha256_hash)
            if existing:
                return existing, True, f"Duplicate file detected. Already uploaded as '{existing.original_filename}'.", existing.id
            return None, False, "Concurrent duplicate upload conflict. Please retry.", None

        self._record_audit(
            user_id=current_user.id,
            action="RESUME_UPLOADED",
            resource_type="Resume",
            resource_id=created_resume.id,
            details={"original_filename": original_filename, "file_size": len(content)},
        )

        # Trigger processing (async background or worker)
        self._dispatch_processing(created_resume.id)

        return created_resume, False, None, None

    def bulk_upload_resumes(
        self,
        files: List[Tuple[str, bytes]],
        current_user: User,
    ) -> BulkUploadResponse:
        results: List[FileUploadResult] = []
        successful_count = 0
        failed_count = 0
        duplicate_count = 0

        for original_filename, content in files:
            resume, is_dup, error, existing_id = self.upload_single_resume(
                content=content,
                original_filename=original_filename,
                current_user=current_user,
            )
            if is_dup:
                duplicate_count += 1
                results.append(
                    FileUploadResult(
                        filename=original_filename,
                        status="DUPLICATE",
                        existing_resume_id=existing_id,
                        error=error,
                    )
                )
            elif error:
                failed_count += 1
                results.append(
                    FileUploadResult(
                        filename=original_filename,
                        status="REJECTED",
                        error=error,
                    )
                )
            else:
                successful_count += 1
                results.append(
                    FileUploadResult(
                        filename=original_filename,
                        status="SUCCESS",
                        resume_id=resume.id,
                        resume=ResumeRead.model_validate(resume),
                    )
                )

        return BulkUploadResponse(
            total_files=len(files),
            successful_count=successful_count,
            failed_count=failed_count,
            duplicate_count=duplicate_count,
            results=results,
        )

    def _dispatch_processing(self, resume_id: uuid.UUID):
        """
        Dispatches resume processing to background worker.
        Never blocks the upload request for AI inference or broker timeouts.
        """
        if not is_redis_available():
            return

        try:
            from app.tasks.resume_tasks import process_resume_pipeline_task
            process_resume_pipeline_task.apply_async(
                args=[str(resume_id), str(self.agency_id)],
                retry=False,
            )
        except Exception:
            # If broker is offline or unreachable, resume remains safely in QUEUED status
            pass

    def process_pipeline(self, resume_id: uuid.UUID, force: bool = False) -> Optional[Resume]:
        """
        Full idempotent pipeline:
        EXTRACT TEXT -> SCANNED DETECTION -> OCR FALLBACK -> SAVE TEXT
        -> AI STRUCTURED EXTRACTION -> VALIDATE OUTPUT -> REVIEWABLE PROFILE
        """
        resume = self.repo.get(resume_id)
        if not resume:
            return None

        # Idempotency guard: If resume is already successfully processed, skip unless forced
        if not force and resume.processing_status in (
            ResumeProcessingStatus.REVIEW_REQUIRED,
            ResumeProcessingStatus.COMPLETED,
        ):
            return resume

        try:
            return self._run_pipeline_stages(resume)
        except Exception as exc:
            try:
                latest = self.repo.get(resume_id)
                if latest:
                    self.repo.update(
                        latest,
                        {
                            "processing_status": ResumeProcessingStatus.FAILED,
                            "error_message": f"Unexpected processing error: {str(exc)}",
                        },
                    )
            except Exception:
                self.db.rollback()
            raise exc

    def _run_pipeline_stages(self, resume: Resume) -> Resume:
        # Step 1: Text Extraction
        self.repo.update(resume, {"processing_status": ResumeProcessingStatus.EXTRACTING})

        try:
            file_bytes = self.storage.get(resume.storage_key)
        except Exception as e:
            self.repo.update(
                resume,
                {
                    "processing_status": ResumeProcessingStatus.FAILED,
                    "error_message": f"Storage retrieval error: {str(e)}",
                },
            )
            return resume

        extraction_result = self.extraction_service.extract_document(file_bytes, resume.mime_type)

        if not extraction_result.success:
            self.repo.update(
                resume,
                {
                    "processing_status": ResumeProcessingStatus.FAILED,
                    "error_message": extraction_result.error_message or "Extraction failed.",
                    "page_count": extraction_result.page_count,
                },
            )
            # Record failed parse run
            failed_run = ResumeParseRun(
                resume_id=resume.id,
                agency_id=self.agency_id,
                provider="extraction_service",
                model_name=extraction_result.extraction_method,
                extraction_method=extraction_result.extraction_method,
                status=ParseRunStatus.FAILED,
                error_code="EXTRACTION_FAILED",
                error_message=extraction_result.error_message,
                completed_at=utc_now(),
            )
            self.repo.create_parse_run(failed_run)
            return resume

        # Save extracted text
        self.repo.update(
            resume,
            {
                "extracted_text": extraction_result.full_text,
                "page_count": extraction_result.page_count,
                "processing_status": ResumeProcessingStatus.EXTRACTED,
                "error_message": None,
            },
        )

        # Step 2: AI Structured Extraction
        self.repo.update(resume, {"processing_status": ResumeProcessingStatus.PARSING})

        model_info = self.ai_provider.get_model_info()
        parse_run = ResumeParseRun(
            resume_id=resume.id,
            agency_id=self.agency_id,
            provider=model_info.provider_name,
            model_name=model_info.model_name,
            model_version=model_info.model_version,
            extraction_method=f"{extraction_result.extraction_method}+ai",
            status=ParseRunStatus.RUNNING,
            started_at=utc_now(),
        )
        created_run = self.repo.create_parse_run(parse_run)

        ai_result: ResumeExtractionResult = self.ai_provider.extract_resume_profile(
            extraction_result.full_text
        )

        if not ai_result.success:
            created_run.status = ParseRunStatus.FAILED
            created_run.completed_at = utc_now()
            created_run.error_code = ai_result.error_code or "AI_EXTRACTION_FAILED"
            created_run.error_message = ai_result.error_message
            created_run.processing_duration_ms = ai_result.duration_ms
            self.db.commit()

            # If AI is unavailable, we leave the resume in EXTRACTED state with clear note
            if ai_result.error_code in ("AI_UNAVAILABLE", "AI_NOT_CONFIGURED"):
                self.repo.update(
                    resume,
                    {
                        "processing_status": ResumeProcessingStatus.EXTRACTED,
                        "error_message": f"AI Parsing Unavailable: {ai_result.error_message}",
                    },
                )
            else:
                self.repo.update(
                    resume,
                    {
                        "processing_status": ResumeProcessingStatus.FAILED,
                        "error_message": ai_result.error_message,
                    },
                )
            return resume

        # AI Extraction Succeeded
        created_run.status = ParseRunStatus.COMPLETED
        created_run.completed_at = utc_now()
        created_run.processing_duration_ms = ai_result.duration_ms
        self.db.commit()

        schema_data: ResumeExtractionSchema = ai_result.data
        extracted_profile = ResumeExtractedProfile(
            resume_id=resume.id,
            parse_run_id=created_run.id,
            agency_id=self.agency_id,
            extracted_name=schema_data.candidate_name,
            extracted_email=schema_data.email,
            extracted_phone=schema_data.phone,
            extracted_location=schema_data.location,
            extracted_current_title=schema_data.current_title,
            extracted_summary=schema_data.professional_summary,
            extracted_experience_months=schema_data.total_experience_months,
            structured_extraction_json=schema_data.model_dump_json(),
            overall_confidence=schema_data.confidence_score,
            recruiter_review_status=RecruiterReviewStatus.PENDING,
        )
        self.repo.create_extracted_profile(extracted_profile)

        # Create Evidences for Skills
        for skill in schema_data.skills:
            if skill.evidence:
                evidence = ResumeEvidence(
                    parse_run_id=created_run.id,
                    resume_id=resume.id,
                    agency_id=self.agency_id,
                    field_name=f"skill:{skill.skill_name}",
                    extracted_value=skill.skill_name,
                    source_page=skill.source_page,
                    source_excerpt=skill.evidence,
                    confidence=schema_data.confidence_score,
                    verification_status=VerificationStatus.UNREVIEWED,
                )
                self.repo.create_evidence(evidence)

        # Create Evidences for Experiences
        for exp in schema_data.experiences:
            if exp.evidence:
                evidence = ResumeEvidence(
                    parse_run_id=created_run.id,
                    resume_id=resume.id,
                    agency_id=self.agency_id,
                    field_name=f"experience:{exp.company}",
                    extracted_value=f"{exp.job_title} at {exp.company}",
                    source_page=exp.source_page,
                    source_excerpt=exp.evidence,
                    confidence=schema_data.confidence_score,
                    verification_status=VerificationStatus.UNREVIEWED,
                )
                self.repo.create_evidence(evidence)

        # Create Evidences for Education
        for edu in schema_data.educations:
            if edu.evidence:
                evidence = ResumeEvidence(
                    parse_run_id=created_run.id,
                    resume_id=resume.id,
                    agency_id=self.agency_id,
                    field_name=f"education:{edu.institution}",
                    extracted_value=f"{edu.qualification} in {edu.field_of_study or ''}".strip(),
                    source_page=edu.source_page,
                    source_excerpt=edu.evidence,
                    confidence=schema_data.confidence_score,
                    verification_status=VerificationStatus.UNREVIEWED,
                )
                self.repo.create_evidence(evidence)

        # Transition status to REVIEW_REQUIRED
        self.repo.update(
            resume,
            {
                "processing_status": ResumeProcessingStatus.REVIEW_REQUIRED,
                "error_message": None,
            },
        )
        return resume

    def get_resume_detail(self, resume_id: uuid.UUID) -> ResumeDetailResponse:
        resume = self.repo.get_detail(resume_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or access denied.",
            )

        # Check if processing has been stuck / worker crashed (timeout: 5 minutes)
        from datetime import datetime, timezone, timedelta
        if resume.processing_status in (ResumeProcessingStatus.EXTRACTING, ResumeProcessingStatus.PARSING):
            updated_at = resume.updated_at
            if updated_at:
                tz_aware = updated_at if updated_at.tzinfo else updated_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - tz_aware > timedelta(minutes=5):
                    resume = self.repo.update(
                        resume,
                        {
                            "processing_status": ResumeProcessingStatus.FAILED,
                            "error_message": "Processing timed out (worker process may have stopped). You can retry processing.",
                        },
                    )

        latest_profile = self.repo.get_latest_extracted_profile(resume_id)
        parse_runs = self.repo.list_parse_runs(resume_id)
        evidences = self.repo.list_evidences(resume_id)

        # Find potential matching existing candidates (without auto-merging!)
        possible_matches: List[CandidateMatchSuggestion] = []
        if latest_profile:
            match_conds = []
            if latest_profile.extracted_email:
                match_conds.append(Candidate.email == latest_profile.extracted_email)
            if latest_profile.extracted_name and len(latest_profile.extracted_name.strip()) > 2:
                match_conds.append(Candidate.full_name.ilike(f"%{latest_profile.extracted_name.strip()}%"))

            if match_conds:
                cand_stmt = select(Candidate).where(
                    Candidate.agency_id == self.agency_id,
                    or_(*match_conds),
                ).limit(5)
                matching_cands = list(self.db.scalars(cand_stmt).all())
                for mc in matching_cands:
                    reason = []
                    if latest_profile.extracted_email and mc.email == latest_profile.extracted_email:
                        reason.append("Matching email address")
                    if latest_profile.extracted_name and latest_profile.extracted_name.lower() in mc.full_name.lower():
                        reason.append("Matching candidate name")
                    possible_matches.append(
                        CandidateMatchSuggestion(
                            candidate_id=mc.id,
                            full_name=mc.full_name,
                            email=mc.email,
                            current_title=mc.current_title,
                            match_reason=", ".join(reason) or "Partial profile match",
                        )
                    )

        profile_read = None
        if latest_profile:
            structured_data = None
            if latest_profile.structured_extraction_json:
                try:
                    structured_data = ResumeExtractionSchema.model_validate_json(
                        latest_profile.structured_extraction_json
                    )
                except Exception:
                    pass
            profile_read = ResumeExtractedProfileRead(
                id=latest_profile.id,
                resume_id=latest_profile.resume_id,
                parse_run_id=latest_profile.parse_run_id,
                agency_id=latest_profile.agency_id,
                extracted_name=latest_profile.extracted_name,
                extracted_email=latest_profile.extracted_email,
                extracted_phone=latest_profile.extracted_phone,
                extracted_location=latest_profile.extracted_location,
                extracted_current_title=latest_profile.extracted_current_title,
                extracted_summary=latest_profile.extracted_summary,
                extracted_experience_months=latest_profile.extracted_experience_months,
                structured_data=structured_data,
                overall_confidence=latest_profile.overall_confidence,
                recruiter_review_status=latest_profile.recruiter_review_status,
                created_at=latest_profile.created_at,
                updated_at=latest_profile.updated_at,
            )

        resume_read = ResumeRead(
            id=resume.id,
            agency_id=resume.agency_id,
            candidate_id=resume.candidate_id,
            uploaded_by=resume.uploaded_by,
            original_filename=resume.original_filename,
            mime_type=resume.mime_type,
            file_size=resume.file_size,
            sha256_hash=resume.sha256_hash,
            page_count=resume.page_count,
            language=resume.language,
            processing_status=resume.processing_status,
            upload_status=resume.upload_status,
            error_message=resume.error_message,
            created_at=resume.created_at,
            updated_at=resume.updated_at,
            candidate_name=resume.candidate.full_name if resume.candidate else None,
        )

        return ResumeDetailResponse(
            resume=resume_read,
            current_profile=profile_read,
            parse_runs=[ResumeParseRunRead.model_validate(pr) for pr in parse_runs],
            evidences=[ResumeEvidenceRead.model_validate(ev) for ev in evidences],
            possible_matching_candidates=possible_matches,
        )

    def download_resume(self, resume_id: uuid.UUID, current_user: User) -> Tuple[bytes, str, str]:
        resume = self.repo.get(resume_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or access denied.",
            )

        # Self-heal ephemeral demo resume if missing from local container disk
        if not self.storage.exists(resume.storage_key):
            try:
                from app.services.demo_service import self_heal_demo_resume
                self_heal_demo_resume(self.db, resume)
            except Exception as e:
                print(f"[DEMO_SELF_HEAL_WARN] Could not self-heal demo resume: {e}")

        content = self.storage.get(resume.storage_key)

        self._record_audit(
            user_id=current_user.id,
            action="RESUME_DOWNLOADED",
            resource_type="Resume",
            resource_id=resume.id,
            details={"original_filename": resume.original_filename},
        )
        return content, resume.original_filename, resume.mime_type

    def delete_resume(self, resume_id: uuid.UUID, current_user: User) -> bool:
        resume = self.repo.get(resume_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or access denied.",
            )

        # Delete physical file from storage
        self.storage.delete(resume.storage_key)

        # Delete database record (cascades)
        self.repo.delete(resume.id)

        self._record_audit(
            user_id=current_user.id,
            action="RESUME_DELETED",
            resource_type="Resume",
            resource_id=resume_id,
            details={"original_filename": resume.original_filename},
        )
        return True

    def retry_processing(self, resume_id: uuid.UUID, current_user: User) -> Resume:
        resume = self.repo.get(resume_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or access denied.",
            )

        self.repo.update(
            resume,
            {
                "processing_status": ResumeProcessingStatus.QUEUED,
                "error_message": None,
            },
        )

        self._record_audit(
            user_id=current_user.id,
            action="RESUME_PROCESSING_RETRIED",
            resource_type="Resume",
            resource_id=resume.id,
        )

        self._dispatch_processing(resume.id)
        return resume

    def update_extracted_profile(
        self,
        resume_id: uuid.UUID,
        update_dto: ResumeExtractedProfileUpdate,
        current_user: User,
    ) -> ResumeExtractedProfile:
        profile = self.repo.get_latest_extracted_profile(resume_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No extracted profile exists for this resume to update.",
            )

        updates = {}
        for k, v in update_dto.model_dump(exclude_unset=True).items():
            if k == "structured_data" and v is not None:
                updates["structured_extraction_json"] = json.dumps(v)
            else:
                updates[k] = v

        updates["recruiter_review_status"] = update_dto.recruiter_review_status or RecruiterReviewStatus.CORRECTED
        updated = self.repo.update_extracted_profile(profile, updates)

        self._record_audit(
            user_id=current_user.id,
            action="RESUME_PROFILE_CORRECTED",
            resource_type="ResumeExtractedProfile",
            resource_id=profile.id,
        )
        return updated

    def update_evidence(
        self,
        resume_id: uuid.UUID,
        evidence_id: uuid.UUID,
        update_dto: ResumeEvidenceUpdate,
        current_user: User,
    ) -> ResumeEvidence:
        evidence = self.repo.get_evidence(evidence_id)
        if not evidence or evidence.resume_id != resume_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence record not found.",
            )

        updates = {"verification_status": update_dto.verification_status}
        if update_dto.corrected_value is not None:
            updates["corrected_value"] = update_dto.corrected_value
            if update_dto.verification_status == VerificationStatus.UNREVIEWED:
                updates["verification_status"] = VerificationStatus.CORRECTED

        updated = self.repo.update_evidence(evidence, updates)

        self._record_audit(
            user_id=current_user.id,
            action="RESUME_EVIDENCE_VERIFIED",
            resource_type="ResumeEvidence",
            resource_id=evidence.id,
            details={"status": update_dto.verification_status.value},
        )
        return updated

    def associate_candidate(
        self,
        resume_id: uuid.UUID,
        req: ResumeAssociateCandidateRequest,
        current_user: User,
    ) -> Candidate:
        resume = self.repo.get(resume_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found or access denied.",
            )

        if req.candidate_id:
            # Associate with existing candidate strictly within this agency
            cand_stmt = select(Candidate).where(
                Candidate.id == req.candidate_id,
                Candidate.agency_id == self.agency_id,
            )
            candidate = self.db.scalars(cand_stmt).first()
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Specified candidate not found in agency.",
                )

            resume.candidate_id = candidate.id
            resume.processing_status = ResumeProcessingStatus.COMPLETED
            self.db.commit()

            self._record_audit(
                user_id=current_user.id,
                action="CANDIDATE_ASSOCIATED_WITH_RESUME",
                resource_type="Resume",
                resource_id=resume.id,
                details={"candidate_id": str(candidate.id)},
            )
            return candidate

        elif req.create_new_candidate:
            # Create a brand new confirmed candidate profile from extracted data
            profile = self.repo.get_latest_extracted_profile(resume_id)
            name = req.candidate_name or (profile.extracted_name if profile else None) or resume.original_filename
            email = req.candidate_email or (profile.extracted_email if profile else None)
            phone = req.candidate_phone or (profile.extracted_phone if profile else None)
            title = req.candidate_title or (profile.extracted_current_title if profile else None)
            loc = req.candidate_location or (profile.extracted_location if profile else None)
            summary = req.candidate_summary or (profile.extracted_summary if profile else None)
            exp_months = req.total_experience_months or (profile.extracted_experience_months if profile else 0) or 0

            candidate = Candidate(
                agency_id=self.agency_id,
                full_name=name,
                email=email,
                phone_encrypted=phone,
                current_title=title,
                current_location=loc,
                professional_summary=summary,
                total_experience_months=exp_months,
                profile_status=CandidateProfileStatus.ACTIVE,
                source="RESUME_UPLOAD",
            )
            self.db.add(candidate)
            self.db.flush()

            # Transfer verified/extracted skills, experiences, educations from structured JSON
            if profile and profile.structured_extraction_json:
                try:
                    structured = ResumeExtractionSchema.model_validate_json(
                        profile.structured_extraction_json
                    )
                    for sk in structured.skills:
                        c_skill = CandidateSkill(
                            candidate_id=candidate.id,
                            skill_name=sk.skill_name,
                            normalized_skill=sk.skill_name.lower().strip(),
                            proficiency=sk.proficiency,
                            evidence=sk.evidence,
                            source_page=sk.source_page,
                        )
                        self.db.add(c_skill)

                    for ex in structured.experiences:
                        c_exp = CandidateExperience(
                            candidate_id=candidate.id,
                            company=ex.company,
                            job_title=ex.job_title,
                            start_date=ex.start_date,
                            end_date=ex.end_date,
                            description=ex.description,
                        )
                        self.db.add(c_exp)

                    for ed in structured.educations:
                        c_edu = CandidateEducation(
                            candidate_id=candidate.id,
                            institution=ed.institution,
                            qualification=ed.qualification,
                            field_of_study=ed.field_of_study,
                            start_year=ed.start_year,
                            end_year=ed.end_year,
                        )
                        self.db.add(c_edu)
                except Exception:
                    pass

            resume.candidate_id = candidate.id
            resume.processing_status = ResumeProcessingStatus.COMPLETED
            if profile:
                profile.recruiter_review_status = RecruiterReviewStatus.VERIFIED

            self.db.commit()
            self.db.refresh(candidate)

            self._record_audit(
                user_id=current_user.id,
                action="NEW_CANDIDATE_CREATED_FROM_RESUME",
                resource_type="Candidate",
                resource_id=candidate.id,
                details={"resume_id": str(resume.id)},
            )
            return candidate

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must specify candidate_id or set create_new_candidate=True.",
            )
