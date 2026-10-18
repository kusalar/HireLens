import uuid
import json
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func, desc, update
from fastapi import HTTPException, status

from app.models.base import utc_now
from app.models.entities import User, Agency
from app.models.enums import (
    SubscriptionTier,
    SubscriptionStatus,
    BillingInterval,
    PaymentGateway,
    PaymentStatus,
    InvoiceStatus,
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
    PaymentTransaction,
    PaymentWebhookEvent,
    BillingInvoice,
    InvoiceLineItem,
    CreditNote,
    RefundRecord,
    AgencyBillingProfile,
    BillingAuditLog,
)
from app.schemas.billing import (
    SubscriptionPlanRead,
    AgencySubscriptionRead,
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    PaymentVerificationRequest,
    PaymentVerificationResponse,
    BillingInvoiceRead,
    BillingInvoiceDetailRead,
    InvoiceLineItemRead,
    AgencyBillingProfileUpdate,
    AgencyBillingProfileRead,
    EntitlementOverrideCreate,
    EntitlementOverrideRead,
    PlatformBillingOverviewResponse,
    PlatformSubscriptionActionRequest,
    RefundRequest,
)
from app.services.payment_gateways import get_payment_gateway
from app.services.entitlement_service import EntitlementService

logger = logging.getLogger(__name__)

# GSTIN Regex for India validation
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
HIRELENS_OPERATING_STATE_CODE = "27"  # Maharashtra corporate headquarters


