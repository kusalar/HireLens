import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import User
from app.models.enums import PaymentGateway
from app.api.deps import get_current_user, require_owner_or_admin, require_platform_admin, require_non_demo_mutation
from app.schemas.billing import (
    SubscriptionPlanRead,
    AgencySubscriptionRead,
    CheckoutSessionCreate,
    CheckoutSessionResponse,
    PaymentVerificationRequest,
    PaymentVerificationResponse,
    UsageOverviewResponse,
    BillingInvoiceRead,
    BillingInvoiceDetailRead,
    AgencyBillingProfileUpdate,
    AgencyBillingProfileRead,
    EntitlementOverrideCreate,
    EntitlementOverrideRead,
    PlatformBillingOverviewResponse,
    PlatformSubscriptionActionRequest,
    RefundRequest,
)
from app.services.billing_service import BillingService
from app.services.entitlement_service import EntitlementService

router = APIRouter()


# =============================================================================
# 1. Plans & Subscription Management (Agency Scope)
# =============================================================================
@router.get("/plans", response_model=List[SubscriptionPlanRead])
def list_subscription_plans(db: Session = Depends(get_db)):
    """
    Public listing of all available SaaS subscription plans and feature limits.
    """
    service = BillingService(db)
    return service.list_plans()


@router.get("/subscription", response_model=AgencySubscriptionRead)
def get_current_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the agency's current subscription tier, period bounds, and renewal status.
    """
    service = BillingService(db, current_user.agency_id)
    return service.get_agency_subscription()


@router.post("/subscription/cancel", response_model=AgencySubscriptionRead)
def cancel_subscription(
    cancel_at_period_end: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_non_demo_mutation),
):
    """
    Schedule subscription cancellation at the end of the billing period. OWNER/ADMIN only.
    """
    require_owner_or_admin(current_user)
    service = BillingService(db, current_user.agency_id)
    return service.cancel_subscription(user=current_user, cancel_at_period_end=cancel_at_period_end)


@router.get("/usage", response_model=UsageOverviewResponse)
def get_usage_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve real-time usage metrics and quota warnings across all resource dimensions.
    """
    service = EntitlementService(db, current_user.agency_id)
    return service.get_usage_overview()


# =============================================================================
# 2. Checkout & Payment Verification
# =============================================================================
@router.post("/checkout", response_model=CheckoutSessionResponse)
def create_checkout_session(
    data: CheckoutSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_non_demo_mutation),
):
    """
    Initiates a secure checkout session with Razorpay, Stripe, or Mock provider. OWNER/ADMIN only.
    """
    require_owner_or_admin(current_user)
    service = BillingService(db, current_user.agency_id)
    return service.initiate_checkout(user=current_user, data=data)


@router.post("/verify-payment", response_model=PaymentVerificationResponse)
def verify_payment(
    data: PaymentVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_non_demo_mutation),
):
    """
    Verifies cryptographic gateway signature and activates the upgraded subscription. OWNER/ADMIN only.
    """
    require_owner_or_admin(current_user)
    service = BillingService(db, current_user.agency_id)
    return service.verify_and_activate_checkout(user=current_user, data=data)


