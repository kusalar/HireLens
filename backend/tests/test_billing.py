import uuid
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import User, Agency
from app.models.enums import (
    UserRole,
    SubscriptionTier,
    SubscriptionStatus,
    BillingInterval,
    PaymentGateway,
    PaymentStatus,
    QuotaResourceType,
    BillingCurrency,
)
from app.models.billing import (
    SubscriptionPlan,
    AgencySubscription,
    UsageMeter,
    PaymentTransaction,
    BillingInvoice,
    EntitlementOverride,
)
from app.services.payment_gateways import MockPaymentAdapter


def create_agency_and_user(
    client: TestClient,
    agency_name: str,
    email: str,
    role: str = "OWNER",
    country: str = "IN",
) -> tuple[str, str, str]:
    """Helper creating an agency and returning (token, user_id, agency_id)."""
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "agency_name": agency_name,
            "full_name": f"{role} User",
            "email": email,
            "password": "SecurePassword123!",
        },
    )
    assert reg_res.status_code == 201, reg_res.text
    data = reg_res.json()
    token = data["tokens"]["access_token"]
    user_id = data["user"]["id"]
    agency_id = data["user"]["agency_id"]

    # Update role if needed
    if role != "OWNER":
        from app.db.session import SessionLocal
        db = SessionLocal()
        u = db.get(User, uuid.UUID(user_id))
        u.role = UserRole(role)
        db.commit()
        db.close()

    return token, user_id, agency_id


