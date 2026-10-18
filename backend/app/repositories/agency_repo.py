import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.entities import Agency, AgencyInvitation
from app.repositories.base import BaseRepository

class AgencyRepository(BaseRepository[Agency]):
    def __init__(self, db: Session):
        super().__init__(Agency, db)

    def get_by_slug(self, slug: str) -> Optional[Agency]:
        stmt = select(Agency).where(Agency.slug == slug)
        return self.db.scalars(stmt).first()

    def get_by_name(self, name: str) -> Optional[Agency]:
        stmt = select(Agency).where(Agency.name == name)
        return self.db.scalars(stmt).first()


class AgencyInvitationRepository(BaseRepository[AgencyInvitation]):
    def __init__(self, db: Session):
        super().__init__(AgencyInvitation, db)

    def get_by_token(self, token: str) -> Optional[AgencyInvitation]:
        stmt = select(AgencyInvitation).where(AgencyInvitation.token == token)
        return self.db.scalars(stmt).first()

    def list_by_agency(self, agency_id: uuid.UUID) -> List[AgencyInvitation]:
        stmt = select(AgencyInvitation).where(AgencyInvitation.agency_id == agency_id)
        return list(self.db.scalars(stmt).all())
