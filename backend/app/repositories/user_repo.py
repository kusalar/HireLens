import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.entities import User
from app.repositories.base import BaseRepository, BaseTenantRepository

class UserRepository(BaseRepository[User]):
    """System-level User repository (used for authentication / global lookups by email)."""
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip())
        return self.db.scalars(stmt).first()


class TenantUserRepository(BaseTenantRepository[User]):
    """Tenant-scoped user repository for agency user management."""
    def __init__(self, db: Session, agency_id: uuid.UUID):
        super().__init__(User, db, agency_id)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(
            User.email == email.lower().strip(),
            User.agency_id == self.agency_id
        )
        return self.db.scalars(stmt).first()
