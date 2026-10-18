import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.models.job import Job, JobRequirement
from app.models.application import Application
from app.models.entities import User, AuditLog
from app.models.enums import JobStatus, WorkMode
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobRead,
    JobListRead,
    JobRequirementCreate,
    JobRequirementUpdate,
    JobRequirementRead,
)
from app.repositories.job_repo import JobRepository

class JobService:
    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id
        self.repo = JobRepository(db, agency_id)

    def create_job(self, current_user: User, data: JobCreate) -> Job:
        job = Job(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            created_by=current_user.id,
            title=data.title.strip(),
            department=data.department.strip() if data.department else None,
            description=data.description,
            responsibilities=data.responsibilities,
            location=data.location.strip() if data.location else None,
            work_mode=data.work_mode,
            employment_type=data.employment_type,
            minimum_experience=data.minimum_experience,
            maximum_experience=data.maximum_experience,
            status=data.status,
        )

        if data.requirements:
            for req_in in data.requirements:
                req = JobRequirement(
                    id=uuid.uuid4(),
                    requirement_text=req_in.requirement_text.strip(),
                    normalized_skill=req_in.normalized_skill.strip() if req_in.normalized_skill else None,
                    requirement_type=req_in.requirement_type,
                    importance_weight=req_in.importance_weight,
                    is_mandatory=req_in.is_mandatory,
                )
                job.requirements.append(req)

        created_job = self.repo.create(job)

        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=current_user.id,
            action="JOB_CREATED",
            resource_type="Job",
            resource_id=str(created_job.id),
            details=f"Job '{created_job.title}' created by {current_user.email}",
        )
        self.db.add(audit)
        self.db.commit()

        return created_job

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        work_mode: Optional[WorkMode] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[JobListRead]:
        jobs = self.repo.list_filtered(
            status=status,
            work_mode=work_mode,
            search=search,
            skip=skip,
            limit=limit,
        )
        result = []
        for j in jobs:
            result.append(
                JobListRead(
                    id=j.id,
                    agency_id=j.agency_id,
                    title=j.title,
                    department=j.department,
                    location=j.location,
                    work_mode=j.work_mode,
                    employment_type=j.employment_type,
                    minimum_experience=j.minimum_experience,
                    maximum_experience=j.maximum_experience,
                    status=j.status,
                    created_at=j.created_at,
                    requirements_count=len(j.requirements) if j.requirements else 0,
                )
            )
        return result

    def get_job(self, job_id: uuid.UUID) -> Job:
        job = self.repo.get_with_requirements(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or unauthorized.",
            )
        return job

    def update_job(self, current_user: User, job_id: uuid.UUID, data: JobUpdate) -> Job:
        job = self.get_job(job_id)
        updates = data.model_dump(exclude_unset=True)

        # Cross validate minimum vs maximum experience if one is updated
        new_min = updates.get("minimum_experience", job.minimum_experience)
        new_max = updates.get("maximum_experience", job.maximum_experience)
        if new_max is not None and new_min > new_max:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Minimum experience cannot exceed maximum experience.",
            )

        updated = self.repo.update(job, updates)

        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=current_user.id,
            action="JOB_UPDATED",
            resource_type="Job",
            resource_id=str(updated.id),
            details=f"Job '{updated.title}' updated by {current_user.email}",
        )
        self.db.add(audit)
        self.db.commit()

        return updated

    def archive_job(self, current_user: User, job_id: uuid.UUID) -> Job:
        job = self.repo.archive(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or unauthorized.",
            )
        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=current_user.id,
            action="JOB_ARCHIVED",
            resource_type="Job",
            resource_id=str(job.id),
            details=f"Job '{job.title}' archived by {current_user.email}",
        )
        self.db.add(audit)
        self.db.commit()
        return job

    def delete_job(self, current_user: User, job_id: uuid.UUID) -> bool:
        job = self.get_job(job_id)
        # Check if job has applications to prevent silent erasure of recruitment history
        app_count = self.db.scalar(
            select(func.count(Application.id)).where(
                Application.job_id == job.id,
                Application.agency_id == self.agency_id,
            )
        ) or 0
        if app_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete job '{job.title}' because it has {app_count} associated application(s). Archive or close the job instead to preserve recruitment history.",
            )

        deleted = self.repo.delete(job.id)
        if deleted:
            audit = AuditLog(
                agency_id=self.agency_id,
                user_id=current_user.id,
                action="JOB_DELETED",
                resource_type="Job",
                resource_id=str(job_id),
                details=f"Job '{job.title}' deleted by {current_user.email}",
            )
            self.db.add(audit)
            self.db.commit()
        return deleted

    # --- Job Requirements ---

    def add_requirement(
        self, current_user: User, job_id: uuid.UUID, data: JobRequirementCreate
    ) -> JobRequirement:
        # Verify job exists in agency
        self.get_job(job_id)

        req = JobRequirement(
            id=uuid.uuid4(),
            job_id=job_id,
            requirement_text=data.requirement_text.strip(),
            normalized_skill=data.normalized_skill.strip() if data.normalized_skill else None,
            requirement_type=data.requirement_type,
            importance_weight=data.importance_weight,
            is_mandatory=data.is_mandatory,
        )
        created_req = self.repo.add_requirement(job_id, req)
        if not created_req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to add requirement to job.",
            )
        return created_req

    def update_requirement(
        self,
        current_user: User,
        job_id: uuid.UUID,
        requirement_id: uuid.UUID,
        data: JobRequirementUpdate,
    ) -> JobRequirement:
        self.get_job(job_id)
        updates = data.model_dump(exclude_unset=True)
        updated_req = self.repo.update_requirement(job_id, requirement_id, updates)
        if not updated_req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job requirement not found or unauthorized.",
            )
        return updated_req

    def delete_requirement(
        self, current_user: User, job_id: uuid.UUID, requirement_id: uuid.UUID
    ) -> bool:
        self.get_job(job_id)
        deleted = self.repo.delete_requirement(job_id, requirement_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job requirement not found or unauthorized.",
            )
        return True
