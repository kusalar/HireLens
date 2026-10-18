import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import UserRole
from app.schemas.agency import (
    AgencyRead,
    AgencyUpdate,
    AgencyInviteCreate,
    AgencyInviteRead,
    AcceptInviteRequest,
    AgencyOverviewResponse,
    AgencyMemberUpdateStatus,
)
from app.schemas.user import UserRead
from app.services.agency_service import AgencyService
from app.api.deps import get_current_user, require_roles, require_owner_or_admin, require_non_demo_mutation

router = APIRouter()

@router.get("/overview", response_model=AgencyOverviewResponse)
def get_agency_overview(
    current_user: User = Depends(require_owner_or_admin),
    db: Session = Depends(get_db),
):
    service = AgencyService(db, current_user.agency_id)
    return service.get_overview()

@router.get("/profile", response_model=AgencyRead)
def get_agency_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AgencyService(db, current_user.agency_id)
    return service.get_profile()

@router.patch("/profile", response_model=AgencyRead)
def update_agency_profile(
    data: AgencyUpdate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
    _: User = Depends(require_non_demo_mutation),
    db: Session = Depends(get_db),
):
    service = AgencyService(db, current_user.agency_id)
    return service.update_profile(data)

@router.get("/members", response_model=List[UserRead])
def list_team_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AgencyService(db, current_user.agency_id)
    return service.list_members()

@router.post("/members/invite", response_model=AgencyInviteRead, status_code=status.HTTP_201_CREATED)
def invite_member(
    data: AgencyInviteCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN)),
    _: User = Depends(require_non_demo_mutation),
    db: Session = Depends(get_db),
):
    service = AgencyService(db, current_user.agency_id)
    return service.invite_member(current_user, data)

@router.post("/members/accept-invite", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def accept_invite(
    data: AcceptInviteRequest,
    db: Session = Depends(get_db),
):
    # Public endpoint using invite token
    service = AgencyService(db, uuid.uuid4()) # Agency ID resolved from token inside service
    return service.accept_invitation(data)

@router.patch("/members/{user_id}/role", response_model=UserRead)
def update_member_role(
    user_id: uuid.UUID,
    new_role: UserRole,
    current_user: User = Depends(require_roles(UserRole.OWNER)),
    _: User = Depends(require_non_demo_mutation),
    db: Session = Depends(get_db),
):
    service = AgencyService(db, current_user.agency_id)
    return service.update_member_role(user_id, new_role)

@router.patch("/members/{user_id}/status", response_model=UserRead)
def update_member_status(
    user_id: uuid.UUID,
    data: AgencyMemberUpdateStatus,
    current_user: User = Depends(require_owner_or_admin),
    _: User = Depends(require_non_demo_mutation),
    db: Session = Depends(get_db),
):
    service = AgencyService(db, current_user.agency_id)
    return service.update_member_status(user_id, data.is_active, current_user)

@router.get("/invitations", response_model=List[AgencyInviteRead])
def list_invitations(
    current_user: User = Depends(require_owner_or_admin),
    db: Session = Depends(get_db),
):
    service = AgencyService(db, current_user.agency_id)
    return service.list_invitations()

@router.delete("/invitations/{invite_id}", status_code=status.HTTP_200_OK)
def revoke_invitation(
    invite_id: uuid.UUID,
    current_user: User = Depends(require_owner_or_admin),
    _: User = Depends(require_non_demo_mutation),
    db: Session = Depends(get_db),
):
    service = AgencyService(db, current_user.agency_id)
    service.revoke_invitation(invite_id, current_user)
    return {"status": "success", "message": "Invitation revoked successfully."}

