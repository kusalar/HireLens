import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from app.models.enums import CandidateProfileStatus

# --- Experience ---

class CandidateExperienceBase(BaseModel):
    company: str = Field(..., min_length=1, max_length=255)
    job_title: str = Field(..., min_length=1, max_length=255)
    start_date: Optional[str] = Field(None, max_length=50)
    end_date: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None

class CandidateExperienceCreate(CandidateExperienceBase):
    pass

class CandidateExperienceRead(CandidateExperienceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID


# --- Education ---

class CandidateEducationBase(BaseModel):
    institution: str = Field(..., min_length=1, max_length=255)
    qualification: str = Field(..., min_length=1, max_length=255)
    field_of_study: Optional[str] = Field(None, max_length=255)
    start_year: Optional[int] = None
    end_year: Optional[int] = None

class CandidateEducationCreate(CandidateEducationBase):
    pass

class CandidateEducationRead(CandidateEducationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID


# --- Skill ---

class CandidateSkillBase(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=150)
    normalized_skill: Optional[str] = Field(None, max_length=150)
    proficiency: Optional[str] = Field(None, max_length=50)
    evidence: Optional[str] = None
    source_page: Optional[int] = None

class CandidateSkillCreate(CandidateSkillBase):
    pass

class CandidateSkillRead(CandidateSkillBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID


# --- Recruiter Note ---

class RecruiterNoteBase(BaseModel):
    note: str = Field(..., min_length=1)

class RecruiterNoteCreate(RecruiterNoteBase):
    pass

class RecruiterNoteUpdate(RecruiterNoteBase):
    pass

class RecruiterNoteRead(RecruiterNoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    agency_id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    author_name: Optional[str] = None


# --- Candidate Master ---

class CandidateBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone_encrypted: Optional[str] = Field(None, max_length=255)
    current_title: Optional[str] = Field(None, max_length=255)
    total_experience_months: int = Field(0, ge=0)
    current_location: Optional[str] = Field(None, max_length=100)
    professional_summary: Optional[str] = None
    profile_status: CandidateProfileStatus = CandidateProfileStatus.ACTIVE
    source: Optional[str] = Field(None, max_length=100)

class CandidateCreate(CandidateBase):
    experiences: Optional[List[CandidateExperienceCreate]] = None
    educations: Optional[List[CandidateEducationCreate]] = None
    skills: Optional[List[CandidateSkillCreate]] = None

class CandidateUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone_encrypted: Optional[str] = None
    current_title: Optional[str] = None
    total_experience_months: Optional[int] = Field(None, ge=0)
    current_location: Optional[str] = None
    professional_summary: Optional[str] = None
    profile_status: Optional[CandidateProfileStatus] = None
    source: Optional[str] = Field(None, max_length=100)

class CandidateRead(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    experiences: List[CandidateExperienceRead] = []
    educations: List[CandidateEducationRead] = []
    skills: List[CandidateSkillRead] = []
    notes: List[RecruiterNoteRead] = []

class CandidateListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    full_name: str
    email: Optional[str] = None
    current_title: Optional[str] = None
    total_experience_months: int
    current_location: Optional[str] = None
    profile_status: CandidateProfileStatus
    source: Optional[str] = None
    skills_preview: List[str] = []
    created_at: datetime
