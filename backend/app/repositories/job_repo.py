import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, and_
from app.models.job import Job, JobRequirement
from app.models.enums import JobStatus, WorkMode
from app.repositories.base import BaseTenantRepository

class JobRepository(BaseTenantRepository[Job]):
    def __init__(self, db: Session, agency_id: uuid.UUID):
        super().__init__(Job, db, agency_id)

    def get_with_requirements(self, id: uuid.UUID) -> Optional[Job]:
        stmt = (
            select(Job)
            .where(Job.id == id, Job.agency_id == self.agency_id)
            .options(selectinload(Job.requirements))
        )
        return self.db.scalars(stmt).first()

    def get_detail(self, id: uuid.UUID) -> Optional[Job]:
        return self.get_with_requirements(id)


    def list_filtered(
        self,
        status: Optional[JobStatus] = None,
        work_mode: Optional[WorkMode] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Job]:
        filters = [Job.agency_id == self.agency_id]
        if status:
            filters.append(Job.status == status)
        if work_mode:
            filters.append(Job.work_mode == work_mode)
        if search:
            search_term = f"%{search.strip()}%"
            filters.append(
                (Job.title.ilike(search_term))
                | (Job.department.ilike(search_term))
                | (Job.location.ilike(search_term))
            )

        stmt = (
            select(Job)
            .where(and_(*filters))
            .options(selectinload(Job.requirements))
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def archive(self, id: uuid.UUID) -> Optional[Job]:
        job = self.get(id)
        if job:
            job.status = JobStatus.ARCHIVED
            self.db.commit()
            self.db.refresh(job)
        return job

    def add_requirement(self, job_id: uuid.UUID, requirement: JobRequirement) -> Optional[JobRequirement]:
        job = self.get(job_id)
        if not job:
            return None
        requirement.job_id = job.id
        self.db.add(requirement)
        self.db.commit()
        self.db.refresh(requirement)
        return requirement

    def get_requirement(self, job_id: uuid.UUID, requirement_id: uuid.UUID) -> Optional[JobRequirement]:
        # Validate job belongs to tenant first
        job = self.get(job_id)
        if not job:
            return None
        stmt = select(JobRequirement).where(
            JobRequirement.id == requirement_id,
            JobRequirement.job_id == job_id,
        )
        return self.db.scalars(stmt).first()

    def update_requirement(
        self, job_id: uuid.UUID, requirement_id: uuid.UUID, updates: dict
    ) -> Optional[JobRequirement]:
        req = self.get_requirement(job_id, requirement_id)
        if not req:
            return None
        for key, value in updates.items():
            if hasattr(req, key) and value is not None:
                setattr(req, key, value)
        self.db.commit()
        self.db.refresh(req)
        return req

    def delete_requirement(self, job_id: uuid.UUID, requirement_id: uuid.UUID) -> bool:
        req = self.get_requirement(job_id, requirement_id)
        if not req:
            return False
        self.db.delete(req)
        self.db.commit()
        return True
