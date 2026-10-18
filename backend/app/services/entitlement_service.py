import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func, desc, update
from fastapi import HTTPException, status

from app.models.base import utc_now
from app.models.enums import (
    SubscriptionTier,
    SubscriptionStatus,
    BillingInterval,
    PaymentGateway,
    QuotaResourceType,
    BillingCurrency,
)
from app.models.billing import (
    SubscriptionPlan,
    AgencySubscription,
    SubscriptionHistory,
    FeatureEntitlement,
    EntitlementOverride,
    UsageMeter,
    UsageRecord,
    UsageReservation,
)
from app.schemas.billing import UsageMeterRead, UsageOverviewResponse

logger = logging.getLogger(__name__)

# Default canonical plan parameters
DEFAULT_PLANS_DATA = [
    {
        "name": "Free Tier",
        "slug": "free",
        "tier": SubscriptionTier.FREE,
        "billing_interval": BillingInterval.MONTHLY,
        "price_inr": 0.00,
        "price_usd": 0.00,
        "max_active_jobs": 2,
        "max_recruiters": 1,
        "max_candidates_monthly": 50,
        "max_resume_storage_mb": 250,
        "max_ai_tokens_monthly": 50000,
        "max_interviews_monthly": 10,
        "max_workflow_runs_monthly": 0,
        "features": {
            "analytics": "basic",
            "predictive_analytics": False,
            "ai_copilot": "basic",
            "calendar_integrations": False,
            "workflow_automation": False,
            "enterprise_governance": False,
            "export_reports": False,
        },
    },
    {
        "name": "Starter Plan",
        "slug": "starter",
        "tier": SubscriptionTier.STARTER,
        "billing_interval": BillingInterval.MONTHLY,
        "price_inr": 4999.00,
        "price_usd": 69.00,
        "max_active_jobs": 10,
        "max_recruiters": 3,
        "max_candidates_monthly": 500,
        "max_resume_storage_mb": 2500,
        "max_ai_tokens_monthly": 500000,
        "max_interviews_monthly": 100,
        "max_workflow_runs_monthly": 50,
        "features": {
            "analytics": "standard",
            "predictive_analytics": False,
            "ai_copilot": "standard",
            "calendar_integrations": True,
            "workflow_automation": True,
            "enterprise_governance": False,
            "export_reports": True,
        },
    },
    {
        "name": "Professional Plan",
        "slug": "professional",
        "tier": SubscriptionTier.PROFESSIONAL,
        "billing_interval": BillingInterval.MONTHLY,
        "price_inr": 14999.00,
        "price_usd": 199.00,
        "max_active_jobs": 30,
        "max_recruiters": 10,
        "max_candidates_monthly": 2500,
        "max_resume_storage_mb": 15000,
        "max_ai_tokens_monthly": 2500000,
        "max_interviews_monthly": 500,
        "max_workflow_runs_monthly": 500,
        "features": {
            "analytics": "advanced",
            "predictive_analytics": False,
            "ai_copilot": "advanced",
            "calendar_integrations": True,
            "workflow_automation": True,
            "enterprise_governance": True,
            "export_reports": True,
        },
    },
    {
        "name": "Business Plan",
        "slug": "business",
        "tier": SubscriptionTier.BUSINESS,
        "billing_interval": BillingInterval.MONTHLY,
        "price_inr": 39999.00,
        "price_usd": 499.00,
        "max_active_jobs": 100,
        "max_recruiters": 30,
        "max_candidates_monthly": 10000,
        "max_resume_storage_mb": 60000,
        "max_ai_tokens_monthly": 10000000,
        "max_interviews_monthly": 2000,
        "max_workflow_runs_monthly": 3000,
        "features": {
            "analytics": "full",
            "predictive_analytics": True,
            "ai_copilot": "full",
            "calendar_integrations": True,
            "workflow_automation": True,
            "enterprise_governance": True,
            "export_reports": True,
        },
    },
    {
        "name": "Enterprise Plan",
        "slug": "enterprise",
        "tier": SubscriptionTier.ENTERPRISE,
        "billing_interval": BillingInterval.MONTHLY,
        "price_inr": 99999.00,
        "price_usd": 1299.00,
        "max_active_jobs": -1,  # unlimited
        "max_recruiters": -1,   # unlimited
        "max_candidates_monthly": -1,
        "max_resume_storage_mb": -1,
        "max_ai_tokens_monthly": 50000000,
        "max_interviews_monthly": -1,
        "max_workflow_runs_monthly": -1,
        "features": {
            "analytics": "custom",
            "predictive_analytics": True,
            "ai_copilot": "dedicated",
            "calendar_integrations": True,
            "workflow_automation": True,
            "enterprise_governance": True,
            "export_reports": True,
            "custom_branding": True,
            "dedicated_sla": True,
        },
    },
]


