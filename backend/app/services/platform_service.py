import uuid
import os
import time
import shutil
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, text
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.entities import Agency, User
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.application import Application
from app.models.interview import Interview
from app.models.resume import Resume
from app.models.enums import (
    JobStatus,
    SubscriptionTier,
    SubscriptionStatus,
    BillingInterval,
    BillingCurrency,
    InvoiceStatus,
    AuditEventCategory,
    AuditSeverity,
)
from app.models.billing import (
    SubscriptionPlan,
    AgencySubscription,
    BillingInvoice,
    AgencyBillingProfile,
    EntitlementOverride,
)
from app.models.governance import SecurityAuditEvent
from app.schemas.billing import BillingInvoiceRead
from app.schemas.platform import (
    PlatformOverviewResponse,
    PlatformAgencyItem,
    PlatformAgencyListResponse,
    PlatformAgencyDetailResponse,
    PlatformAuditLogItem,
    PlatformAuditLogListResponse,
    PlatformSystemHealthResponse,
)



class PlatformService:
    def __init__(self, db: Session):
        self.db = db

    def get_overview(self) -> PlatformOverviewResponse:
        total_agencies = self.db.query(Agency).count()
        active_agencies = self.db.query(Agency).filter(Agency.is_active.is_(True)).count()
        suspended_agencies = total_agencies - active_agencies

        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active.is_(True)).count()

        total_jobs = self.db.query(Job).count()
        active_jobs = self.db.query(Job).filter(Job.status == JobStatus.ACTIVE).count()

        total_candidates = self.db.query(Candidate).count()
        total_applications = self.db.query(Application).count()
        total_interviews = self.db.query(Interview).count()
        total_resumes = self.db.query(Resume).count()

        # Subscription breakdowns
        subs = self.db.query(AgencySubscription).all()
        subs_by_tier: Dict[str, int] = {tier.value: 0 for tier in SubscriptionTier}
        subs_by_status: Dict[str, int] = {s.value: 0 for s in SubscriptionStatus}

        mrr_inr = 0.0
        mrr_usd = 0.0

        for sub in subs:
            status_val = sub.status.value if hasattr(sub.status, "value") else str(sub.status)
            subs_by_status[status_val] = subs_by_status.get(status_val, 0) + 1

            if sub.plan:
                tier_val = sub.plan.tier.value if hasattr(sub.plan.tier, "value") else str(sub.plan.tier)
                subs_by_tier[tier_val] = subs_by_tier.get(tier_val, 0) + 1

                if sub.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]:
                    # Calculate normalized MRR
                    if sub.currency == BillingCurrency.INR:
                        if sub.billing_interval == BillingInterval.ANNUAL:
                            mrr_inr += sub.plan.price_inr / 12.0
                        else:
                            mrr_inr += sub.plan.price_inr
                    else:
                        if sub.billing_interval == BillingInterval.ANNUAL:
                            mrr_usd += sub.plan.price_usd / 12.0
                        else:
                            mrr_usd += sub.plan.price_usd

        arr_inr = mrr_inr * 12.0
        arr_usd = mrr_usd * 12.0

        # Invoices and gross revenue
        paid_invoices = self.db.query(BillingInvoice).filter(BillingInvoice.status == InvoiceStatus.PAID).all()
        total_invoices_paid = len(paid_invoices)
        total_rev_inr = 0.0
        total_rev_usd = 0.0

        for inv in paid_invoices:
            if inv.currency == BillingCurrency.INR:
                total_rev_inr += float(inv.total_amount)
            else:
                total_rev_usd += float(inv.total_amount)

        return PlatformOverviewResponse(
            total_agencies=total_agencies,
            active_agencies=active_agencies,
            suspended_agencies=suspended_agencies,
            total_users=total_users,
            active_users=active_users,
            total_jobs=total_jobs,
            active_jobs=active_jobs,
            total_candidates=total_candidates,
            total_applications=total_applications,
            total_interviews=total_interviews,
            total_resumes_processed=total_resumes,
            subscriptions_by_tier=subs_by_tier,
            subscriptions_by_status=subs_by_status,
            mrr_inr=round(mrr_inr, 2),
            mrr_usd=round(mrr_usd, 2),
            arr_inr=round(arr_inr, 2),
            arr_usd=round(arr_usd, 2),
            total_revenue_inr=round(total_rev_inr, 2),
            total_revenue_usd=round(total_rev_usd, 2),
            total_invoices_paid=total_invoices_paid,
            system_status="HEALTHY",
        )

    def list_agencies(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        country: Optional[str] = None,
    ) -> PlatformAgencyListResponse:
        query = self.db.query(Agency)

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Agency.name.ilike(search_term),
                    Agency.slug.ilike(search_term),
                    Agency.domain.ilike(search_term),
                )
            )

        if status_filter:
            if status_filter.upper() == "ACTIVE":
                query = query.filter(Agency.is_active.is_(True))
            elif status_filter.upper() == "SUSPENDED":
                query = query.filter(Agency.is_active.is_(False))

        if country:
            query = query.filter(Agency.country == country.upper())

        total = query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        agencies = query.order_by(Agency.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        items: List[PlatformAgencyItem] = []
        for a in agencies:
            user_count = self.db.query(User).filter(User.agency_id == a.id).count()
            job_count = self.db.query(Job).filter(Job.agency_id == a.id).count()
            candidate_count = self.db.query(Candidate).filter(Candidate.agency_id == a.id).count()

            sub = self.db.query(AgencySubscription).filter(AgencySubscription.agency_id == a.id).first()
            plan_name = sub.plan.name if sub and sub.plan else "FREE"
            sub_status = sub.status.value if sub else "ACTIVE"

            items.append(
                PlatformAgencyItem(
                    id=a.id,
                    name=a.name,
                    slug=a.slug,
                    domain=a.domain,
                    country=a.country,
                    is_active=a.is_active,
                    created_at=a.created_at,
                    user_count=user_count,
                    job_count=job_count,
                    candidate_count=candidate_count,
                    current_plan=plan_name,
                    subscription_status=sub_status,
                )
            )

        return PlatformAgencyListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_agency_detail(self, agency_id: uuid.UUID) -> PlatformAgencyDetailResponse:
        agency = self.db.query(Agency).filter(Agency.id == agency_id).first()
        if not agency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agency not found.",
            )

        users = self.db.query(User).filter(User.agency_id == agency_id).all()
        sub = self.db.query(AgencySubscription).filter(AgencySubscription.agency_id == agency_id).first()
        profile = self.db.query(AgencyBillingProfile).filter(AgencyBillingProfile.agency_id == agency_id).first()
        active_jobs = self.db.query(Job).filter(Job.agency_id == agency_id, Job.status == JobStatus.ACTIVE).count()
        total_candidates = self.db.query(Candidate).filter(Candidate.agency_id == agency_id).count()
        total_applications = self.db.query(Application).filter(Application.agency_id == agency_id).count()

        recent_invoices = self.db.query(BillingInvoice).filter(
            BillingInvoice.agency_id == agency_id
        ).order_by(BillingInvoice.created_at.desc()).limit(10).all()

        overrides = self.db.query(EntitlementOverride).filter(
            EntitlementOverride.agency_id == agency_id,
            or_(
                EntitlementOverride.expires_at.is_(None),
                EntitlementOverride.expires_at > datetime.now(timezone.utc),
            ),
        ).all()


        from app.services.billing_service import BillingService
        bs = BillingService(self.db, agency_id)
        sub_read = bs.get_agency_subscription()


        mapped_invoices = [
            BillingInvoiceRead(
                id=inv.id,
                invoice_number=inv.invoice_number,
                status=inv.status,
                currency=inv.currency,
                subtotal=float(inv.subtotal),
                tax_rate_pct=inv.tax_rate_pct,
                tax_amount=float(inv.tax_amount),
                total_amount=float(inv.total_amount),
                customer_name=inv.customer_name,
                customer_email=inv.customer_email,
                customer_gstin=inv.customer_gstin,
                is_domestic_india=inv.is_domestic_india,
                paid_at=inv.paid_at,
                due_date=inv.due_date,
                download_url=f"/api/v1/billing/invoices/{inv.id}/download",
                created_at=inv.created_at,
            )
            for inv in recent_invoices
        ]

        return PlatformAgencyDetailResponse(
            id=agency.id,
            name=agency.name,
            slug=agency.slug,
            domain=agency.domain,
            country=agency.country,
            is_active=agency.is_active,
            created_at=agency.created_at,
            users=users,
            subscription=sub_read,
            billing_profile=profile,
            active_jobs_count=active_jobs,
            total_candidates_count=total_candidates,
            total_applications_count=total_applications,
            recent_invoices=mapped_invoices,
            entitlement_overrides=overrides,
        )


    def update_agency_status(
        self,
        agency_id: uuid.UUID,
        is_active: bool,
        reason: str,
        admin_user: User,
    ) -> Agency:
        agency = self.db.query(Agency).filter(Agency.id == agency_id).first()
        if not agency:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agency not found.",
            )

        import json
        prev_status = agency.is_active
        agency.is_active = is_active
        self.db.commit()

        # Audit event
        audit = SecurityAuditEvent(
            id=uuid.uuid4(),
            agency_id=agency_id,
            actor_user_id=admin_user.id,
            actor_email=admin_user.email,
            event_category=AuditEventCategory.ADMIN_ACTION,
            severity=AuditSeverity.HIGH,
            action="PLATFORM_AGENCY_STATUS_UPDATE",
            resource_type="Agency",
            resource_id=str(agency_id),
            details_json=json.dumps({
                "previous_status": prev_status,
                "new_status": is_active,
                "reason": reason,
                "admin_email": admin_user.email,
            }),
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(audit)
        self.db.commit()
        return agency

    def list_audit_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        agency_id: Optional[uuid.UUID] = None,
        event_category: Optional[str] = None,
        severity: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PlatformAuditLogListResponse:
        import json
        query = self.db.query(SecurityAuditEvent)

        if agency_id:
            query = query.filter(SecurityAuditEvent.agency_id == agency_id)

        if event_category:
            query = query.filter(SecurityAuditEvent.event_category == event_category)

        if severity:
            query = query.filter(SecurityAuditEvent.severity == severity)

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    SecurityAuditEvent.action.ilike(search_term),
                    SecurityAuditEvent.actor_email.ilike(search_term),
                    SecurityAuditEvent.resource_type.ilike(search_term),
                    SecurityAuditEvent.resource_id.ilike(search_term),
                )
            )

        total = query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        logs = query.order_by(SecurityAuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        # Pre-fetch agency names
        agency_ids = {l.agency_id for l in logs if l.agency_id}
        agencies_map = {}
        if agency_ids:
            found_agencies = self.db.query(Agency.id, Agency.name).filter(Agency.id.in_(agency_ids)).all()
            agencies_map = {a.id: a.name for a in found_agencies}

        items: List[PlatformAuditLogItem] = []
        for l in logs:
            cat_str = l.event_category.value if hasattr(l.event_category, "value") else str(l.event_category)
            sev_str = l.severity.value if hasattr(l.severity, "value") else str(l.severity)
            details_dict = None
            if l.details_json:
                try:
                    details_dict = json.loads(l.details_json)
                except Exception:
                    details_dict = {"raw": l.details_json}

            items.append(
                PlatformAuditLogItem(
                    id=l.id,
                    agency_id=l.agency_id,
                    agency_name=agencies_map.get(l.agency_id, "Unknown Agency"),
                    actor_user_id=l.actor_user_id,
                    actor_email=l.actor_email,
                    event_category=cat_str,
                    severity=sev_str,
                    action=l.action,
                    resource_type=l.resource_type,
                    resource_id=l.resource_id,
                    details=details_dict,
                    ip_address=l.ip_address,
                    created_at=l.created_at,
                )
            )


        return PlatformAuditLogListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_system_health(self) -> PlatformSystemHealthResponse:
        # 1. Database Check
        db_start = time.time()
        try:
            self.db.execute(text("SELECT 1"))
            db_latency_ms = round((time.time() - db_start) * 1000, 2)
            db_status = {"status": "UP", "latency_ms": db_latency_ms, "dialect": self.db.bind.dialect.name}
        except Exception as e:
            db_status = {"status": "DOWN", "error": str(e)}

        # 2. Redis & Celery Check
        redis_status = {"status": "UP", "broker_url": settings.CELERY_BROKER_URL}
        try:
            import redis
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=1.0)
            r.ping()
            redis_status["ping"] = "PONG"
        except Exception as e:
            # Redis might not be running locally if in SQLite mode, mark degraded gracefully
            redis_status["status"] = "LOCAL_SANDBOX"
            redis_status["note"] = "Local dev mode without dedicated Redis"

        # 3. Storage Check
        storage_path = settings.LOCAL_STORAGE_PATH
        storage_status = {"type": settings.STORAGE_TYPE, "path": storage_path}
        try:
            os.makedirs(storage_path, exist_ok=True)
            test_file = os.path.join(storage_path, ".health_check_test")
            with open(test_file, "w") as f:
                f.write("health_ok")
            os.remove(test_file)
            total, used, free = shutil.disk_usage(storage_path)
            storage_status["status"] = "UP"
            storage_status["free_mb"] = round(free / (1024 * 1024), 2)
            storage_status["writable"] = True
        except Exception as e:
            storage_status["status"] = "ERROR"
            storage_status["error"] = str(e)

        overall = "HEALTHY"
        if db_status.get("status") != "UP":
            overall = "UNHEALTHY"
        elif storage_status.get("status") != "UP":
            overall = "DEGRADED"

        return PlatformSystemHealthResponse(
            status=overall,
            database=db_status,
            redis=redis_status,
            celery={"broker": settings.CELERY_BROKER_URL, "status": "CONNECTED" if redis_status.get("status") == "UP" else "STANDBY"},
            storage=storage_status,
            timestamp=datetime.now(timezone.utc),
        )
