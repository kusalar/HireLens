import uuid
from typing import Generator, List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token
from app.models.entities import User, Agency
from app.models.enums import UserRole
from app.repositories.user_repo import UserRepository
from app.repositories.agency_repo import AgencyRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload:
        raise credentials_exception
    
    token_type = payload.get("type")
    if token_type != "access":
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except Exception:
        raise credentials_exception

    user_repo = UserRepository(db)
    user = user_repo.get(user_id)
    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account.",
        )

    # Check agency status for non-platform admin users
    if not getattr(user, "is_platform_admin", False):
        agency_repo = AgencyRepository(db)
        agency = agency_repo.get(user.agency_id)
        if not agency or not agency.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agency is inactive or not found.",
            )


    # 1. Server-side session revocation check (if sid claim present)
    sid_str = payload.get("sid")
    if sid_str:
        try:
            sid = uuid.UUID(sid_str)
            from app.models.governance import UserSession
            from app.models.base import utc_now
            session_obj = db.get(UserSession, sid)
            if not session_obj or not session_obj.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication session has been revoked or expired.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Update last activity
            session_obj.last_activity_at = utc_now()
            db.commit()
        except HTTPException:
            raise
        except Exception:
            raise credentials_exception

    # 2. Global tokens revocation check (tokens_revoked_before)
    if user.tokens_revoked_before:
        iat = payload.get("iat")
        if iat:
            from datetime import datetime, timezone
            iat_dt = datetime.fromtimestamp(iat, tz=timezone.utc) if isinstance(iat, (int, float)) else iat
            revoked_before = user.tokens_revoked_before
            if revoked_before.tzinfo is None:
                revoked_before = revoked_before.replace(tzinfo=timezone.utc)
            if iat_dt < revoked_before:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="All user sessions have been globally revoked. Please log in again.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    return user


def get_current_agency(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Agency:
    agency_repo = AgencyRepository(db)
    agency = agency_repo.get(current_user.agency_id)
    if not agency or not agency.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agency is inactive or not found.",
        )
    return agency


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Dependency factory checking that current user possesses an authorized role."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {[r.value for r in allowed_roles]}; current role: {current_user.role.value}.",
            )
        return current_user
    return role_checker


def require_owner_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Convenience dependency restricting operations to agency OWNER or ADMIN."""
    if current_user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to agency OWNER or ADMIN.",
        )
    return current_user


def require_platform_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency verifying that the user is an authorized platform administrator."""
    if not getattr(current_user, "is_platform_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator privileges required.",
        )
    return current_user


def require_non_demo_mutation(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency protecting core demonstration records.
    Rejects destructive mutations (deletes, billing changes, team member removal)
    for demo agency accounts with a 403 Forbidden explaining the restriction.
    """
    if getattr(current_user, "is_demo", False) or current_user.email == "recruiter@apex-demo.hirelens.ai":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action restricted in Live Demo Mode. Core sample jobs, candidate profiles, and organization settings are protected.",
        )
    return current_user
