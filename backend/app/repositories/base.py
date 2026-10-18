from typing import Generic, TypeVar, Type, Optional, List, Any
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from app.db.session import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Base repository for non-tenant-scoped models (like Agency itself)."""
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: uuid.UUID) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == id)
        return self.db.scalars(stmt).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def update(self, db_obj: ModelType, updates: dict) -> ModelType:
        for field, value in updates.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: uuid.UUID) -> bool:
        db_obj = self.get(id)
        if db_obj:
            self.db.delete(db_obj)
            self.db.commit()
            return True
        return False


class BaseTenantRepository(Generic[ModelType]):
    """Tenant-isolated base repository.
    Enforces that every read, write, update, and delete is strictly scoped
    to the authenticated agency_id.
    """
    def __init__(self, model: Type[ModelType], db: Session, agency_id: uuid.UUID):
        self.model = model
        self.db = db
        self.agency_id = agency_id

    def get(self, id: uuid.UUID) -> Optional[ModelType]:
        """Fetch a record strictly matching both the ID and agency_id."""
        stmt = select(self.model).where(
            self.model.id == id,
            self.model.agency_id == self.agency_id
        )
        return self.db.scalars(stmt).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """List records strictly matching agency_id."""
        stmt = (
            select(self.model)
            .where(self.model.agency_id == self.agency_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def create(self, db_obj: ModelType) -> ModelType:
        """Create a record and guarantee agency_id is set to authenticated tenant."""
        setattr(db_obj, "agency_id", self.agency_id)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, db_obj: ModelType, updates: dict) -> ModelType:
        """Update a record verifying it belongs to the current agency."""
        if getattr(db_obj, "agency_id", None) != self.agency_id:
            raise PermissionError("Cross-tenant modification prohibited.")
        # Prevent any modification of agency_id
        updates.pop("agency_id", None)
        for field, value in updates.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: uuid.UUID) -> bool:
        """Delete a record strictly matching both ID and agency_id."""
        db_obj = self.get(id)
        if not db_obj:
            return False
        self.db.delete(db_obj)
        self.db.commit()
        return True
