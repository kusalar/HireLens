import json
import time
import uuid
from typing import Optional, List, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.matching import JobMatchRun, JobMatchResult, MatchEvidence
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.resume import Resume, ResumeExtractedProfile, ResumeEvidence
from app.models.entities import User, AuditLog
from app.models.enums import (
    JobMatchRunStatus,
    CandidateProfileStatus,
    MatchStatus,
    VerificationStatus,
)
from app.repositories.matching_repo import JobMatchRepository
from app.repositories.job_repo import JobRepository
from app.repositories.candidate_repo import CandidateRepository
from app.services.matching_engine import DeterministicMatchingEngine, ScoringConfig
from app.services.match_explanation_service import MatchExplanationService
from app.models.base import utc_now


import hashlib
from datetime import timedelta

def compute_source_fingerprint(
    job: Job,
    candidate: Candidate,
    scoring_version: str = "v1.0",
    cand_resumes: Optional[List[Resume]] = None,
) -> str:
    """
    Computes a deterministic SHA-256 fingerprint representing the exact source state:
    - Job requirements (ID, type, requirement_text, importance_weight, is_mandatory)
    - Candidate state (ID, title, total_experience_months)
    - Candidate confirmed resumes (ID, parsing_status, file_hash, updated_at)
    - Scoring version
    """
    hasher = hashlib.sha256()
    hasher.update(str(job.id).encode("utf-8"))
    hasher.update((job.title or "").encode("utf-8"))

    reqs = sorted(job.requirements or [], key=lambda r: str(r.id))
    for r in reqs:
        req_token = f"{r.id}:{r.requirement_type}:{getattr(r, 'requirement_text', '')}:{getattr(r, 'importance_weight', 1.0)}:{getattr(r, 'is_mandatory', True)}"
        hasher.update(req_token.encode("utf-8"))

    hasher.update(str(candidate.id).encode("utf-8"))
    hasher.update((candidate.current_title or "").encode("utf-8"))
    hasher.update(str(getattr(candidate, "total_experience_months", 0) or 0).encode("utf-8"))

    if cand_resumes:
        for res in sorted(cand_resumes, key=lambda r: str(r.id)):
            res_token = f"{res.id}:{res.parsing_status}:{getattr(res, 'file_hash', '')}:{res.updated_at.isoformat() if getattr(res, 'updated_at', None) else ''}"
            hasher.update(res_token.encode("utf-8"))

    hasher.update(scoring_version.encode("utf-8"))
    return hasher.hexdigest()


def select_candidate_resumes(db: Session, agency_id: uuid.UUID, candidate_id: uuid.UUID) -> List[Resume]:
    """
    Deterministic Resume Selection Policy:
    1. Filter only confirmed candidate resumes belonging to this agency (Resume.candidate_id == cand.id).
       Unassociated resumes are strictly excluded.
    2. Sort deterministically with status priority:
       - Resumes with COMPLETED or REVIEW_REQUIRED or EXTRACTED have highest priority.
       - Tie-breaker: most recently created/updated (created_at desc).
    """
    res_stmt = (
        select(Resume)
        .where(
            Resume.candidate_id == candidate_id,
            Resume.agency_id == agency_id,
        )
        .order_by(Resume.created_at.desc())
    )
    raw_resumes = list(db.scalars(res_stmt).all())
    if not raw_resumes:
        return []

    status_weights = {
        "COMPLETED": 4,
        "EXTRACTED": 3,
        "REVIEW_REQUIRED": 2,
        "PROCESSING": 1,
        "PENDING": 1,
        "FAILED": 0,
    }
    raw_resumes.sort(
        key=lambda r: (
            status_weights.get(r.parsing_status.value if hasattr(r.parsing_status, "value") else str(r.parsing_status), 0),
            r.created_at.timestamp() if r.created_at else 0,
        ),
        reverse=True,
    )
    return raw_resumes


