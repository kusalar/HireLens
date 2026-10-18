import re
import uuid
import json
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.entities import Agency, User, AuditLog
from app.models.enums import UserRole
from app.schemas.auth import UserRegister, Token
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.repositories.user_repo import UserRepository
from app.repositories.agency_repo import AgencyRepository

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.agency_repo = AgencyRepository(db)

    def register_agency_and_owner(self, data: UserRegister) -> Tuple[User, Token]:
        # 1. Check if email already registered
        existing_user = self.user_repo.get_by_email(data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        # 2. Generate unique slug for agency
        base_slug = slugify(data.agency_name)
        if not base_slug:
            base_slug = "agency"
        unique_slug = base_slug
        counter = 1
        while self.agency_repo.get_by_slug(unique_slug):
            unique_slug = f"{base_slug}-{counter}"
            counter += 1

        # 3. Create Agency
        agency = Agency(
            id=uuid.uuid4(),
            name=data.agency_name.strip(),
            slug=unique_slug,
            country="IN",
            is_active=True,
        )
        self.agency_repo.create(agency)

        # 4. Create User as OWNER
        hashed_password = get_password_hash(data.password)
        user = User(
            id=uuid.uuid4(),
            agency_id=agency.id,
            email=data.email.lower().strip(),
            hashed_password=hashed_password,
            full_name=data.full_name.strip(),
            role=UserRole.OWNER,
            is_active=True,
            is_verified=True,
        )
        self.user_repo.create(user)

        # 5. Log audit
        audit = AuditLog(
            agency_id=agency.id,
            user_id=user.id,
            action="AGENCY_REGISTERED",
            resource_type="Agency",
            resource_id=str(agency.id),
            details=f"Agency '{agency.name}' registered with owner '{user.email}'",
        )
        self.db.add(audit)
        self.db.commit()

        # 6. Generate tokens
        tokens = Token(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
            token_type="bearer",
        )
        return user, tokens

    def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, Token]:
        import hashlib
        from app.models.governance import UserSession, SecurityAuditEvent
        from app.models.enums import AuditEventCategory, AuditSeverity

        clean_email = email.lower().strip()
        user = self.user_repo.get_by_email(clean_email)
        if not user or not verify_password(password, user.hashed_password):
            # Log failed authentication attempt if agency is identifiable
            if user:
                fail_event = SecurityAuditEvent(
                    agency_id=user.agency_id,
                    actor_user_id=user.id,
                    actor_email=clean_email,
                    event_category=AuditEventCategory.AUTHENTICATION,
                    severity=AuditSeverity.MEDIUM,
                    action="LOGIN_FAILED",
                    resource_type="User",
                    resource_id=str(user.id),
                    details_json=json.dumps({"reason": "Invalid credentials"}),
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                self.db.add(fail_event)
                self.db.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is inactive. Please contact your agency administrator.",
            )

        # 1. Create server-side revocable session
        device = "Desktop Browser"
        if user_agent:
            if "Mobile" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
                device = "Mobile Browser"
            elif "Postman" in user_agent or "pytest" in user_agent:
                device = "API Client"

        session = UserSession(
            agency_id=user.agency_id,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device,
            is_active=True,
        )
        self.db.add(session)
        self.db.flush()

        # 2. Mint tokens bound to session
        access_tok = create_access_token(user.id, session_id=session.id)
        refresh_tok = create_refresh_token(user.id, session_id=session.id)

        session.session_token_hash = hashlib.sha256(access_tok.encode("utf-8")).hexdigest()

        # 3. Security audit event
        success_event = SecurityAuditEvent(
            agency_id=user.agency_id,
            actor_user_id=user.id,
            actor_email=user.email,
            event_category=AuditEventCategory.AUTHENTICATION,
            severity=AuditSeverity.LOW,
            action="LOGIN_SUCCESS",
            resource_type="UserSession",
            resource_id=str(session.id),
            details_json=json.dumps({"device_info": device}),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(success_event)
        self.db.commit()

        tokens = Token(
            access_token=access_tok,
            refresh_token=refresh_tok,
            token_type="bearer",
        )
        return user, tokens

    def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Token:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
            )

        user_id_str = payload.get("sub")
        try:
            user_id = uuid.UUID(user_id_str)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed token subject.",
            )

        user = self.user_repo.get(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer active or found.",
            )

        # Validate session if sid present in refresh token
        sid_str = payload.get("sid")
        session_id = None
        if sid_str:
            from app.models.governance import UserSession
            session_id = uuid.UUID(sid_str)
            session = self.db.get(UserSession, session_id)
            if not session or not session.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh session has been revoked.",
                )

        new_access = create_access_token(user.id, session_id=session_id)
        new_refresh = create_refresh_token(user.id, session_id=session_id)
        return Token(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
        )

    def create_demo_session(
        self,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, Token, Agency]:
        from app.services.demo_service import (
            DEMO_USER_EMAIL,
            DEMO_AGENCY_SLUG,
            ensure_demo_resumes_in_storage,
        )
        from app.models.governance import UserSession, SecurityAuditEvent
        from app.models.enums import AuditEventCategory, AuditSeverity
        import hashlib
        import json

        user = self.user_repo.get_by_email(DEMO_USER_EMAIL)
        if not user:
            from app.db.seed_demo import seed_demo_data
            seed_demo_data()
            user = self.user_repo.get_by_email(DEMO_USER_EMAIL)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Demo recruiter account could not be initialized.",
                )

        agency = self.agency_repo.get(user.agency_id)
        if not agency or not agency.is_active:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Demo agency is currently unavailable.",
            )

        # 1. Create revocable server-side demo session
        session = UserSession(
            agency_id=user.agency_id,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info="Demo Session (Judge/Visitor)",
            is_active=True,
        )
        self.db.add(session)
        self.db.flush()

        # 2. Mint tokens bound to session
        access_tok = create_access_token(user.id, session_id=session.id)
        refresh_tok = create_refresh_token(user.id, session_id=session.id)
        session.session_token_hash = hashlib.sha256(access_tok.encode("utf-8")).hexdigest()

        # 3. Record audit event
        event = SecurityAuditEvent(
            agency_id=user.agency_id,
            actor_user_id=user.id,
            actor_email=user.email,
            event_category=AuditEventCategory.AUTHENTICATION,
            severity=AuditSeverity.LOW,
            action="DEMO_SESSION_LAUNCHED",
            resource_type="UserSession",
            resource_id=str(session.id),
            details_json=json.dumps({"demo_role": user.role.value, "origin": "1-click-evaluator"}),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(event)
        self.db.commit()

        # 4. Ensure sample PDF resumes are persisted in local storage
        try:
            ensure_demo_resumes_in_storage(self.db, agency.id)
        except Exception as e:
            # Non-blocking resume restoration error logging
            print(f"[DEMO_RESUME_WARN] Could not ensure demo resumes: {e}")

        tokens = Token(
            access_token=access_tok,
            refresh_token=refresh_tok,
            token_type="bearer",
        )
        return user, tokens, agency
