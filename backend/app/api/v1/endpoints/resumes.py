import uuid
from typing import Optional, List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Query,
    Response,
)
from fastapi.responses import StreamingResponse
import io

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user, require_roles, require_non_demo_mutation
from app.models.entities import User
from app.models.enums import UserRole, ResumeProcessingStatus
from app.services.resume_service import ResumeService
from app.schemas.resume import (
    ResumeRead,
    ResumeListResponse,
    BulkUploadResponse,
    ResumeDetailResponse,
    ResumeExtractedProfileRead,
    ResumeExtractedProfileUpdate,
    ResumeEvidenceRead,
    ResumeEvidenceUpdate,
    ResumeAssociateCandidateRequest,
    FileUploadResult,
)
from app.schemas.candidate import CandidateRead

router = APIRouter()

MUTATION_ROLES = [UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER]


@router.post(
    "/upload",
    response_model=FileUploadResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a single resume file (PDF or DOCX)",
)
async def upload_resume(
    response: Response,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MUTATION_ROLES)),
):
    service = ResumeService(db, current_user.agency_id)
    content = await file.read()

    resume, is_dup, error, existing_id = service.upload_single_resume(
        content=content,
        original_filename=file.filename or "resume.pdf",
        current_user=current_user,
        reraise_validation=True,
    )

    if is_dup:
        response.status_code = status.HTTP_200_OK
        return FileUploadResult(
            filename=file.filename or "resume",
            status="DUPLICATE",
            existing_resume_id=existing_id,
            error=error,
        )

    if error or not resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Failed to process resume upload.",
        )

    return FileUploadResult(
        filename=file.filename or "resume",
        status="SUCCESS",
        resume_id=resume.id,
        resume=ResumeRead.model_validate(resume),
    )


@router.post(
    "/bulk-upload",
    response_model=BulkUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload multiple resumes in bulk",
)
async def bulk_upload_resumes(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MUTATION_ROLES)),
):
    service = ResumeService(db, current_user.agency_id)
    file_payloads = []
    for f in files:
        data = await f.read()
        file_payloads.append((f.filename or "document.pdf", data))

    return service.bulk_upload_resumes(file_payloads, current_user)


@router.get(
    "",
    response_model=ResumeListResponse,
    summary="List and filter resumes scoped to agency",
)
def list_resumes(
    search: Optional[str] = Query(None, description="Search by original filename"),
    status: Optional[ResumeProcessingStatus] = Query(None, description="Filter by processing status"),
    candidate_id: Optional[uuid.UUID] = Query(None, description="Filter by associated candidate"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ResumeService(db, current_user.agency_id)
    skip = (page - 1) * page_size
    items, total = service.repo.list_filtered(
        search=search,
        status=status,
        candidate_id=candidate_id,
        skip=skip,
        limit=page_size,
    )

    read_items = [
        ResumeRead(
            id=r.id,
            agency_id=r.agency_id,
            candidate_id=r.candidate_id,
            uploaded_by=r.uploaded_by,
            original_filename=r.original_filename,
            mime_type=r.mime_type,
            file_size=r.file_size,
            sha256_hash=r.sha256_hash,
            page_count=r.page_count,
            language=r.language,
            processing_status=r.processing_status,
            upload_status=r.upload_status,
            error_message=r.error_message,
            created_at=r.created_at,
            updated_at=r.updated_at,
            candidate_name=r.candidate.full_name if r.candidate else None,
        )
        for r in items
    ]

    return ResumeListResponse(
        items=read_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{resume_id}",
    response_model=ResumeDetailResponse,
    summary="Get full resume details including extracted profile and parsing history",
)
def get_resume(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ResumeService(db, current_user.agency_id)
    return service.get_resume_detail(resume_id)


@router.get(
    "/{resume_id}/download",
    summary="Download original resume file with authenticated tenant verification",
)
def download_resume(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ResumeService(db, current_user.agency_id)
    content, filename, mime_type = service.download_resume(resume_id, current_user)

    safe_filename = filename.replace('"', '\\"')
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_filename}"',
        "Content-Length": str(len(content)),
    }
    return StreamingResponse(io.BytesIO(content), media_type=mime_type, headers=headers)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a resume and its storage file",
)
def delete_resume(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MUTATION_ROLES)),
    _: User = Depends(require_non_demo_mutation),
):
    service = ResumeService(db, current_user.agency_id)
    service.delete_resume(resume_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{resume_id}/retry",
    response_model=ResumeRead,
    summary="Retry processing pipeline for a failed or stuck resume",
)
def retry_resume_processing(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MUTATION_ROLES)),
):
    service = ResumeService(db, current_user.agency_id)
    retried = service.retry_processing(resume_id, current_user)
    return ResumeRead.model_validate(retried)


@router.get(
    "/{resume_id}/profile",
    response_model=Optional[ResumeExtractedProfileRead],
    summary="Get the extracted profile for a resume",
)
def get_extracted_profile(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ResumeService(db, current_user.agency_id)
    detail = service.get_resume_detail(resume_id)
    return detail.current_profile


@router.put(
    "/{resume_id}/profile",
    response_model=ResumeExtractedProfileRead,
    summary="Recruiter correction of extracted profile fields",
)
def update_extracted_profile(
    resume_id: uuid.UUID,
    update_dto: ResumeExtractedProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MUTATION_ROLES)),
):
    service = ResumeService(db, current_user.agency_id)
    service.update_extracted_profile(resume_id, update_dto, current_user)
    detail = service.get_resume_detail(resume_id)
    return detail.current_profile


@router.patch(
    "/{resume_id}/evidence/{evidence_id}",
    response_model=ResumeEvidenceRead,
    summary="Verify, correct, or reject an extracted evidence item",
)
def update_evidence(
    resume_id: uuid.UUID,
    evidence_id: uuid.UUID,
    update_dto: ResumeEvidenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MUTATION_ROLES)),
):
    service = ResumeService(db, current_user.agency_id)
    updated = service.update_evidence(resume_id, evidence_id, update_dto, current_user)
    return ResumeEvidenceRead.model_validate(updated)


@router.post(
    "/{resume_id}/associate-candidate",
    response_model=CandidateRead,
    summary="Associate resume with existing candidate or confirm & create new candidate",
)
def associate_candidate(
    resume_id: uuid.UUID,
    req: ResumeAssociateCandidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MUTATION_ROLES)),
):
    service = ResumeService(db, current_user.agency_id)
    candidate = service.associate_candidate(resume_id, req, current_user)
    return CandidateRead.model_validate(candidate)
