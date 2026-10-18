import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Enum as SQLEnum, Text, Index, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.guid import GUID
from app.models.base import TimestampMixin, utc_now
from app.models.enums import UserRole, InvitationStatus

class Agency(Base, TimestampMixin):
    __tablename__ = "agencies"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    domain = Column(String(255), nullable=True)
    country = Column(String(10), default="IN", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    users = relationship("User", back_populates="agency", cascade="all, delete-orphan")
    invitations = relationship("AgencyInvitation", back_populates="agency", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="agency", cascade="all, delete-orphan")

    @property
    def is_demo(self) -> bool:
        return self.slug == "apex-talent-partners-demo"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.RECRUITER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_platform_admin = Column(Boolean, default=False, nullable=False)
    tokens_revoked_before = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agency = relationship("Agency", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")

    @property
    def is_demo(self) -> bool:
        return self.email == "recruiter@apex-demo.hirelens.ai" or (bool(self.agency and self.agency.is_demo))

    __table_args__ = (
        Index("ix_users_agency_role", "agency_id", "role"),
    )


class AgencyInvitation(Base, TimestampMixin):
    __tablename__ = "agency_invitations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    role = Column(SQLEnum(UserRole), default=UserRole.RECRUITER, nullable=False)
    token = Column(String(255), unique=True, index=True, nullable=False)
    invited_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(SQLEnum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    agency = relationship("Agency", back_populates="invitations")
    invited_by = relationship("User", foreign_keys=[invited_by_user_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