# =============================================================================
# 3. Invoices & Billing Profile
# =============================================================================
@router.get("/invoices", response_model=List[BillingInvoiceRead])
def list_invoices(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists paginated historical invoices for the agency. OWNER/ADMIN only.
    """
    require_owner_or_admin(current_user)
    service = BillingService(db, current_user.agency_id)
    return service.list_invoices(skip=skip, limit=limit)


@router.get("/invoices/{invoice_id}", response_model=BillingInvoiceDetailRead)
def get_invoice_detail(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches full line-item breakdown for an individual invoice. OWNER/ADMIN only.
    """
    require_owner_or_admin(current_user)
    service = BillingService(db, current_user.agency_id)
    return service.get_invoice_detail(invoice_id)


@router.get("/invoices/{invoice_id}/download")
def download_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generates and downloads a clean text/receipt representation of the invoice.
    """
    require_owner_or_admin(current_user)
    service = BillingService(db, current_user.agency_id)
    inv = service.get_invoice_detail(invoice_id)

    receipt = (
        f"==========================================================\n"
        f"               HIRELENS AI - TAX INVOICE                  \n"
        f"==========================================================\n"
        f"Invoice Number: {inv.invoice_number}\n"
        f"Date:           {inv.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"Status:         {inv.status.value}\n"
        f"Customer:       {inv.customer_name}\n"
        f"Email:          {inv.customer_email}\n"
        f"GSTIN:          {inv.customer_gstin or 'N/A'}\n"
        f"----------------------------------------------------------\n"
        f"Line Items:\n"
    )
    for item in inv.line_items:
        receipt += f"  - {item.description} (Qty: {item.quantity}): {inv.currency.value} {item.total_price:.2f}\n"

    receipt += (
        f"----------------------------------------------------------\n"
        f"Subtotal:       {inv.currency.value} {inv.subtotal:.2f}\n"
        f"Tax ({inv.tax_rate_pct}%):     {inv.currency.value} {inv.tax_amount:.2f}\n"
        f"Total Paid:     {inv.currency.value} {inv.total_amount:.2f}\n"
        f"==========================================================\n"
        f"Thank you for choosing HireLens AI.\n"
    )

    return PlainTextResponse(
        content=receipt,
        headers={"Content-Disposition": f"attachment; filename={inv.invoice_number}.txt"},
    )


@router.get("/profile", response_model=Optional[AgencyBillingProfileRead])
def get_billing_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Gets the agency's corporate billing address and GSTIN profile.
    """
    service = BillingService(db, current_user.agency_id)
    profile = service.get_billing_profile()
    if not profile:
        return None
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
        is_gstin_valid=bool(profile.gstin),
        updated_at=profile.updated_at,
    )


@router.put("/profile", response_model=AgencyBillingProfileRead)
def update_billing_profile(
    data: AgencyBillingProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_non_demo_mutation),
):
    """
    Updates the agency's legal entity name, address, and GSTIN. OWNER/ADMIN only.
    """
    require_owner_or_admin(current_user)
    service = BillingService(db, current_user.agency_id)
    return service.update_billing_profile(data=data, user=current_user)


# =============================================================================
# 4. Payment Gateway Webhook Receivers
# =============================================================================
@router.post("/webhooks/{gateway}")
async def receive_payment_webhook(
    gateway: PaymentGateway,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public webhook receiver for Razorpay, Stripe, or Mock providers.
    Cryptographically authenticates signatures and prevents replay attacks.
    """
    body_bytes = await request.body()
    headers_dict = dict(request.headers)
    service = BillingService(db)
    return service.handle_incoming_webhook(
        gateway=gateway,
        payload_bytes=body_bytes,
        headers=headers_dict,
    )


# =============================================================================
# 5. Platform-Level Administration (Distinct from Agency Roles)
# =============================================================================
@router.get("/platform/overview", response_model=PlatformBillingOverviewResponse)
def get_platform_billing_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Platform-level financial metrics, MRR/ARR, and subscription analytics.
    Restricted to Platform Administrators.
    """
    service = BillingService(db)
    return service.platform_get_overview()


@router.post("/platform/subscriptions/{target_agency_id}/action", response_model=AgencySubscriptionRead)
def execute_platform_subscription_action(
    target_agency_id: uuid.UUID,
    data: PlatformSubscriptionActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Platform admin action: SUSPEND, REACTIVATE, or CANCEL an agency subscription.
    """
    service = BillingService(db)
    return service.platform_action_subscription(
        target_agency_id=target_agency_id,
        user=current_user,
        data=data,
    )


@router.post("/platform/subscriptions/{target_agency_id}/override", response_model=EntitlementOverrideRead)
def apply_entitlement_override(
    target_agency_id: uuid.UUID,
    data: EntitlementOverrideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Grants a custom resource quota or promotional entitlement override to an agency.
    """
    service = BillingService(db)
    return service.platform_override_entitlement(
        target_agency_id=target_agency_id,
        user=current_user,
        data=data,
    )


@router.post("/platform/refund")
def process_platform_refund(
    target_agency_id: uuid.UUID,
    data: RefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Processes an audited refund against a prior payment transaction.
    """
    service = BillingService(db)
    return service.platform_process_refund(
        target_agency_id=target_agency_id,
        user=current_user,
        data=data,
    )
