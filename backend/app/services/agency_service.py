import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.entities import Agency, User, AgencyInvitation, AuditLog
from app.models.enums import UserRole, InvitationStatus
from app.schemas.agency import AgencyUpdate, AgencyInviteCreate, AcceptInviteRequest
from app.core.security import get_password_hash
from app.repositories.agency_repo import AgencyRepository, AgencyInvitationRepository
from app.repositories.user_repo import UserRepository, TenantUserRepository

class AgencyService:
    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id
        self.agency_repo = AgencyRepository(db)
        self.invitation_repo = AgencyInvitationRepository(db)
        self.tenant_user_repo = TenantUserRepository(db, agency_id)
        self.user_repo = UserRepository(db)

    def get_profile(self) -> Agency:
        agency = self.agency_repo.get(self.agency_id)
        if not agency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agency not found.",
            )
        return agency

    def update_profile(self, data: AgencyUpdate) -> Agency:
        agency = self.get_profile()
        updates = data.model_dump(exclude_unset=True)
        return self.agency_repo.update(agency, updates)

    def list_members(self) -> List[User]:
        return self.tenant_user_repo.list()

    def invite_member(self, current_user: User, data: AgencyInviteCreate) -> AgencyInvitation:
        # Check if already a member in system
        existing = self.user_repo.get_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email is already registered in an agency.",
            )

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = AgencyInvitation(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            email=data.email.lower().strip(),
            role=data.role,
            token=token,
            invited_by_user_id=current_user.id,
            status=InvitationStatus.PENDING,
            expires_at=expires_at,
        )
        self.invitation_repo.create(invitation)

        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=current_user.id,
            action="INVITE_SENT",
            resource_type="AgencyInvitation",
            resource_id=str(invitation.id),
            details=f"Invited {data.email} as {data.role}",
        )
        self.db.add(audit)
        self.db.commit()

        return invitation

    def accept_invitation(self, data: AcceptInviteRequest) -> User:
        invitation = self.invitation_repo.get_by_token(data.token)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired invitation token.",
            )

        if invitation.status != InvitationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation is no longer active.",
            )

        # Check expiration
        now_utc = datetime.now(timezone.utc)
        inv_expiry = invitation.expires_at
        if inv_expiry.tzinfo is None:
            inv_expiry = inv_expiry.replace(tzinfo=timezone.utc)

        if inv_expiry < now_utc:
            invitation.status = InvitationStatus.EXPIRED
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation token has expired.",
            )

        # Create user
        hashed_password = get_password_hash(data.password)
        new_user = User(
            id=uuid.uuid4(),
            agency_id=invitation.agency_id,
            email=invitation.email,
            hashed_password=hashed_password,
            full_name=data.full_name.strip(),
            role=invitation.role,
            is_active=True,
            is_verified=True,
        )
        self.user_repo.create(new_user)

        invitation.status = InvitationStatus.ACCEPTED
        self.db.commit()

        audit = AuditLog(
            agency_id=invitation.agency_id,
            user_id=new_user.id,
            action="INVITE_ACCEPTED",
            resource_type="User",
            resource_id=str(new_user.id),
            details=f"User {new_user.email} joined agency via invitation",
        )
        self.db.add(audit)
        self.db.commit()

        return new_user

    def update_member_role(self, target_user_id: uuid.UUID, new_role: UserRole) -> User:
        member = self.tenant_user_repo.get(target_user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found.",
            )
        if member.role == UserRole.OWNER and new_role != UserRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the agency owner.",
            )
        return self.tenant_user_repo.update(member, {"role": new_role})

    def update_member_status(self, target_user_id: uuid.UUID, is_active: bool, actor_user: User) -> User:
        member = self.tenant_user_repo.get(target_user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team member not found.",
            )
        if member.id == actor_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify your own active status.",
            )
        if member.role == UserRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the agency owner.",
            )
        member.is_active = is_active
        self.db.commit()

        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=actor_user.id,
            action="MEMBER_STATUS_UPDATED",
            resource_type="User",
            resource_id=str(member.id),
            details=f"User {member.email} status set to {'ACTIVE' if is_active else 'INACTIVE'}",
        )
        self.db.add(audit)
        self.db.commit()
        return member

    def list_invitations(self) -> List[AgencyInvitation]:
        return self.invitation_repo.list_by_agency(self.agency_id)

    def revoke_invitation(self, invite_id: uuid.UUID, actor_user: User) -> bool:
        invitation = self.invitation_repo.get(invite_id)
        if not invitation or invitation.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found.",
            )
        invitation.status = InvitationStatus.CANCELLED
        self.db.commit()

        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=actor_user.id,
            action="INVITE_CANCELLED",
            resource_type="AgencyInvitation",
            resource_id=str(invitation.id),
            details=f"Cancelled invitation for {invitation.email}",
        )
        self.db.add(audit)
        self.db.commit()
        return True

    def get_overview(self) -> dict:
        agency = self.get_profile()
        members = self.tenant_user_repo.list()
        total_members = len(members)
        members_by_role = {}
        for m in members:
            role_key = m.role.value if hasattr(m.role, "value") else str(m.role)
            members_by_role[role_key] = members_by_role.get(role_key, 0) + 1

        from app.models.job import Job
        from app.models.candidate import Candidate
        from app.models.application import Application
        from app.models.interview import Interview
        from app.models.enums import JobStatus
        from app.models.billing import AgencySubscription, UsageMeter

        active_jobs = self.db.query(Job).filter(
            Job.agency_id == self.agency_id,
            Job.status == JobStatus.ACTIVE,
        ).count()

        total_candidates = self.db.query(Candidate).filter(
            Candidate.agency_id == self.agency_id,
        ).count()

        total_applications = self.db.query(Application).filter(
            Application.agency_id == self.agency_id,
        ).count()

        start_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        interviews_this_month = self.db.query(Interview).filter(
            Interview.agency_id == self.agency_id,
            Interview.created_at >= start_of_month,
        ).count()

        sub = self.db.query(AgencySubscription).filter(
            AgencySubscription.agency_id == self.agency_id,
        ).first()

        tier_name = sub.plan.tier.value if sub and sub.plan else "FREE"
        sub_status = sub.status.value if sub else "ACTIVE"
        billing_interval = sub.billing_interval.value if sub else "MONTHLY"
        period_end = sub.current_period_end if sub else None

        # Check soft warning
        meters = self.db.query(UsageMeter).filter(UsageMeter.agency_id == self.agency_id).all()
        has_soft_warning = any(
            m.current_usage >= m.soft_limit and not m.is_unlimited and m.soft_limit > 0
            for m in meters
        )

        return {

            "agency": agency,
            "total_members": total_members,
            "members_by_role": members_by_role,
            "active_jobs_count": active_jobs,
            "total_candidates_count": total_candidates,
            "total_applications_count": total_applications,
            "interviews_this_month_count": interviews_this_month,
            "subscription_tier": tier_name,
            "subscription_status": sub_status,
            "billing_interval": billing_interval,
            "current_period_end": period_end,
            "soft_quota_warning": has_soft_warning,
        }