# =============================================================================
# 1. Plans & Default Subscription Enrollment
# =============================================================================
def test_list_plans_and_default_free_enrollment(client: TestClient):
    """
    Verifies that all 5 canonical plans are listed and new agencies
    automatically receive a FREE active subscription.
    """
    token, _, _ = create_agency_and_user(client, "Billing Plan Agency", "plan_admin@corp.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List public plans
    plans_res = client.get("/api/v1/billing/plans")
    assert plans_res.status_code == 200
    plans = plans_res.json()
    assert len(plans) >= 5
    tiers = [p["tier"] for p in plans]
    assert "FREE" in tiers
    assert "STARTER" in tiers
    assert "PROFESSIONAL" in tiers
    assert "BUSINESS" in tiers
    assert "ENTERPRISE" in tiers

    # 2. Get current agency subscription (should auto-enroll in FREE)
    sub_res = client.get("/api/v1/billing/subscription", headers=headers)
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["tier"] == "FREE"
    assert sub_data["status"] == "ACTIVE"


# =============================================================================
# 2. Checkout & Server-Side Payment Verification (Mock Gateway)
# =============================================================================
def test_checkout_and_payment_activation(client: TestClient):
    """
    Tests initiating a checkout session, verifying cryptographic signatures server-side,
    upgrading plan to PROFESSIONAL, and generating a paid invoice.
    """
    token, _, _ = create_agency_and_user(client, "Checkout Agency", "checkout_admin@corp.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Initiate checkout for Professional plan
    chk_res = client.post(
        "/api/v1/billing/checkout",
        headers=headers,
        json={
            "plan_slug": "professional",
            "billing_interval": "MONTHLY",
            "currency": "INR",
            "gateway": "MOCK",
        },
    )
    assert chk_res.status_code == 200
    chk_data = chk_res.json()
    session_id = chk_data["session_id"]
    assert chk_data["amount"] == 14999.0
    assert chk_data["currency"] == "INR"

    # 2. Generate valid mock signature
    mock_adapter = MockPaymentAdapter()
    valid_sig = mock_adapter.generate_valid_mock_signature(session_id)

    # 3. Complete payment verification
    verify_res = client.post(
        "/api/v1/billing/verify-payment",
        headers=headers,
        json={
            "gateway": "MOCK",
            "session_id": session_id,
            "payment_id": f"pay_{session_id[:12]}",
            "signature": valid_sig,
        },
    )
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["success"] is True
    assert v_data["subscription_status"] == "ACTIVE"
    assert v_data["invoice_number"].startswith("HL-INV-")

    # 4. Verify subscription upgraded to PROFESSIONAL
    sub_res = client.get("/api/v1/billing/subscription", headers=headers)
    assert sub_res.status_code == 200
    assert sub_res.json()["tier"] == "PROFESSIONAL"


def test_payment_verification_rejects_invalid_signature(client: TestClient):
    """
    Verifies that forged or invalid signatures are rejected with 400 Bad Request.
    """
    token, _, _ = create_agency_and_user(client, "Tamper Agency", "tamper@corp.com")
    headers = {"Authorization": f"Bearer {token}"}

    chk_res = client.post(
        "/api/v1/billing/checkout",
        headers=headers,
        json={"plan_slug": "starter", "gateway": "MOCK"},
    )
    session_id = chk_res.json()["session_id"]

    verify_res = client.post(
        "/api/v1/billing/verify-payment",
        headers=headers,
        json={
            "gateway": "MOCK",
            "session_id": session_id,
            "payment_id": "forged_pay_123",
            "signature": "invalid_forged_signature_hash",
        },
    )
    assert verify_res.status_code == 400
    assert "Invalid mock signature" in verify_res.json()["detail"]


# =============================================================================
# 3. Usage Metering & Quota Enforcement
# =============================================================================
def test_usage_metering_and_quota_breach_protection(client: TestClient, db_session: Session):
    """
    Verifies that atomic quota tracking reports usage and strictly blocks
    operations when the hard limit is exceeded (HTTP 402 Payment Required).
    """
    token, _, agency_id_str = create_agency_and_user(client, "Quota Agency", "quota_admin@corp.com")
    headers = {"Authorization": f"Bearer {token}"}
    agency_id = uuid.UUID(agency_id_str)

    # 1. Check initial usage overview
    usage_res = client.get("/api/v1/billing/usage", headers=headers)
    assert usage_res.status_code == 200
    u_data = usage_res.json()
    assert "ACTIVE_JOBS" in u_data["meters"]
    assert "CANDIDATES_MONTHLY" in u_data["meters"]
    assert u_data["meters"]["ACTIVE_JOBS"]["hard_limit"] == 2  # Free plan default

    # 2. Consume quota via EntitlementService directly to simulate operations
    from app.services.entitlement_service import EntitlementService
    es = EntitlementService(db_session, agency_id)

    # Consume 1 job quota
    m1 = es.consume_quota(QuotaResourceType.ACTIVE_JOBS, units=1, operation_reference="JOB-1")
    assert m1.current_usage == 1

    # Consume 2nd job quota (reaches limit)
    m2 = es.consume_quota(QuotaResourceType.ACTIVE_JOBS, units=1, operation_reference="JOB-2")
    assert m2.current_usage == 2

    # Attempting to consume 3rd job quota must raise HTTP 402 Payment Required
    with pytest.raises(Exception) as excinfo:
        es.consume_quota(QuotaResourceType.ACTIVE_JOBS, units=1, operation_reference="JOB-3")
    assert "402" in str(excinfo.value)


def test_idempotent_quota_consumption(client: TestClient, db_session: Session):
    """
    Verifies that replaying an operation with the same idempotency key
    does NOT consume additional quota units.
    """
    _, _, agency_id_str = create_agency_and_user(client, "Idemp Agency", "idemp_admin@corp.com")
    agency_id = uuid.UUID(agency_id_str)

    from app.services.entitlement_service import EntitlementService
    es = EntitlementService(db_session, agency_id)

    # First consumption with idempotency key
    es.consume_quota(
        QuotaResourceType.CANDIDATES_MONTHLY,
        units=5,
        idempotency_key="idemp_cand_key_1001",
    )
    m = es.get_or_create_meter(QuotaResourceType.CANDIDATES_MONTHLY)
    assert m.current_usage == 5

    # Replay with same key
    es.consume_quota(
        QuotaResourceType.CANDIDATES_MONTHLY,
        units=5,
        idempotency_key="idemp_cand_key_1001",
    )
    db_session.refresh(m)
    assert m.current_usage == 5  # Usage remained 5, not double-counted


# =============================================================================
# 4. Invoicing, GSTIN Validation & Tax Calculations
# =============================================================================
def test_billing_profile_gstin_validation(client: TestClient):
    """
    Verifies that Indian GSTIN format is strictly validated via regex.
    """
    token, _, _ = create_agency_and_user(client, "GST Agency", "gst_admin@corp.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Invalid GSTIN must be rejected with 422
    inv_res = client.put(
        "/api/v1/billing/profile",
        headers=headers,
        json={
            "legal_name": "GST Agency Pvt Ltd",
            "billing_email": "gst@corp.com",
            "country": "IN",
            "gstin": "INVALID_GST_123",
        },
    )
    assert inv_res.status_code == 422

    # 2. Valid GSTIN (Maharashtra standard format: 27AABCU9603R1ZN)
    valid_res = client.put(
        "/api/v1/billing/profile",
        headers=headers,
        json={
            "legal_name": "GST Agency Pvt Ltd",
            "billing_email": "gst@corp.com",
            "country": "IN",
            "gstin": "27AABCU9603R1ZN",
            "address_line1": "Nariman Point",
            "city": "Mumbai",
            "state_province": "Maharashtra",
            "postal_code": "400021",
        },
    )
    assert valid_res.status_code == 200
    assert valid_res.json()["is_gstin_valid"] is True
    assert valid_res.json()["gstin"] == "27AABCU9603R1ZN"


def test_invoice_history_and_receipt_download(client: TestClient):
    """
    Verifies that paid invoices appear in invoice history and can be downloaded.
    """
    token, _, _ = create_agency_and_user(client, "Invoice Agency", "inv_admin@corp.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Upgrade to Starter to generate invoice
    chk_res = client.post(
        "/api/v1/billing/checkout",
        headers=headers,
        json={"plan_slug": "starter", "gateway": "MOCK"},
    )
    session_id = chk_res.json()["session_id"]
    mock_adapter = MockPaymentAdapter()
    sig = mock_adapter.generate_valid_mock_signature(session_id)

    client.post(
        "/api/v1/billing/verify-payment",
        headers=headers,
        json={"gateway": "MOCK", "session_id": session_id, "signature": sig},
    )

    # 1. List invoices
    inv_list_res = client.get("/api/v1/billing/invoices", headers=headers)
    assert inv_list_res.status_code == 200
    invoices = inv_list_res.json()
    assert len(invoices) >= 1
    inv_id = invoices[0]["id"]
    assert invoices[0]["tax_rate_pct"] == 18.0  # Domestic India 18% GST

    # 2. Get detail
    det_res = client.get(f"/api/v1/billing/invoices/{inv_id}", headers=headers)
    assert det_res.status_code == 200
    assert len(det_res.json()["line_items"]) >= 1

    # 3. Download receipt
    down_res = client.get(f"/api/v1/billing/invoices/{inv_id}/download", headers=headers)
    assert down_res.status_code == 200
    assert "HIRELENS AI - TAX INVOICE" in down_res.text
    assert "Subtotal:" in down_res.text


# =============================================================================
# 5. Subscription Cancellation Lifecycle
# =============================================================================
def test_subscription_cancellation_lifecycle(client: TestClient):
    """
    Tests scheduling cancellation for an active paid subscription.
    """
    token, _, _ = create_agency_and_user(client, "Cancel Agency", "cancel_admin@corp.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Upgrade to Starter first
    chk_res = client.post(
        "/api/v1/billing/checkout",
        headers=headers,
        json={"plan_slug": "starter", "gateway": "MOCK"},
    )
    sess_id = chk_res.json()["session_id"]
    sig = MockPaymentAdapter().generate_valid_mock_signature(sess_id)
    client.post(
        "/api/v1/billing/verify-payment",
        headers=headers,
        json={"gateway": "MOCK", "session_id": sess_id, "signature": sig},
    )

    # Cancel at period end
    cancel_res = client.post(
        "/api/v1/billing/subscription/cancel?cancel_at_period_end=true",
        headers=headers,
    )
    assert cancel_res.status_code == 200
    data = cancel_res.json()
    assert data["cancel_at_period_end"] is True
    assert data["status"] == "ACTIVE"  # Remains active until period end


# =============================================================================
# 6. Webhook Processing & Deduplication
# =============================================================================
def test_payment_webhook_processing_and_deduplication(client: TestClient):
    """
    Verifies that incoming webhooks are processed with valid signatures and
    duplicate events are gracefully ignored.
    """
    import json, hmac, hashlib
    payload = {"event": "payment.succeeded", "id": "evt_test_webhook_1001", "amount": 4999}
    payload_bytes = json.dumps(payload).encode("utf-8")
    adapter = MockPaymentAdapter()
    sig = hmac.new(
        adapter.MOCK_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    # 1. First webhook submission
    w1_res = client.post(
        "/api/v1/billing/webhooks/MOCK",
        content=payload_bytes,
        headers={"Content-Type": "application/json", "X-Mock-Signature": sig},
    )
    assert w1_res.status_code == 200
    assert w1_res.json()["status"] == "processed"

    # 2. Duplicate submission with same event ID
    w2_res = client.post(
        "/api/v1/billing/webhooks/MOCK",
        content=payload_bytes,
        headers={"Content-Type": "application/json", "X-Mock-Signature": sig},
    )
    assert w2_res.status_code == 200
    assert w2_res.json()["status"] == "ignored"


# =============================================================================
# 7. Platform Admin Governance & Separation
# =============================================================================
def test_platform_admin_access_separation(client: TestClient, db_session: Session):
    """
    Verifies that ordinary agency users are blocked with 403 Forbidden from
    accessing platform billing endpoints, while users with is_platform_admin=True succeed.
    """
    token, user_id_str, agency_id_str = create_agency_and_user(
        client, "Platform Sec Agency", "plat_user@corp.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Ordinary agency OWNER cannot access platform overview
    block_res = client.get("/api/v1/billing/platform/overview", headers=headers)
    assert block_res.status_code == 403
    assert "Platform administrator privileges required" in block_res.json()["detail"]

    # 2. Grant platform admin privilege to this user
    u = db_session.get(User, uuid.UUID(user_id_str))
    u.is_platform_admin = True
    db_session.commit()

    # 3. Platform admin now succeeds
    succ_res = client.get("/api/v1/billing/platform/overview", headers=headers)
    assert succ_res.status_code == 200
    data = succ_res.json()
    assert "total_agencies" in data
    assert "mrr_inr" in data
    assert "subscriptions_by_tier" in data

    # 4. Test platform admin entitlement override
    target_agency_id = uuid.UUID(agency_id_str)
    over_res = client.post(
        f"/api/v1/billing/platform/subscriptions/{target_agency_id}/override",
        headers=headers,
        json={
            "resource_type": "ACTIVE_JOBS",
            "override_limit": 50,
            "is_unlimited": False,
            "reason": "Promotional tier extension",
        },
    )
    assert over_res.status_code == 200
    assert over_res.json()["override_limit"] == 50


# =============================================================================
# 8. Cross-Agency Isolation & RBAC
# =============================================================================
def test_cross_agency_billing_isolation(client: TestClient):
    """
    Verifies strict tenant isolation: an agency cannot access another agency's invoices or subscription.
    """
    tok_a, _, _ = create_agency_and_user(client, "Agency Alpha", "alpha@agency.com")
    tok_b, _, _ = create_agency_and_user(client, "Agency Beta", "beta@agency.com")

    # Alpha upgrades to get an invoice
    chk_res = client.post(
        "/api/v1/billing/checkout",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"plan_slug": "starter", "gateway": "MOCK"},
    )
    sess_id = chk_res.json()["session_id"]
    sig = MockPaymentAdapter().generate_valid_mock_signature(sess_id)
    client.post(
        "/api/v1/billing/verify-payment",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"gateway": "MOCK", "session_id": sess_id, "signature": sig},
    )

    invoices_a = client.get(
        "/api/v1/billing/invoices",
        headers={"Authorization": f"Bearer {tok_a}"},
    ).json()
    assert len(invoices_a) >= 1
    invoice_a_id = invoices_a[0]["id"]

    # Beta attempts to access Alpha's invoice: MUST be 404
    cross_res = client.get(
        f"/api/v1/billing/invoices/{invoice_a_id}",
        headers={"Authorization": f"Bearer {tok_b}"},
    )
    assert cross_res.status_code == 404
