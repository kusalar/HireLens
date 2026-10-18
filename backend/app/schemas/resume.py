import uuid
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import (
    ResumeProcessingStatus,
    VerificationStatus,
    RecruiterReviewStatus,
    ParseRunStatus,
)


# ==========================================
# AI Extraction Structured Schemas
# ==========================================

class ExtractedSkillItem(BaseModel):
    skill_name: str = Field(..., min_length=1)
    proficiency: Optional[str] = None
    evidence: Optional[str] = None
    source_page: Optional[int] = None


class ExtractedExperienceItem(BaseModel):
    company: str = Field(..., min_length=1)
    job_title: str = Field(..., min_length=1)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    evidence: Optional[str] = None
    source_page: Optional[int] = None


class ExtractedEducationItem(BaseModel):
    institution: str = Field(..., min_length=1)
    qualification: str = Field(..., min_length=1)
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    evidence: Optional[str] = None
    source_page: Optional[int] = None


class ExtractedProjectItem(BaseModel):
    project_name: str = Field(..., min_length=1)
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)


class ExtractedCertificationItem(BaseModel):
    name: str = Field(..., min_length=1)
    issuer: Optional[str] = None
    year: Optional[int] = None


class ResumeExtractionSchema(BaseModel):
    """
    Strict validated schema for model output.
    Prompt injection defense: Model only extracts facts present in document.
    """
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    current_title: Optional[str] = None
    professional_summary: Optional[str] = None
    total_experience_months: Optional[int] = None
    skills: List[ExtractedSkillItem] = Field(default_factory=list)
    experiences: List[ExtractedExperienceItem] = Field(default_factory=list)
    educations: List[ExtractedEducationItem] = Field(default_factory=list)
    projects: List[ExtractedProjectItem] = Field(default_factory=list)
    certifications: List[ExtractedCertificationItem] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    confidence_score: float = 0.8


# ==========================================
# API DTOs & Responses
# ==========================================

class ResumeBase(BaseModel):
    original_filename: str
    mime_type: str
    file_size: int
    page_count: Optional[int] = None
    language: Optional[str] = "en"
    processing_status: ResumeProcessingStatus
    upload_status: str = "COMPLETED"
    error_message: Optional[str] = None


class ResumeRead(ResumeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    candidate_id: Optional[uuid.UUID] = None
    uploaded_by: Optional[uuid.UUID] = None
    sha256_hash: str
    created_at: datetime
    updated_at: datetime
    candidate_name: Optional[str] = None


class ResumeListResponse(BaseModel):
    items: List[ResumeRead]
    total: int
    page: int
    page_size: int


class FileUploadResult(BaseModel):
    filename: str
    status: str  # "SUCCESS", "DUPLICATE", "REJECTED"
    resume_id: Optional[uuid.UUID] = None
    resume: Optional[ResumeRead] = None
    error: Optional[str] = None
    existing_resume_id: Optional[uuid.UUID] = None


class BulkUploadResponse(BaseModel):
    total_files: int
    successful_count: int
    failed_count: int
    duplicate_count: int
    results: List[FileUploadResult]


class ResumeParseRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resume_id: uuid.UUID
    provider: str
    model_name: str
    model_version: Optional[str] = None
    extraction_method: str
    status: ParseRunStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime


class ResumeEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parse_run_id: uuid.UUID
    resume_id: uuid.UUID
    field_name: str
    extracted_value: str
    corrected_value: Optional[str] = None
    source_page: Optional[int] = None
    source_excerpt: Optional[str] = None
    confidence: Optional[float] = 1.0
    verification_status: VerificationStatus
    created_at: datetime


class ResumeEvidenceUpdate(BaseModel):
    verification_status: VerificationStatus
    corrected_value: Optional[str] = None


class ResumeExtractedProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resume_id: uuid.UUID
    parse_run_id: uuid.UUID
    agency_id: uuid.UUID
    extracted_name: Optional[str] = None
    extracted_email: Optional[str] = None
    extracted_phone: Optional[str] = None
    extracted_location: Optional[str] = None
    extracted_current_title: Optional[str] = None
    extracted_summary: Optional[str] = None
    extracted_experience_months: Optional[int] = None
    structured_data: Optional[ResumeExtractionSchema] = None
    overall_confidence: Optional[float] = 0.0
    recruiter_review_status: RecruiterReviewStatus
    created_at: datetime
    updated_at: datetime


class ResumeExtractedProfileUpdate(BaseModel):
    extracted_name: Optional[str] = None
    extracted_email: Optional[str] = None
    extracted_phone: Optional[str] = None
    extracted_location: Optional[str] = None
    extracted_current_title: Optional[str] = None
    extracted_summary: Optional[str] = None
    extracted_experience_months: Optional[int] = None
    structured_data: Optional[ResumeExtractionSchema] = None
    recruiter_review_status: Optional[RecruiterReviewStatus] = None


class ResumeAssociateCandidateRequest(BaseModel):
    candidate_id: Optional[uuid.UUID] = None
    create_new_candidate: bool = False
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    candidate_title: Optional[str] = None
    candidate_location: Optional[str] = None
    candidate_summary: Optional[str] = None
    total_experience_months: Optional[int] = None


class CandidateMatchSuggestion(BaseModel):
    candidate_id: uuid.UUID
    full_name: str
    email: Optional[str] = None
    current_title: Optional[str] = None
    match_reason: str


class ResumeDetailResponse(BaseModel):
    resume: ResumeRead
    current_profile: Optional[ResumeExtractedProfileRead] = None
    parse_runs: List[ResumeParseRunRead] = Field(default_factory=list)
    evidences: List[ResumeEvidenceRead] = Field(default_factory=list)
    possible_matching_candidates: List[CandidateMatchSuggestion] = Field(default_factory=list)