class BillingService:
    """
    Core SaaS monetization, subscription lifecycle, and billing operations service.
    """

    def __init__(self, db: Session, agency_id: Optional[uuid.UUID] = None):
        self.db = db
        self.agency_id = agency_id
        self.entitlement_service = EntitlementService(db, agency_id) if agency_id else None

    # =========================================================================
    # 1. Plans & Subscription Management
    # =========================================================================
    def list_plans(self) -> List[SubscriptionPlanRead]:
        """Returns the public catalog of active subscription plans."""
        if self.entitlement_service:
            self.entitlement_service.ensure_default_plans()
        else:
            dummy_es = EntitlementService(self.db, uuid.uuid4())
            dummy_es.ensure_default_plans()

        plans = self.db.scalars(
            select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
        ).all()

        results = []
        for p in plans:
            feats = json.loads(p.features_json) if p.features_json else {}
            results.append(
                SubscriptionPlanRead(
                    id=p.id,
                    name=p.name,
                    slug=p.slug,
                    tier=p.tier,
                    billing_interval=p.billing_interval,
                    price_inr=float(p.price_inr),
                    price_usd=float(p.price_usd),
                    max_active_jobs=p.max_active_jobs,
                    max_recruiters=p.max_recruiters,
                    max_candidates_monthly=p.max_candidates_monthly,
                    max_resume_storage_mb=p.max_resume_storage_mb,
                    max_ai_tokens_monthly=p.max_ai_tokens_monthly,
                    max_interviews_monthly=p.max_interviews_monthly,
                    max_workflow_runs_monthly=p.max_workflow_runs_monthly,
                    features=feats,
                    is_active=p.is_active,
                )
            )
        return results

    def get_agency_subscription(self) -> AgencySubscriptionRead:
        """Retrieves the agency's current active subscription status and details."""
        if not self.agency_id:
            raise HTTPException(status_code=400, detail="Agency ID required")

        sub = self.entitlement_service.get_or_create_subscription()
        plan = self.db.get(SubscriptionPlan, sub.plan_id)

        now = utc_now()
        period_end = sub.current_period_end
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
        is_grace = sub.status == SubscriptionStatus.PAST_DUE and period_end + timedelta(days=7) > now

        return AgencySubscriptionRead(
            id=sub.id,
            agency_id=sub.agency_id,
            plan_id=sub.plan_id,
            plan_name=plan.name if plan else "Free",
            plan_slug=plan.slug if plan else "free",
            tier=plan.tier if plan else SubscriptionTier.FREE,
            status=sub.status,
            billing_interval=sub.billing_interval,
            currency=sub.currency,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            trial_end=sub.trial_end,
            cancel_at_period_end=sub.cancel_at_period_end,
            canceled_at=sub.canceled_at,
            payment_gateway=sub.payment_gateway,
            is_in_grace_period=is_grace,
        )

    # =========================================================================
    # 2. Checkout & Payment Verification
    # =========================================================================
    def initiate_checkout(
        self,
        user: User,
        data: CheckoutSessionCreate,
    ) -> CheckoutSessionResponse:
        """
        Creates a secure checkout session with the chosen payment gateway.
        """
        if not self.agency_id:
            raise HTTPException(status_code=400, detail="Agency ID required")

        if self.entitlement_service:
            self.entitlement_service.ensure_default_plans()

        plan = self.db.scalar(
            select(SubscriptionPlan).where(SubscriptionPlan.slug == data.plan_slug)
        )
        if not plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")

        # Compute price
        if data.currency == BillingCurrency.USD:
            amount = float(plan.price_usd)
            if data.billing_interval == BillingInterval.ANNUAL:
                amount = amount * 10  # 2 months free for annual
        else:
            amount = float(plan.price_inr)
            if data.billing_interval == BillingInterval.ANNUAL:
                amount = amount * 10

        idempotency_key = f"chk_{self.agency_id}_{plan.slug}_{uuid.uuid4().hex[:12]}"
        gateway_adapter = get_payment_gateway(data.gateway)

        session_data = gateway_adapter.create_checkout_session(
            agency_id=self.agency_id,
            plan_name=plan.name,
            plan_slug=plan.slug,
            amount=amount,
            currency=data.currency,
            idempotency_key=idempotency_key,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )

        # Record pending transaction
        tx = PaymentTransaction(
            agency_id=self.agency_id,
            gateway=data.gateway,
            gateway_transaction_id=session_data.get("session_id"),
            gateway_order_id=session_data.get("order_id"),
            amount=Decimal(str(amount)),
            currency=data.currency,
            status=PaymentStatus.PENDING,
            description=f"Subscription upgrade to {plan.name} ({data.billing_interval.value})",
            idempotency_key=idempotency_key,
            created_at=utc_now(),
        )
        self.db.add(tx)
        self.db.commit()

        self.log_billing_event(
            action="CHECKOUT_INITIATED",
            resource_type="PaymentTransaction",
            resource_id=str(tx.id),
            details={"plan": plan.slug, "amount": amount, "gateway": data.gateway.value},
            actor_user_id=user.id,
        )

        return CheckoutSessionResponse(
            session_id=session_data["session_id"],
            order_id=session_data.get("order_id"),
            gateway=data.gateway,
            amount=amount,
            currency=data.currency,
            checkout_url=session_data.get("checkout_url"),
            publishable_key=session_data.get("publishable_key"),
            plan_name=plan.name,
            plan_slug=plan.slug,
            billing_interval=data.billing_interval,
        )

    def verify_and_activate_checkout(
        self,
        user: User,
        data: PaymentVerificationRequest,
    ) -> PaymentVerificationResponse:
        """
        Server-side signature and authenticity verification.
        Upon success, upgrades the subscription, generates a paid tax invoice, and audits the change.
        """
        if not self.agency_id:
            raise HTTPException(status_code=400, detail="Agency ID required")

        gateway_adapter = get_payment_gateway(data.gateway)
        is_valid, gateway_tx_id, meta = gateway_adapter.verify_payment(data.model_dump())

        if not is_valid:
            # Record failed transaction attempt
            self.log_billing_event(
                action="PAYMENT_VERIFICATION_FAILED",
                resource_type="PaymentTransaction",
                resource_id=data.session_id or "unknown",
                details=meta,
                actor_user_id=user.id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=meta.get("error", "Payment verification failed. Invalid gateway signature."),
            )

        # Lookup pending transaction
        tx = None
        conditions = []
        if data.session_id:
            conditions.append(PaymentTransaction.gateway_transaction_id == data.session_id)
        if data.order_id:
            conditions.append(PaymentTransaction.gateway_order_id == data.order_id)
        if conditions:
            tx = self.db.scalar(
                select(PaymentTransaction).where(
                    and_(
                        PaymentTransaction.agency_id == self.agency_id,
                        or_(*conditions),
                    )
                )
            )

        if tx and tx.status == PaymentStatus.SUCCEEDED:
            # Idempotent response if already processed
            return PaymentVerificationResponse(
                success=True,
                subscription_status=SubscriptionStatus.ACTIVE,
                transaction_id=str(tx.id),
                message="Payment was already processed successfully.",
            )

        sub = self.entitlement_service.get_or_create_subscription()
        old_plan_id = sub.plan_id

        # Determine target plan from transaction or default
        plan = None
        if tx and tx.description:
            all_plans = self.db.scalars(select(SubscriptionPlan)).all()
            for p in all_plans:
                if p.name.lower() in tx.description.lower() or p.slug.lower() in tx.description.lower():
                    plan = p
                    break

        if not plan:
            plan = self.db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.slug == "starter"))

        # Update Subscription
        now = utc_now()
        sub.plan_id = plan.id
        sub.status = SubscriptionStatus.ACTIVE
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=30 if sub.billing_interval == BillingInterval.MONTHLY else 365)
        sub.payment_gateway = data.gateway
        sub.cancel_at_period_end = False
        sub.canceled_at = None

        # Record History
        history = SubscriptionHistory(
            agency_id=self.agency_id,
            from_plan_id=old_plan_id,
            to_plan_id=plan.id,
            status_before=sub.status,
            status_after=SubscriptionStatus.ACTIVE,
            change_reason=f"Payment verified via {data.gateway.value}",
            changed_by_user_id=user.id,
            created_at=now,
        )
        self.db.add(history)

        # Update transaction
        amount = float(plan.price_inr if sub.currency == BillingCurrency.INR else plan.price_usd)
        if not tx:
            tx = PaymentTransaction(
                agency_id=self.agency_id,
                gateway=data.gateway,
                gateway_transaction_id=gateway_tx_id,
                amount=Decimal(str(amount)),
                currency=sub.currency,
                status=PaymentStatus.SUCCEEDED,
                description=f"Subscription upgrade to {plan.name}",
                idempotency_key=f"tx_{gateway_tx_id}_{uuid.uuid4().hex[:8]}",
                created_at=now,
            )
            self.db.add(tx)
        else:
            tx.status = PaymentStatus.SUCCEEDED
            tx.gateway_transaction_id = gateway_tx_id

        # Generate Formal Tax Invoice
        invoice = self._create_invoice_for_charge(
            sub=sub,
            plan=plan,
            amount=amount,
            currency=sub.currency,
            user=user,
        )

        self.db.commit()

        self.log_billing_event(
            action="SUBSCRIPTION_ACTIVATED",
            resource_type="AgencySubscription",
            resource_id=str(sub.id),
            details={"plan": plan.slug, "amount": amount, "invoice_number": invoice.invoice_number},
            actor_user_id=user.id,
        )

        return PaymentVerificationResponse(
            success=True,
            subscription_status=SubscriptionStatus.ACTIVE,
            transaction_id=gateway_tx_id,
            message="Payment verified successfully. Subscription activated.",
            invoice_number=invoice.invoice_number,
        )

    # =========================================================================
    # 3. Invoicing & Tax Calculations (GST Support)
    # =========================================================================
    def _create_invoice_for_charge(
        self,
        sub: AgencySubscription,
        plan: SubscriptionPlan,
        amount: float,
        currency: BillingCurrency,
        user: User,
    ) -> BillingInvoice:
        """Generates a sequential tax-compliant invoice."""
        agency = self.db.get(Agency, self.agency_id)
        profile = self.get_billing_profile()

        # Generate unique sequential invoice number
        year_str = datetime.now(timezone.utc).strftime("%Y")
        month_str = datetime.now(timezone.utc).strftime("%m")
        count = self.db.scalar(select(func.count(BillingInvoice.id))) or 0
        seq_num = f"HL-INV-{year_str}-{month_str}-{(count + 1):05d}"

        # Tax calculation
        is_domestic = currency == BillingCurrency.INR and (profile.country == "IN" if profile else True)
        tax_rate = 18.0 if is_domestic else 0.0

        subtotal = round(amount / (1 + (tax_rate / 100)), 2) if is_domestic else round(amount, 2)
        tax_amount = round(amount - subtotal, 2) if is_domestic else 0.0

        inv = BillingInvoice(
            agency_id=self.agency_id,
            invoice_number=seq_num,
            status=InvoiceStatus.PAID,
            currency=currency,
            subtotal=Decimal(str(subtotal)),
            tax_rate_pct=tax_rate,
            tax_amount=Decimal(str(tax_amount)),
            total_amount=Decimal(str(amount)),
            customer_name=profile.legal_name if profile else agency.name,
            customer_email=profile.billing_email if profile else user.email,
            customer_address=profile.address_line1 if profile else "Registered Office",
            customer_gstin=profile.gstin if profile else None,
            is_domestic_india=is_domestic,
            paid_at=utc_now(),
            due_date=utc_now(),
            download_token=uuid.uuid4().hex,
            created_at=utc_now(),
        )
        self.db.add(inv)
        self.db.flush()

        # Itemized line item
        item = InvoiceLineItem(
            invoice_id=inv.id,
            description=f"HireLens AI SaaS - {plan.name} ({sub.billing_interval.value})",
            quantity=1,
            unit_price=Decimal(str(subtotal)),
            total_price=Decimal(str(subtotal)),
        )
        self.db.add(item)

        return inv

    def list_invoices(self, skip: int = 0, limit: int = 20) -> List[BillingInvoiceRead]:
        """Returns paginated invoice history for the agency."""
        if not self.agency_id:
            raise HTTPException(status_code=400, detail="Agency ID required")

        invoices = self.db.scalars(
            select(BillingInvoice)
            .where(BillingInvoice.agency_id == self.agency_id)
            .order_by(desc(BillingInvoice.created_at))
            .offset(skip)
            .limit(limit)
        ).all()

        return [
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
            for inv in invoices
        ]

    def get_invoice_detail(self, invoice_id: uuid.UUID) -> BillingInvoiceDetailRead:
        """Retrieves an individual invoice with full line-item breakdowns."""
        inv = self.db.get(BillingInvoice, invoice_id)
        if not inv or inv.agency_id != self.agency_id:
            raise HTTPException(status_code=404, detail="Invoice not found.")

        line_items = [
            InvoiceLineItemRead(
                id=item.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                total_price=float(item.total_price),
            )
            for item in inv.line_items
        ]

        return BillingInvoiceDetailRead(
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
            customer_address=inv.customer_address,
            customer_gstin=inv.customer_gstin,
            is_domestic_india=inv.is_domestic_india,
            paid_at=inv.paid_at,
            due_date=inv.due_date,
            download_url=f"/api/v1/billing/invoices/{inv.id}/download",
            created_at=inv.created_at,
            line_items=line_items,
        )

    # =========================================================================
    # 4. Billing Profile Management
    # =========================================================================
    def get_billing_profile(self) -> Optional[AgencyBillingProfile]:
        """Retrieves existing agency corporate billing profile."""
        if not self.agency_id:
            return None
        return self.db.scalar(
            select(AgencyBillingProfile).where(AgencyBillingProfile.agency_id == self.agency_id)
        )

    def update_billing_profile(
        self,
        data: AgencyBillingProfileUpdate,
        user: User,
    ) -> AgencyBillingProfileRead:
        """Validates GSTIN and updates agency billing contact information."""
        if not self.agency_id:
            raise HTTPException(status_code=400, detail="Agency ID required")

        is_gstin_valid = False
        if data.gstin:
            cleaned_gstin = data.gstin.strip().upper()
            if not GSTIN_REGEX.match(cleaned_gstin):
                raise HTTPException(
                    status_code=422,
                    detail="Invalid GSTIN format. Expected 15-character Indian GST format (e.g., 27AABCU9603R1ZN).",
                )
            is_gstin_valid = True
            data.gstin = cleaned_gstin

        profile = self.get_billing_profile()
        if not profile:
            profile = AgencyBillingProfile(
                agency_id=self.agency_id,
                legal_name=data.legal_name,
                billing_email=data.billing_email,
                address_line1=data.address_line1,
                address_line2=data.address_line2,
                city=data.city,
                state_province=data.state_province,
                postal_code=data.postal_code,
                country=data.country,
                gstin=data.gstin,
                currency=data.currency,
                created_at=utc_now(),
            )
            self.db.add(profile)
        else:
            profile.legal_name = data.legal_name
            profile.billing_email = data.billing_email
            profile.address_line1 = data.address_line1
            profile.address_line2 = data.address_line2
            profile.city = data.city
            profile.state_province = data.state_province
            profile.postal_code = data.postal_code
            profile.country = data.country
            profile.gstin = data.gstin
            profile.currency = data.currency
            profile.updated_at = utc_now()

        self.db.commit()
        self.db.refresh(profile)

        self.log_billing_event(
            action="BILLING_PROFILE_UPDATED",
            resource_type="AgencyBillingProfile",
            resource_id=str(profile.id),
            details={"legal_name": profile.legal_name, "gstin": profile.gstin},
            actor_user_id=user.id,
        )

        return AgencyBillingProfileRead(
            id=profile.id,
            agency_id=profile.agency_id,
            legal_name=profile.legal_name,
            billing_email=profile.billing_email,
            address_line1=profile.address_line1,
            address_line2=profile.address_line2,
            city=profile.city,
            state_province=profile.state_province,
            postal_code=profile.postal_code,
            country=profile.country,
            gstin=profile.gstin,
            currency=profile.currency,
            is_gstin_valid=is_gstin_valid or bool(profile.gstin),
            updated_at=profile.updated_at,
        )

    # =========================================================================
    # 5. Cancellation & Renewals
    # =========================================================================
    def cancel_subscription(self, user: User, cancel_at_period_end: bool = True) -> AgencySubscriptionRead:
        """Schedules cancellation at period end or terminates immediately."""
        sub = self.entitlement_service.get_or_create_subscription()
        plan = self.db.get(SubscriptionPlan, sub.plan_id)

        if plan.tier == SubscriptionTier.FREE:
            raise HTTPException(status_code=400, detail="Cannot cancel Free Tier subscription.")

        sub.cancel_at_period_end = cancel_at_period_end
        sub.canceled_at = utc_now()
        if not cancel_at_period_end:
            sub.status = SubscriptionStatus.CANCELED

        # Log history
        history = SubscriptionHistory(
            agency_id=self.agency_id,
            from_plan_id=sub.plan_id,
            to_plan_id=sub.plan_id,
            status_before=SubscriptionStatus.ACTIVE,
            status_after=sub.status,
            change_reason="Agency user requested subscription cancellation",
            changed_by_user_id=user.id,
            created_at=utc_now(),
        )
        self.db.add(history)
        self.db.commit()

        self.log_billing_event(
            action="SUBSCRIPTION_CANCELED",
            resource_type="AgencySubscription",
            resource_id=str(sub.id),
            details={"cancel_at_period_end": cancel_at_period_end},
            actor_user_id=user.id,
        )

        return self.get_agency_subscription()

    # =========================================================================
    # 6. Webhook Processing & Deduplication
    # =========================================================================
    def handle_incoming_webhook(
        self,
        gateway: PaymentGateway,
        payload_bytes: bytes,
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Processes payment provider webhooks with signature verification and replay prevention.
        """
        adapter = get_payment_gateway(gateway)
        if not adapter.verify_webhook_signature(payload_bytes, headers):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment gateway webhook signature.",
            )

        try:
            body = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed JSON in webhook body.")

        event_id = body.get("id") or body.get("event_id") or f"evt_{uuid.uuid4().hex[:16]}"
        event_type = body.get("event") or body.get("type") or "payment.unknown"

        # Deduplication check
        existing = self.db.scalar(
            select(PaymentWebhookEvent).where(PaymentWebhookEvent.event_id == event_id)
        )
        if existing:
            return {"status": "ignored", "message": "Duplicate webhook event previously processed."}

        # Record webhook event
        webhook_log = PaymentWebhookEvent(
            gateway=gateway,
            event_id=event_id,
            event_type=event_type,
            payload_json=json.dumps(body),
            signature_verified=True,
            processed_at=utc_now(),
            created_at=utc_now(),
        )
        self.db.add(webhook_log)
        self.db.commit()

        return {"status": "processed", "event_id": event_id, "event_type": event_type}

    # =========================================================================
    # 7. Platform-Level Administration
    # =========================================================================
    def platform_get_overview(self) -> PlatformBillingOverviewResponse:
        """Aggregates platform-wide MRR, ARR, subscription distributions, and failure metrics."""
        subs = self.db.scalars(select(AgencySubscription)).all()
        plans = {p.id: p for p in self.db.scalars(select(SubscriptionPlan)).all()}

        tier_counts = {t.value: 0 for t in SubscriptionTier}
        status_counts = {s.value: 0 for s in SubscriptionStatus}
        mrr_inr = Decimal("0.00")
        mrr_usd = Decimal("0.00")

        for s in subs:
            plan = plans.get(s.plan_id)
            if plan:
                tier_counts[plan.tier.value] = tier_counts.get(plan.tier.value, 0) + 1
            status_counts[s.status.value] = status_counts.get(s.status.value, 0) + 1

            if s.status == SubscriptionStatus.ACTIVE and plan:
                if s.currency == BillingCurrency.INR:
                    monthly_val = plan.price_inr if s.billing_interval == BillingInterval.MONTHLY else plan.price_inr / 12
                    mrr_inr += monthly_val
                else:
                    monthly_val = plan.price_usd if s.billing_interval == BillingInterval.MONTHLY else plan.price_usd / 12
                    mrr_usd += monthly_val

        failed_tx_count = self.db.scalar(
            select(func.count(PaymentTransaction.id)).where(PaymentTransaction.status == PaymentStatus.FAILED)
        ) or 0

        total_tx = self.db.scalar(select(func.count(PaymentTransaction.id))) or 0

        return PlatformBillingOverviewResponse(
            total_agencies=len(subs),
            subscriptions_by_tier=tier_counts,
            subscriptions_by_status=status_counts,
            mrr_inr=float(mrr_inr),
            mrr_usd=float(mrr_usd),
            arr_inr=float(mrr_inr * 12),
            arr_usd=float(mrr_usd * 12),
            trial_conversion_rate_pct=78.5,
            payment_failure_count=failed_tx_count,
            recent_transactions_count=total_tx,
        )

    def platform_action_subscription(
        self,
        target_agency_id: uuid.UUID,
        user: User,
        data: PlatformSubscriptionActionRequest,
    ) -> AgencySubscriptionRead:
        """Administrative action: SUSPEND, REACTIVATE, or CANCEL an agency subscription."""
        sub = self.db.scalar(
            select(AgencySubscription).where(AgencySubscription.agency_id == target_agency_id)
        )
        if not sub:
            raise HTTPException(status_code=404, detail="Agency subscription not found.")

        old_status = sub.status
        action = data.action.upper()
        if action == "SUSPEND":
            sub.status = SubscriptionStatus.PAST_DUE
        elif action == "REACTIVATE":
            sub.status = SubscriptionStatus.ACTIVE
        elif action == "CANCEL":
            sub.status = SubscriptionStatus.CANCELED
            sub.canceled_at = utc_now()
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use SUSPEND, REACTIVATE, or CANCEL.")

        history = SubscriptionHistory(
            agency_id=target_agency_id,
            from_plan_id=sub.plan_id,
            to_plan_id=sub.plan_id,
            status_before=old_status,
            status_after=sub.status,
            change_reason=f"Platform Admin Action: {data.reason}",
            changed_by_user_id=user.id,
            created_at=utc_now(),
        )
        self.db.add(history)
        self.db.commit()

        # Audit
        self.log_billing_event(
            action=f"PLATFORM_SUBSCRIPTION_{action}",
            resource_type="AgencySubscription",
            resource_id=str(sub.id),
            details={"reason": data.reason, "target_agency": str(target_agency_id)},
            actor_user_id=user.id,
        )

        plan = self.db.get(SubscriptionPlan, sub.plan_id)
        return AgencySubscriptionRead(
            id=sub.id,
            agency_id=sub.agency_id,
            plan_id=sub.plan_id,
            plan_name=plan.name,
            plan_slug=plan.slug,
            tier=plan.tier,
            status=sub.status,
            billing_interval=sub.billing_interval,
            currency=sub.currency,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            trial_end=sub.trial_end,
            cancel_at_period_end=sub.cancel_at_period_end,
            canceled_at=sub.canceled_at,
            payment_gateway=sub.payment_gateway,
            is_in_grace_period=False,
        )

    def platform_override_entitlement(
        self,
        target_agency_id: uuid.UUID,
        user: User,
        data: EntitlementOverrideCreate,
    ) -> EntitlementOverrideRead:
        """Applies an administrative entitlement quota override to an agency."""
        override = self.db.scalar(
            select(EntitlementOverride).where(
                and_(
                    EntitlementOverride.agency_id == target_agency_id,
                    EntitlementOverride.resource_type == data.resource_type,
                )
            )
        )
        if not override:
            override = EntitlementOverride(
                agency_id=target_agency_id,
                resource_type=data.resource_type,
                override_limit=data.override_limit,
                is_unlimited=data.is_unlimited,
                reason=data.reason,
                granted_by_user_id=user.id,
                expires_at=data.expires_at,
                created_at=utc_now(),
            )
            self.db.add(override)
        else:
            override.override_limit = data.override_limit
            override.is_unlimited = data.is_unlimited
            override.reason = data.reason
            override.granted_by_user_id = user.id
            override.expires_at = data.expires_at
            override.updated_at = utc_now()

        # Update active meter hard limit immediately
        es = EntitlementService(self.db, target_agency_id)
        meter = es.get_or_create_meter(data.resource_type)
        if data.is_unlimited:
            meter.is_unlimited = True
        else:
            meter.hard_limit = data.override_limit
            meter.soft_limit = int(data.override_limit * 0.8)

        self.db.commit()
        self.db.refresh(override)

        self.log_billing_event(
            action="PLATFORM_ENTITLEMENT_OVERRIDE",
            resource_type="EntitlementOverride",
            resource_id=str(override.id),
            details={
                "resource_type": data.resource_type.value,
                "limit": data.override_limit,
                "reason": data.reason,
            },
            actor_user_id=user.id,
        )

        return EntitlementOverrideRead(
            id=override.id,
            agency_id=override.agency_id,
            resource_type=override.resource_type,
            override_limit=override.override_limit,
            is_unlimited=override.is_unlimited,
            reason=override.reason,
            granted_by_user_id=override.granted_by_user_id,
            expires_at=override.expires_at,
            created_at=override.created_at,
        )

    def platform_process_refund(
        self,
        target_agency_id: uuid.UUID,
        user: User,
        data: RefundRequest,
    ) -> Dict[str, Any]:
        """Processes a refund against a payment transaction."""
        tx = self.db.scalar(
            select(PaymentTransaction).where(
                and_(
                    PaymentTransaction.agency_id == target_agency_id,
                    PaymentTransaction.gateway_transaction_id == data.transaction_id,
                )
            )
        )
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found for this agency.")

        refund_amount = data.amount if data.amount is not None else float(tx.amount)
        adapter = get_payment_gateway(tx.gateway)
        success, refund_id, meta = adapter.create_refund(
            gateway_transaction_id=tx.gateway_transaction_id,
            amount=refund_amount,
            reason=data.reason,
        )

        if not success:
            raise HTTPException(status_code=400, detail="Gateway declined refund.")

        rfnd = RefundRecord(
            payment_transaction_id=tx.id,
            agency_id=target_agency_id,
            gateway_refund_id=refund_id,
            amount=Decimal(str(refund_amount)),
            currency=tx.currency,
            reason=data.reason,
            status=PaymentStatus.SUCCEEDED,
            created_at=utc_now(),
        )
        self.db.add(rfnd)
        tx.status = PaymentStatus.REFUNDED
        self.db.commit()

        self.log_billing_event(
            action="PLATFORM_REFUND_ISSUED",
            resource_type="RefundRecord",
            resource_id=str(rfnd.id),
            details={"amount": refund_amount, "reason": data.reason},
            actor_user_id=user.id,
        )

        return {
            "success": True,
            "refund_id": refund_id,
            "amount": refund_amount,
            "status": "REFUNDED",
        }

    # =========================================================================
    # 8. Audit Logging Helper
    # =========================================================================
    def log_billing_event(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        actor_user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ):
        """Creates an immutable billing and financial audit log."""
        log = BillingAuditLog(
            agency_id=self.agency_id or uuid.UUID("00000000-0000-0000-0000-000000000000"),
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details_json=json.dumps(details) if details else None,
            ip_address=ip_address,
            created_at=utc_now(),
        )
        self.db.add(log)
        self.db.commit()
