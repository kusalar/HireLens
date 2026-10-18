import uuid
from sqlalchemy import (
    Column,
    String,
    Numeric,
    ForeignKey,
    Enum as SQLEnum,
    Text,
    Index,
    DateTime,
)
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.guid import GUID
from app.models.base import TimestampMixin, utc_now
from app.models.enums import ExpenseCategory


class RecruitmentExpense(Base, TimestampMixin):
    __tablename__ = "recruitment_expenses"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(GUID, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    category = Column(
        SQLEnum(ExpenseCategory),
        default=ExpenseCategory.OTHER,
        nullable=False,
        index=True,
    )
    expense_date = Column(DateTime(timezone=True), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_by = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    job = relationship("Job", foreign_keys=[job_id])
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index("ix_recruitment_expenses_agency_date", "agency_id", "expense_date"),
        Index("ix_recruitment_expenses_agency_job", "agency_id", "job_id"),
        Index("ix_recruitment_expenses_agency_category", "agency_id", "category"),
    )