class EntitlementService:
    """
    Centralized SaaS entitlement and quota metering service.
    Guarantees atomic quota enforcement, concurrency protection, and policy limits.
    """

    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id

    def ensure_default_plans(self_or_db, db_arg: Optional[Session] = None) -> List[SubscriptionPlan]:
        """Ensures the 5 canonical subscription plans exist in the catalog."""
        if db_arg is not None:
            db = db_arg
        elif hasattr(self_or_db, "db"):
            db = self_or_db.db
        else:
            db = self_or_db

        plans = db.scalars(select(SubscriptionPlan)).all()
        if not plans:
            created = []
            for item in DEFAULT_PLANS_DATA:
                plan = SubscriptionPlan(
                    name=item["name"],
                    slug=item["slug"],
                    tier=item["tier"],
                    billing_interval=item["billing_interval"],
                    price_inr=item["price_inr"],
                    price_usd=item["price_usd"],
                    max_active_jobs=item["max_active_jobs"],
                    max_recruiters=item["max_recruiters"],
                    max_candidates_monthly=item["max_candidates_monthly"],
                    max_resume_storage_mb=item["max_resume_storage_mb"],
                    max_ai_tokens_monthly=item["max_ai_tokens_monthly"],
                    max_interviews_monthly=item["max_interviews_monthly"],
                    max_workflow_runs_monthly=item["max_workflow_runs_monthly"],
                    features_json=json.dumps(item["features"]),
                    is_active=True,
                )
                db.add(plan)
                created.append(plan)
            db.commit()
            return created
        return list(plans)

    def get_or_create_subscription(self) -> AgencySubscription:
        """
        Retrieves the active agency subscription or automatically enrolls the agency in the FREE plan.
        """
        sub = self.db.scalar(
            select(AgencySubscription).where(AgencySubscription.agency_id == self.agency_id)
        )
        if not sub:
            self.ensure_default_plans()
            free_plan = self.db.scalar(
                select(SubscriptionPlan).where(SubscriptionPlan.tier == SubscriptionTier.FREE)
            )
            now = utc_now()
            sub = AgencySubscription(
                agency_id=self.agency_id,
                plan_id=free_plan.id,
                status=SubscriptionStatus.ACTIVE,
                billing_interval=BillingInterval.MONTHLY,
                currency=BillingCurrency.INR,
                current_period_start=now,
                current_period_end=now + timedelta(days=3650),  # Free plan is indefinite
                cancel_at_period_end=False,
                payment_gateway=PaymentGateway.MOCK,
            )
            self.db.add(sub)
            self.db.commit()
            self.db.refresh(sub)

        return sub

    def check_feature_access(self, feature_key: str) -> bool:
        """
        Verifies whether an agency's subscription plan entitles access to a specific feature flag.
        """
        sub = self.get_or_create_subscription()
        plan = self.db.get(SubscriptionPlan, sub.plan_id)
        if not plan:
            return False

        features = json.loads(plan.features_json) if plan.features_json else {}
        val = features.get(feature_key)
        if val is True:
            return True
        if isinstance(val, str) and val.lower() not in ["false", "none", "0"]:
            return True

        # Check explicit feature entitlement table
        ent = self.db.scalar(
            select(FeatureEntitlement).where(
                and_(
                    FeatureEntitlement.agency_id == self.agency_id,
                    FeatureEntitlement.feature_key == feature_key,
                )
            )
        )
        if ent and ent.is_enabled:
            return True

        return False

    def require_feature(self, feature_key: str, error_message: Optional[str] = None):
        """Raises 403 Forbidden if the agency is not entitled to the feature."""
        if not self.check_feature_access(feature_key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_message or f"Feature '{feature_key}' is not included in your current subscription plan. Please upgrade to access this capability.",
            )

    def _get_current_period_bounds(self) -> Tuple[datetime, datetime]:
        """Calculates current monthly billing-period start and end."""
        sub = self.get_or_create_subscription()
        now = utc_now()
        start = sub.current_period_start
        end = sub.current_period_end
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if now > end:
            # Shift period window forward
            start = end
            end = start + timedelta(days=30)
        return start, end

    def get_or_create_meter(self, resource_type: QuotaResourceType) -> UsageMeter:
        """
        Retrieves or creates the monthly usage meter for a specific quota resource.
        """
        period_start, period_end = self._get_current_period_bounds()
        meter = self.db.scalar(
            select(UsageMeter).where(
                and_(
                    UsageMeter.agency_id == self.agency_id,
                    UsageMeter.resource_type == resource_type,
                    UsageMeter.period_start == period_start,
                )
            )
        )
        if not meter:
            sub = self.get_or_create_subscription()
            plan = self.db.get(SubscriptionPlan, sub.plan_id)
            
            # Map plan limit to resource type
            limit_map = {
                QuotaResourceType.ACTIVE_JOBS: plan.max_active_jobs,
                QuotaResourceType.RECRUITERS: plan.max_recruiters,
                QuotaResourceType.CANDIDATES_MONTHLY: plan.max_candidates_monthly,
                QuotaResourceType.RESUME_STORAGE_MB: plan.max_resume_storage_mb,
                QuotaResourceType.AI_TOKENS_MONTHLY: plan.max_ai_tokens_monthly,
                QuotaResourceType.INTERVIEWS_MONTHLY: plan.max_interviews_monthly,
                QuotaResourceType.WORKFLOW_RUNS_MONTHLY: plan.max_workflow_runs_monthly,
            }
            limit = limit_map.get(resource_type, 100)
            is_unlimited = limit == -1

            # Check for administrative override
            override = self.db.scalar(
                select(EntitlementOverride).where(
                    and_(
                        EntitlementOverride.agency_id == self.agency_id,
                        EntitlementOverride.resource_type == resource_type,
                        or_(
                            EntitlementOverride.expires_at.is_(None),
                            EntitlementOverride.expires_at > utc_now(),
                        ),
                    )
                )
            )
            if override:
                if override.is_unlimited:
                    is_unlimited = True
                    limit = -1
                else:
                    limit = override.override_limit

            soft_limit = int(limit * 0.8) if limit > 0 else 0
            hard_limit = limit if limit > 0 else 0

            meter = UsageMeter(
                agency_id=self.agency_id,
                resource_type=resource_type,
                period_start=period_start,
                period_end=period_end,
                current_usage=0,
                soft_limit=soft_limit,
                hard_limit=hard_limit,
                is_unlimited=is_unlimited,
                version=1,
            )
            self.db.add(meter)
            self.db.commit()
            self.db.refresh(meter)

        return meter

    def check_quota(
        self,
        resource_type: QuotaResourceType,
        requested_units: int = 1,
    ) -> Tuple[bool, UsageMeter, Optional[str]]:
        """
        Evaluates whether an agency can consume the requested quota without breach.
        Returns: (is_allowed, meter, warning_or_error_message)
        """
        meter = self.get_or_create_meter(resource_type)
        if meter.is_unlimited:
            return True, meter, None

        projected = meter.current_usage + requested_units
        if projected > meter.hard_limit:
            err = (
                f"Subscription quota exceeded for {resource_type.value}. "
                f"Limit: {meter.hard_limit}, Current usage: {meter.current_usage}, Requested: {requested_units}. "
                "Please upgrade your plan to increase limits."
            )
            return False, meter, err

        warning = None
        if meter.soft_limit > 0 and projected >= meter.soft_limit:
            warning = f"Warning: {resource_type.value} has reached {int((projected / meter.hard_limit) * 100)}% of monthly capacity."

        return True, meter, warning

    def consume_quota(
        self,
        resource_type: QuotaResourceType,
        units: int = 1,
        idempotency_key: Optional[str] = None,
        operation_reference: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> UsageMeter:
        """
        Atomically records quota consumption with database concurrency versioning and audit logging.
        Prevents double-counting if an idempotency_key is replayed.
        """
        # Idempotency check
        if idempotency_key:
            existing = self.db.scalar(
                select(UsageRecord).where(
                    and_(
                        UsageRecord.agency_id == self.agency_id,
                        UsageRecord.idempotency_key == idempotency_key,
                    )
                )
            )
            if existing:
                return self.get_or_create_meter(resource_type)

        # Lock the usage meter row for atomic concurrency in PostgreSQL
        period_start, period_end = self._get_current_period_bounds()
        meter = self.db.scalar(
            select(UsageMeter)
            .where(
                and_(
                    UsageMeter.agency_id == self.agency_id,
                    UsageMeter.resource_type == resource_type,
                    UsageMeter.period_start == period_start,
                )
            )
            .with_for_update()
        )
        if not meter:
            meter = self.get_or_create_meter(resource_type)
            meter = self.db.scalar(
                select(UsageMeter).where(UsageMeter.id == meter.id).with_for_update()
            ) or meter

        if not meter.is_unlimited:
            projected = meter.current_usage + units
            if projected > meter.hard_limit:
                err = (
                    f"Subscription quota exceeded for {resource_type.value}. "
                    f"Limit: {meter.hard_limit}, Current usage: {meter.current_usage}, Requested: {units}. "
                    "Please upgrade your plan to increase limits."
                )
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": "QUOTA_EXCEEDED",
                        "resource_type": resource_type.value,
                        "current_usage": meter.current_usage,
                        "hard_limit": meter.hard_limit,
                        "message": err,
                        "upgrade_url": "/settings/billing",
                    },
                )

        # Atomic versioned increment
        meter.current_usage += units
        meter.version += 1
        meter.updated_at = utc_now()

        # Record audit item
        record = UsageRecord(
            agency_id=self.agency_id,
            resource_type=resource_type,
            quantity=units,
            idempotency_key=idempotency_key,
            operation_reference=operation_reference,
            user_id=user_id,
            created_at=utc_now(),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(meter)

        return meter

    def get_usage_overview(self) -> UsageOverviewResponse:
        """Gathers aggregate consumption stats across all 7 quota resource types."""
        sub = self.get_or_create_subscription()
        plan = self.db.get(SubscriptionPlan, sub.plan_id)
        period_start, period_end = self._get_current_period_bounds()

        meters_dict = {}
        has_warnings = False
        has_exhausted = False

        for r_type in QuotaResourceType:
            m = self.get_or_create_meter(r_type)
            util_pct = (
                0.0
                if m.is_unlimited or m.hard_limit == 0
                else round((m.current_usage / m.hard_limit) * 100, 1)
            )
            is_soft = m.soft_limit > 0 and m.current_usage >= m.soft_limit
            is_hard = not m.is_unlimited and m.current_usage >= m.hard_limit

            if is_soft:
                has_warnings = True
            if is_hard:
                has_exhausted = True

            meters_dict[r_type.value] = UsageMeterRead(
                resource_type=r_type,
                current_usage=m.current_usage,
                soft_limit=m.soft_limit,
                hard_limit=m.hard_limit,
                is_unlimited=m.is_unlimited,
                utilization_pct=util_pct,
                is_soft_limit_exceeded=is_soft,
                is_hard_limit_exceeded=is_hard,
            )

        return UsageOverviewResponse(
            agency_id=self.agency_id,
            plan_name=plan.name if plan else "Free",
            tier=plan.tier if plan else SubscriptionTier.FREE,
            period_start=period_start,
            period_end=period_end,
            meters=meters_dict,
            has_warnings=has_warnings,
            has_exhausted_quotas=has_exhausted,
        )