class MatchingService:
    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id
        self.repo = JobMatchRepository(db, agency_id)
        self.job_repo = JobRepository(db, agency_id)
        self.candidate_repo = CandidateRepository(db, agency_id)
        self.matching_engine = DeterministicMatchingEngine()
        self.explanation_service = MatchExplanationService()

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

    def _recover_stuck_runs(self, job_id: uuid.UUID) -> None:
        """
        Detects and recovers stuck matching runs in PROCESSING status older than 10 minutes.
        """
        stuck_threshold = utc_now() - timedelta(minutes=10)
        stmt = (
            select(JobMatchRun)
            .where(
                JobMatchRun.job_id == job_id,
                JobMatchRun.agency_id == self.agency_id,
                JobMatchRun.status == JobMatchRunStatus.PROCESSING,
            )
        )
        active_runs = list(self.db.scalars(stmt).all())
        for run in active_runs:
            if run.started_at and run.started_at < stuck_threshold:
                run.status = JobMatchRunStatus.FAILED
                run.completed_at = utc_now()
                self.db.commit()

    def run_matching_for_job(
        self, job_id: uuid.UUID, current_user: User
    ) -> JobMatchRun:
        """
        Executes a deterministic matching run for a job across all active agency candidates.
        Preserves previous run history rather than overwriting.
        """
        job = self.job_repo.get_detail(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or access denied.",
            )

        # Check and recover stuck runs
        self._recover_stuck_runs(job_id)

        # Ensure no active concurrent matching run is underway
        active_stmt = (
            select(JobMatchRun)
            .where(
                JobMatchRun.job_id == job_id,
                JobMatchRun.agency_id == self.agency_id,
                JobMatchRun.status == JobMatchRunStatus.PROCESSING,
            )
        )
        if self.db.scalars(active_stmt).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A matching run is already in progress for this job. Please wait for it to complete.",
            )

        start_time = time.time()

        # Fetch all active candidates scoped strictly to this agency
        cand_stmt = (
            select(Candidate)
            .where(
                Candidate.agency_id == self.agency_id,
                Candidate.profile_status == CandidateProfileStatus.ACTIVE,
            )
        )
        candidates = list(self.db.scalars(cand_stmt).all())

        # Initialize matching run record
        run = JobMatchRun(
            agency_id=self.agency_id,
            job_id=job_id,
            initiated_by=current_user.id,
            scoring_version=self.matching_engine.config.scoring_version,
            matching_provider="deterministic+semantic",
            embedding_model="hirelens-subword-v1",
            candidate_count=len(candidates),
            completed_count=0,
            failed_count=0,
            status=JobMatchRunStatus.PROCESSING,
            started_at=utc_now(),
        )
        created_run = self.repo.create_run(run)

        completed_count = 0
        failed_count = 0

        for cand in candidates:
            try:
                with self.db.begin_nested():
                    # Deterministic candidate resume selection
                    cand_resumes = select_candidate_resumes(self.db, self.agency_id, cand.id)

                    latest_profile = None
                    resume_evidences = []
                    if cand_resumes:
                        primary_resume = cand_resumes[0]
                        prof_stmt = (
                            select(ResumeExtractedProfile)
                            .where(
                                ResumeExtractedProfile.resume_id == primary_resume.id,
                                ResumeExtractedProfile.agency_id == self.agency_id,
                            )
                            .order_by(ResumeExtractedProfile.created_at.desc())
                        )
                        latest_profile = self.db.scalars(prof_stmt).first()

                        ev_stmt = (
                            select(ResumeEvidence)
                            .where(
                                ResumeEvidence.resume_id == primary_resume.id,
                                ResumeEvidence.agency_id == self.agency_id,
                            )
                        )
                        resume_evidences = list(self.db.scalars(ev_stmt).all())

                    # 1. Deterministic score calculation
                    scoring = self.matching_engine.score_candidate_for_job(
                        job=job,
                        candidate=cand,
                        resumes=cand_resumes,
                        latest_extracted_profile=latest_profile,
                        resume_evidences=resume_evidences,
                    )

                    # 2. AI explanation grounded strictly in verified evidence
                    explanation = self.explanation_service.generate_explanation(
                        job=job,
                        candidate=cand,
                        scoring=scoring,
                    )

                    # Compute source fingerprint
                    source_fp = compute_source_fingerprint(
                        job=job,
                        candidate=cand,
                        scoring_version=scoring.scoring_version,
                        cand_resumes=cand_resumes,
                    )

                    # 3. Persist JobMatchResult
                    result_obj = JobMatchResult(
                        agency_id=self.agency_id,
                        job_id=job.id,
                        candidate_id=cand.id,
                        match_run_id=created_run.id,
                        overall_score=scoring.overall_score,
                        required_skills_score=scoring.required_skills_score,
                        experience_score=scoring.experience_score,
                        preferred_skills_score=scoring.preferred_skills_score,
                        project_relevance_score=scoring.project_relevance_score,
                        other_criteria_score=scoring.other_criteria_score,
                        matched_requirements_count=scoring.matched_requirements_count,
                        partial_requirements_count=scoring.partial_requirements_count,
                        missing_requirements_count=scoring.missing_requirements_count,
                        needs_verification_count=scoring.needs_verification_count,
                        explanation=explanation.summary,
                        strengths=json.dumps(explanation.strengths),
                        skill_gaps=json.dumps(explanation.skill_gaps),
                        verification_items=json.dumps(explanation.verification_items),
                        suggested_questions=json.dumps(explanation.suggested_interview_questions),
                        scoring_version=scoring.scoring_version,
                        source_fingerprint=source_fp,
                        status="COMPLETED",
                    )
                    self.db.add(result_obj)
                    self.db.flush()

                    # 4. Persist MatchEvidences
                    for ev_data in scoring.evidences:
                        ev_obj = MatchEvidence(
                            agency_id=self.agency_id,
                            match_result_id=result_obj.id,
                            job_requirement_id=ev_data.job_requirement_id,
                            criterion_name=ev_data.criterion_name,
                            criterion_type=ev_data.criterion_type,
                            expected_requirement=ev_data.expected_requirement,
                            evidence_status=ev_data.evidence_status,
                            candidate_evidence=ev_data.candidate_evidence,
                            source_resume_id=ev_data.source_resume_id,
                            source_page=ev_data.source_page,
                            source_excerpt=ev_data.source_excerpt,
                            semantic_similarity=ev_data.semantic_similarity,
                            score_contribution=ev_data.score_contribution,
                            explanation=ev_data.explanation,
                            verification_status=ev_data.verification_status,
                        )
                        self.db.add(ev_obj)

                completed_count += 1
            except Exception:
                failed_count += 1

        duration_ms = int((time.time() - start_time) * 1000)
        final_status = (
            JobMatchRunStatus.COMPLETED
            if failed_count == 0
            else (
                JobMatchRunStatus.PARTIALLY_COMPLETED
                if completed_count > 0
                else JobMatchRunStatus.FAILED
            )
        )

        created_run.completed_count = completed_count
        created_run.failed_count = failed_count
        created_run.status = final_status
        created_run.completed_at = utc_now()
        created_run.duration_ms = duration_ms
        self.db.commit()
        self.db.refresh(created_run)

        self._record_audit(
            user_id=current_user.id,
            action="JOB_MATCHING_RUN_EXECUTED",
            resource_type="JobMatchRun",
            resource_id=created_run.id,
            details={
                "job_id": str(job_id),
                "candidates_processed": completed_count,
                "duration_ms": duration_ms,
            },
        )

        return created_run

    def get_run_status(self, run_id: uuid.UUID) -> JobMatchRun:
        run = self.repo.get_run(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matching run not found or access denied.",
            )
        return run

    def get_candidate_match_detail(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> JobMatchResult:
        result = self.repo.get_result_by_candidate(job_id, candidate_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match result not found for this candidate and job.",
            )
        return result

    def list_matches_for_job(
        self,
        job_id: uuid.UUID,
        min_score: Optional[float] = None,
        search: Optional[str] = None,
        run_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[JobMatchResult], int, Optional[JobMatchRun]]:
        job = self.job_repo.get_detail(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or access denied.",
            )
        latest_run = self.repo.get_latest_run_for_job(job_id)
        results, total = self.repo.list_results_for_job(
            job_id=job_id,
            min_score=min_score,
            search=search,
            run_id=run_id,
            skip=skip,
            limit=limit,
        )
        return results, total, latest_run

    def list_candidate_matching_history(
        self, candidate_id: uuid.UUID, limit: int = 20
    ) -> List[JobMatchResult]:
        candidate = self.candidate_repo.get_detail(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found or access denied.",
            )
        return self.repo.list_candidate_matching_history(candidate_id=candidate_id, limit=limit)


    def refresh_explanation(
        self, result_id: uuid.UUID, current_user: User
    ) -> JobMatchResult:
        """
        Retries AI explanation generation without altering the deterministic score.
        """
        result = self.repo.get_result(result_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match result not found.",
            )

        job = self.job_repo.get_detail(result.job_id)
        candidate = self.candidate_repo.get_detail(result.candidate_id)
        if not job or not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated job or candidate record not found.",
            )

        # Build mock scoring result from existing result and evidences
        scoring_result = DeterministicMatchingEngine().score_candidate_for_job(
            job=job,
            candidate=candidate,
        )
        # Keep original stored overall score intact
        scoring_result.overall_score = result.overall_score

        new_explanation = self.explanation_service.generate_explanation(
            job=job,
            candidate=candidate,
            scoring=scoring_result,
        )

        updates = {
            "explanation": new_explanation.summary,
            "strengths": json.dumps(new_explanation.strengths),
            "skill_gaps": json.dumps(new_explanation.skill_gaps),
            "verification_items": json.dumps(new_explanation.verification_items),
            "suggested_questions": json.dumps(new_explanation.suggested_interview_questions),
        }
        updated = self.repo.update_result(result, updates)

        self._record_audit(
            user_id=current_user.id,
            action="MATCH_EXPLANATION_REFRESHED",
            resource_type="JobMatchResult",
            resource_id=result.id,
        )
        return updated

    def recalculate_result(
        self, result_id: uuid.UUID, current_user: User, scoring_version: str = "v1.0"
    ) -> JobMatchResult:
        """
        Recalculates match score using current candidate records and job requirements.
        Preserves the previous evaluation as HISTORICAL and creates an auditable new evaluation.
        """
        result = self.repo.get_result(result_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match result not found.",
            )

        job = self.job_repo.get_detail(result.job_id)
        candidate = self.candidate_repo.get_detail(result.candidate_id)
        if not job or not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated job or candidate record not found.",
            )

        # 1. Mark existing evaluation as HISTORICAL (immutable snapshot)
        result.status = "HISTORICAL"
        self.db.commit()

        # 2. Select latest confirmed resumes and evidence
        cand_resumes = select_candidate_resumes(self.db, self.agency_id, candidate.id)
        latest_profile = None
        resume_evidences = []
        if cand_resumes:
            primary_resume = cand_resumes[0]
            prof_stmt = (
                select(ResumeExtractedProfile)
                .where(
                    ResumeExtractedProfile.resume_id == primary_resume.id,
                    ResumeExtractedProfile.agency_id == self.agency_id,
                )
                .order_by(ResumeExtractedProfile.created_at.desc())
            )
            latest_profile = self.db.scalars(prof_stmt).first()

            ev_stmt = (
                select(ResumeEvidence)
                .where(
                    ResumeEvidence.resume_id == primary_resume.id,
                    ResumeEvidence.agency_id == self.agency_id,
                )
            )
            resume_evidences = list(self.db.scalars(ev_stmt).all())

        # 3. Deterministic calculation & explanation
        scoring = self.matching_engine.score_candidate_for_job(
            job=job,
            candidate=candidate,
            resumes=cand_resumes,
            latest_extracted_profile=latest_profile,
            resume_evidences=resume_evidences,
        )
        explanation = self.explanation_service.generate_explanation(
            job=job,
            candidate=candidate,
            scoring=scoring,
        )

        source_fp = compute_source_fingerprint(
            job=job,
            candidate=candidate,
            scoring_version=scoring.scoring_version,
            cand_resumes=cand_resumes,
        )

        # 4. Create new recalculation JobMatchRun
        recalc_run = JobMatchRun(
            agency_id=self.agency_id,
            job_id=job.id,
            initiated_by=current_user.id,
            scoring_version=scoring.scoring_version,
            matching_provider="deterministic+semantic",
            embedding_model="hirelens-subword-v1",
            candidate_count=1,
            completed_count=1,
            failed_count=0,
            status=JobMatchRunStatus.COMPLETED,
            started_at=utc_now(),
            completed_at=utc_now(),
            duration_ms=0,
        )
        self.db.add(recalc_run)
        self.db.flush()

        # 5. Create new JobMatchResult
        new_result = JobMatchResult(
            agency_id=self.agency_id,
            job_id=job.id,
            candidate_id=candidate.id,
            match_run_id=recalc_run.id,
            overall_score=scoring.overall_score,
            required_skills_score=scoring.required_skills_score,
            experience_score=scoring.experience_score,
            preferred_skills_score=scoring.preferred_skills_score,
            project_relevance_score=scoring.project_relevance_score,
            other_criteria_score=scoring.other_criteria_score,
            matched_requirements_count=scoring.matched_requirements_count,
            partial_requirements_count=scoring.partial_requirements_count,
            missing_requirements_count=scoring.missing_requirements_count,
            needs_verification_count=scoring.needs_verification_count,
            explanation=explanation.summary,
            strengths=json.dumps(explanation.strengths),
            skill_gaps=json.dumps(explanation.skill_gaps),
            verification_items=json.dumps(explanation.verification_items),
            suggested_questions=json.dumps(explanation.suggested_interview_questions),
            scoring_version=scoring.scoring_version,
            source_fingerprint=source_fp,
            status="COMPLETED",
        )
        self.db.add(new_result)
        self.db.flush()

        # 6. Create new MatchEvidences
        for ev_data in scoring.evidences:
            ev_obj = MatchEvidence(
                agency_id=self.agency_id,
                match_result_id=new_result.id,
                job_requirement_id=ev_data.job_requirement_id,
                criterion_name=ev_data.criterion_name,
                criterion_type=ev_data.criterion_type,
                expected_requirement=ev_data.expected_requirement,
                evidence_status=ev_data.evidence_status,
                candidate_evidence=ev_data.candidate_evidence,
                source_resume_id=ev_data.source_resume_id,
                source_page=ev_data.source_page,
                source_excerpt=ev_data.source_excerpt,
                semantic_similarity=ev_data.semantic_similarity,
                score_contribution=ev_data.score_contribution,
                explanation=ev_data.explanation,
                verification_status=ev_data.verification_status,
            )
            self.db.add(ev_obj)

        self.db.commit()
        self.db.refresh(new_result)

        self._record_audit(
            user_id=current_user.id,
            action="MATCH_RESULT_RECALCULATED",
            resource_type="JobMatchResult",
            resource_id=new_result.id,
            details={
                "job_id": str(job.id),
                "candidate_id": str(candidate.id),
                "previous_result_id": str(result.id),
                "old_score": result.overall_score,
                "new_score": new_result.overall_score,
            },
        )
        return new_result
