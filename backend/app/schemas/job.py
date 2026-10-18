import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.models.enums import WorkMode, EmploymentType, JobStatus, RequirementType

# --- Job Requirements ---

class JobRequirementBase(BaseModel):
    requirement_text: str = Field(..., min_length=1, max_length=1000)
    normalized_skill: Optional[str] = Field(None, max_length=150)
    requirement_type: RequirementType = RequirementType.SKILL
    importance_weight: float = Field(1.0, gt=0, le=10.0, description="Importance weight between 0.1 and 10.0")
    is_mandatory: bool = True

class JobRequirementCreate(JobRequirementBase):
    pass

class JobRequirementUpdate(BaseModel):
    requirement_text: Optional[str] = Field(None, min_length=1, max_length=1000)
    normalized_skill: Optional[str] = Field(None, max_length=150)
    requirement_type: Optional[RequirementType] = None
    importance_weight: Optional[float] = Field(None, gt=0, le=10.0)
    is_mandatory: Optional[bool] = None

class JobRequirementRead(JobRequirementBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    created_at: datetime


# --- Jobs ---

class JobBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    location: Optional[str] = Field(None, max_length=100)
    work_mode: WorkMode = WorkMode.ONSITE
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    minimum_experience: int = Field(0, ge=0, description="Minimum experience in years")
    maximum_experience: Optional[int] = Field(None, ge=0, description="Maximum experience in years")
    status: JobStatus = JobStatus.ACTIVE

    @model_validator(mode="after")
    def validate_experience_range(self):
        if self.maximum_experience is not None:
            if self.maximum_experience < self.minimum_experience:
                raise ValueError("Minimum experience cannot exceed maximum experience.")
        return self

class JobCreate(JobBase):
    requirements: Optional[List[JobRequirementCreate]] = None

class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    department: Optional[str] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[WorkMode] = None
    employment_type: Optional[EmploymentType] = None
    minimum_experience: Optional[int] = Field(None, ge=0)
    maximum_experience: Optional[int] = Field(None, ge=0)
    status: Optional[JobStatus] = None

    @model_validator(mode="after")
    def validate_experience_range(self):
        if self.minimum_experience is not None and self.maximum_experience is not None:
            if self.maximum_experience < self.minimum_experience:
                raise ValueError("Minimum experience cannot exceed maximum experience.")
        return self

class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    requirements: List[JobRequirementRead] = []

class JobListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    work_mode: WorkMode
    employment_type: EmploymentType
    minimum_experience: int
    maximum_experience: Optional[int] = None
    status: JobStatus
    created_at: datetime
    requirements_count: int = 0
