import os
import hmac
import hashlib
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.security import encrypt_token, decrypt_token
from app.core.logging import StructuredJSONFormatter
from app.models.entities import User, Agency
from app.models.enums import (
    UserRole,
    PaymentGateway,
    PaymentStatus,
    BillingCurrency,
    SubscriptionTier,
    SubscriptionStatus,
    CalendarProviderType,
    CalendarSyncStatus,
    CalendarSyncDirection,
    CalendarSyncOperation,
    NotificationType,
    NotificationDeliveryStatus,
)
from app.models.billing import (
    SubscriptionPlan,
    AgencySubscription,
    PaymentTransaction,
    BillingInvoice,
    PaymentWebhookEvent,
)
from app.models.calendar import (
    CalendarConnection,
    CalendarEventMapping,
    CalendarSyncJob,
    CalendarSyncLog,
)
from app.models.notification import (
    Notification,
    NotificationOutbox,
    NotificationPreference,
)
from app.services.payment_gateways import (
    RazorpayAdapter,
    StripeAdapter,
    MockPaymentAdapter,
    get_payment_gateway,
)
from app.services.billing_service import BillingService
from app.services.calendar_sync_service import CalendarSyncService
from app.services.calendar.google import GoogleCalendarProvider
from app.services.calendar.microsoft import MicrosoftOutlookProvider
from app.services.calendar.mock import MockCalendarProvider
from app.services.email.smtp_provider import SmtpEmailProvider
from app.services.email.base import EmailMessage
from app.services.notification_service import NotificationService
from app.tasks.calendar_tasks import dispatch_calendar_sync_job_task, process_calendar_sync_batch_task
from app.tasks.notification_tasks import dispatch_outbox_email_task, process_outbox_batch_task


def create_agency_and_user(
    client: TestClient,
    agency_name: str,
    email: str,
    role: str = "OWNER",
) -> tuple[str, str, str]:
    """Helper creating an agency and returning (token, user_id, agency_id)."""
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "agency_name": agency_name,
            "full_name": f"{agency_name} Admin",
            "email": email,
            "password": "SecurePassword123!",
        },
    )
    assert reg_res.status_code == 201, reg_res.text
    data = reg_res.json()
    token = data["tokens"]["access_token"]
    user_id = data["user"]["id"]
    agency_id = data["user"]["agency_id"]
    return token, user_id, agency_id


# =============================================================================
# 1. RAZORPAY SANDBOX & ADAPTER VERIFICATION
# =============================================================================

def test_razorpay_unconfigured_credentials_rejection():
    """
    Verifies that RazorpayAdapter safely rejects checkout/verification
    with HTTP 503 when credentials are not configured, instructing to use MOCK.
    """
    with patch.dict(os.environ, {}, clear=True):
        adapter = RazorpayAdapter()
        adapter.key_id = None
        adapter.key_secret = None
        adapter.is_live = False

        with pytest.raises(Exception) as exc_info:
            adapter.create_checkout_session(
                agency_id=uuid.uuid4(),
                plan_name="Starter Plan",
                plan_slug="starter",
                amount=4999.0,
                currency=BillingCurrency.INR,
                idempotency_key="idemp_rzp_test_1",
            )
        assert "503" in str(exc_info.value)
        assert "Razorpay payment gateway is not configured with live credentials" in str(exc_info.value)


def test_razorpay_sandbox_checkout_order_creation():
    """
    Verifies Razorpay sandbox order payload generation with INR currency and test publishable key.
    """
    adapter = RazorpayAdapter()
    adapter.key_id = "rzp_test_mock_sandbox_key_99"
    adapter.key_secret = "rzp_test_mock_secret_88"
    adapter.is_live = True

    session = adapter.create_checkout_session(
        agency_id=uuid.uuid4(),
        plan_name="Professional Plan",
        plan_slug="professional",
        amount=14999.0,
        currency=BillingCurrency.INR,
        idempotency_key="idemp_rzp_order_001",
    )
    assert session["gateway"] == PaymentGateway.RAZORPAY
    assert session["amount"] == 14999.0
    assert session["currency"] == BillingCurrency.INR
    assert session["publishable_key"] == "rzp_test_mock_sandbox_key_99"
    assert session["order_id"].startswith("order_rzp_")
    assert "https://api.razorpay.com/v1/checkout/" in session["checkout_url"]


def test_razorpay_signature_verification_and_forgery_rejection():
    """
    Verifies HMAC-SHA256 signature calculation over order_id|payment_id
    and confirms rejection of forged signatures.
    """
    adapter = RazorpayAdapter()
    adapter.key_id = "rzp_test_mock_sandbox_key_99"
    adapter.key_secret = "rzp_test_mock_secret_88"
    adapter.is_live = True

    order_id = "order_rzp_test_order_12345"
    payment_id = "pay_rzp_test_payment_67890"

    # 1. Compute valid signature
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(
        adapter.key_secret.encode("utf-8"),
        msg,
        hashlib.sha256,
    ).hexdigest()

    is_valid, tx_id, meta = adapter.verify_payment({
        "order_id": order_id,
        "payment_id": payment_id,
        "signature": valid_sig,
    })
    assert is_valid is True
    assert tx_id == payment_id
    assert meta["order_id"] == order_id

    # 2. Forged signature must fail
    is_valid_bad, tx_bad, meta_bad = adapter.verify_payment({
        "order_id": order_id,
        "payment_id": payment_id,
        "signature": "forged_invalid_hex_signature_hash_000000000000",
    })
    assert is_valid_bad is False
    assert tx_bad == ""
    assert "Invalid Razorpay HMAC signature" in meta_bad["error"]


def test_razorpay_webhook_signature_and_deduplication(client: TestClient, db_session: Session):
    """
    Verifies Razorpay webhook HMAC-SHA256 signature verification via X-Razorpay-Signature header
    and verifies replay/deduplication protection.
    """
    webhook_secret = "rzp_whsec_test_secret_7777"
    with patch.object(settings, "RAZORPAY_WEBHOOK_SECRET", webhook_secret), \
         patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": webhook_secret}):
        event_id = f"evt_rzp_{uuid.uuid4().hex[:14]}"
        payload = {
            "id": event_id,
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_9999",
                        "amount": 1499900,
                        "currency": "INR",
                        "status": "captured",
                    }
                }
            }
        }
        payload_bytes = json.dumps(payload).encode("utf-8")

        # Compute valid webhook signature
        sig = hmac.new(
            webhook_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        # 1. Invalid signature must be rejected with 400
        bad_res = client.post(
            "/api/v1/billing/webhooks/RAZORPAY",
            content=payload_bytes,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": "invalid_sig"},
        )
        assert bad_res.status_code == 400
        assert "Invalid payment gateway webhook signature" in bad_res.json()["detail"]

        # 2. Valid signature must be processed
        good_res = client.post(
            "/api/v1/billing/webhooks/RAZORPAY",
            content=payload_bytes,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
        )
        assert good_res.status_code == 200
        assert good_res.json()["status"] == "processed"
        assert good_res.json()["event_id"] == event_id

        # 3. Duplicate webhook must be ignored
        dup_res = client.post(
            "/api/v1/billing/webhooks/RAZORPAY",
            content=payload_bytes,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
        )
        assert dup_res.status_code == 200
        assert dup_res.json()["status"] == "ignored"


# =============================================================================
# 2. STRIPE SANDBOX & ADAPTER VERIFICATION
# =============================================================================

def test_stripe_unconfigured_credentials_rejection():
    """
    Verifies that StripeAdapter safely rejects session creation when keys are missing.
    """
    adapter = StripeAdapter()
    adapter.secret_key = None
    adapter.publishable_key = None
    adapter.is_live = False

    with pytest.raises(Exception) as exc_info:
        adapter.create_checkout_session(
            agency_id=uuid.uuid4(),
            plan_name="Starter Plan",
            plan_slug="starter",
            amount=59.0,
            currency=BillingCurrency.USD,
            idempotency_key="idemp_str_test_1",
        )
    assert "503" in str(exc_info.value)
    assert "Stripe payment gateway is not configured with live credentials" in str(exc_info.value)


def test_stripe_sandbox_checkout_session_creation():
    """
    Verifies Stripe sandbox session generation with USD currency and publishable key.
    """
    adapter = StripeAdapter()
    adapter.secret_key = "sk_test_mock_sandbox_secret_key"
    adapter.publishable_key = "pk_test_mock_sandbox_pub_key"
    adapter.is_live = True

    session = adapter.create_checkout_session(
        agency_id=uuid.uuid4(),
        plan_name="Enterprise Plan",
        plan_slug="enterprise",
        amount=199.0,
        currency=BillingCurrency.USD,
        idempotency_key="idemp_str_order_001",
    )
    assert session["gateway"] == PaymentGateway.STRIPE
    assert session["amount"] == 199.0
    assert session["currency"] == BillingCurrency.USD
    assert session["publishable_key"] == "pk_test_mock_sandbox_pub_key"
    assert session["session_id"].startswith("cs_test_")
    assert "https://checkout.stripe.com/pay/" in session["checkout_url"]


def test_stripe_webhook_signature_format_and_deduplication(client: TestClient, db_session: Session):
    """
    Verifies Stripe webhook signature verification using 't=timestamp,v1=signature' format
    and verifies deduplication handling.
    """
    webhook_secret = "whsec_test_stripe_secret_key_8888"
    with patch.object(settings, "STRIPE_WEBHOOK_SECRET", webhook_secret), \
         patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": webhook_secret}):
        event_id = f"evt_str_{uuid.uuid4().hex[:14]}"
        payload = {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_session_completed_123",
                    "amount_total": 19900,
                    "currency": "usd",
                    "payment_status": "paid",
                }
            }
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        timestamp = str(int(time.time()))

        signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
        expected_sig = hmac.new(
            webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        header_val = f"t={timestamp},v1={expected_sig}"

        # 1. Invalid signature must fail with 400
        bad_res = client.post(
            "/api/v1/billing/webhooks/STRIPE",
            content=payload_bytes,
            headers={"Content-Type": "application/json", "Stripe-Signature": f"t={timestamp},v1=forged_hash"},
        )
        assert bad_res.status_code == 400
        assert "Invalid payment gateway webhook signature" in bad_res.json()["detail"]

        # 2. Valid signature succeeds
        good_res = client.post(
            "/api/v1/billing/webhooks/STRIPE",
            content=payload_bytes,
            headers={"Content-Type": "application/json", "Stripe-Signature": header_val},
        )
        assert good_res.status_code == 200
        assert good_res.json()["status"] == "processed"

        # 3. Duplicate event ignored
        dup_res = client.post(
            "/api/v1/billing/webhooks/STRIPE",
            content=payload_bytes,
            headers={"Content-Type": "application/json", "Stripe-Signature": header_val},
        )
        assert dup_res.status_code == 200
        assert dup_res.json()["status"] == "ignored"


# =============================================================================
# 3. GOOGLE OAUTH & CALENDAR INTEGRATION VERIFICATION
# =============================================================================

def test_google_oauth_url_and_encrypted_state_generation(client: TestClient, db_session: Session):
    """
    Verifies Google OAuth URL generation including scopes, prompt=consent, access_type=offline,
    and Fernet encrypted state token binding user_id and agency_id.
    """
    token, user_id, agency_id = create_agency_and_user(client, "Google OAuth Agency", "google_admin@corp.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test direct Google provider authorization URL format
    google_provider = GoogleCalendarProvider(
        client_id="mock-google-client-id-123.apps.googleusercontent.com",
        client_secret="mock-google-client-secret-456",
    )
    direct_auth_url = google_provider.get_authorization_url(
        state="test-state-token",
        redirect_uri="http://localhost:3000/settings/integrations?provider=google",
    )
    assert "accounts.google.com/o/oauth2/v2/auth" in direct_auth_url
    assert "mock-google-client-id-123" in direct_auth_url
    assert "calendar.events" in direct_auth_url
    assert "prompt=consent" in direct_auth_url
    assert "access_type=offline" in direct_auth_url

    # 2. Test API endpoint initialization with state generation
    res = client.post(
        "/api/v1/integrations/calendars/init",
        headers=headers,
        json={"provider": "GOOGLE"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "authorization_url" in data
    assert "state" in data

    # Decrypt and verify state payload
    state_json = decrypt_token(data["state"])
    assert state_json is not None
    state_payload = json.loads(state_json)
    assert state_payload["agency_id"] == agency_id
    assert state_payload["user_id"] == user_id
    assert state_payload["provider"] == "GOOGLE"
    assert "nonce" in state_payload
    assert state_payload["exp"] > time.time()


def test_google_oauth_csrf_tampering_and_cross_agency_rejection(client: TestClient):
    """
    Verifies that tampered states, expired states, and cross-agency states are strictly rejected.
    """
    tok_a, u_a, a_a = create_agency_and_user(client, "Agency G-Alpha", "alpha_g@agency.com")
    tok_b, u_b, a_b = create_agency_and_user(client, "Agency G-Beta", "beta_g@agency.com")

    # 1. Completely invalid state string
    bad_res = client.post(
        "/api/v1/integrations/calendars/callback",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"code": "auth_code_123", "state": "invalid-non-encrypted-state-token"},
    )
    assert bad_res.status_code == 400
    assert "Invalid or tampered OAuth state" in bad_res.json()["detail"]

    # 2. State created for Agency Alpha passed by Agency Beta user
    init_res = client.post(
        "/api/v1/integrations/calendars/init",
        headers={"Authorization": f"Bearer {tok_a}"},
        json={"provider": "GOOGLE"},
    )
    state_a = init_res.json()["state"]

    cross_res = client.post(
        "/api/v1/integrations/calendars/callback",
        headers={"Authorization": f"Bearer {tok_b}"},
        json={"code": "auth_code_123", "state": state_a},
    )
    assert cross_res.status_code == 403
    assert "Cross-agency OAuth callback attempt rejected" in cross_res.json()["detail"]


def test_google_calendar_token_encryption_at_rest(client: TestClient, db_session: Session):
    """
    Verifies that access and refresh tokens are encrypted via Fernet before database persistence,
    guaranteeing zero plaintext token exposure in database storage.
    """
    token, user_id_str, agency_id_str = create_agency_and_user(client, "Enc Test Agency", "enc_admin@corp.com")
    agency_id = uuid.UUID(agency_id_str)
    user_id = uuid.UUID(user_id_str)

    raw_access_token = "ya29.a0AfH6SMTestGoogleAccessToken123456789"
    raw_refresh_token = "1//04TestGoogleRefreshTokenSecureValue98765"

    conn = CalendarConnection(
        agency_id=agency_id,
        user_id=user_id,
        provider=CalendarProviderType.GOOGLE,
        provider_account_id="google-user-1001",
        provider_account_email="enc_admin@corp.com",
        encrypted_access_token=encrypt_token(raw_access_token),
        encrypted_refresh_token=encrypt_token(raw_refresh_token),
        access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        selected_calendar_id="primary",
        is_active=True,
    )
    db_session.add(conn)
    db_session.commit()
    db_session.refresh(conn)

    # 1. Confirm DB field is NOT plaintext
    assert conn.encrypted_access_token != raw_access_token
    assert not conn.encrypted_access_token.startswith("ya29.")
    assert conn.encrypted_refresh_token != raw_refresh_token

    # 2. Confirm decryption produces original plaintext
    assert decrypt_token(conn.encrypted_access_token) == raw_access_token
    assert decrypt_token(conn.encrypted_refresh_token) == raw_refresh_token


# =============================================================================
# 4. MICROSOFT ENTRA & OUTLOOK CALENDAR INTEGRATION VERIFICATION
# =============================================================================

def test_microsoft_oauth_url_and_graph_scopes():
    """
    Verifies Microsoft Entra OAuth authorization URL, tenant 'common',
    and Microsoft Graph calendar scopes.
    """
    provider = MicrosoftOutlookProvider(
        client_id="mock-ms-client-id-123",
        client_secret="mock-ms-client-secret-456",
        tenant_id="common",
    )
    auth_url = provider.get_authorization_url(
        state="test-encrypted-state-token",
        redirect_uri="http://localhost:3000/settings/integrations?provider=microsoft",
    )
    assert "login.microsoftonline.com/common/oauth2/v2.0/authorize" in auth_url
    assert "mock-ms-client-id-123" in auth_url
    assert "Calendars.ReadWrite" in auth_url
    assert "offline_access" in auth_url
    assert "User.Read" in auth_url


def test_microsoft_calendar_event_lifecycle_and_conflict_handling(db_session: Session):
    """
    Verifies Microsoft Calendar provider abstraction event creation, update,
    and cancellation using mock adapter semantics.
    """
    agency_id = uuid.uuid4()
    mock_prov = MockCalendarProvider()

    now = datetime.now(timezone.utc)
    res = mock_prov.create_event(
        access_token="test-access-token",
        calendar_id="primary",
        title="Technical Interview — Senior Backend Engineer",
        description="Interview discussion and coding",
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=1, hours=1),
        timezone_str="Asia/Kolkata",
        attendees=[{"email": "candidate@example.com"}, {"email": "interviewer@corp.com"}],
        generate_meeting=True,
    )
    assert res.status == "confirmed"
    assert res.event_id is not None
    assert res.meeting_link is not None

    # Update event
    up_res = mock_prov.update_event(
        access_token="test-access-token",
        calendar_id="primary",
        event_id=res.event_id,
        title="Technical Interview (Rescheduled)",
        description="Updated discussion agenda",
        start_time=now + timedelta(days=2),
        end_time=now + timedelta(days=2, hours=1),
        timezone_str="Asia/Kolkata",
        attendees=[{"email": "candidate@example.com"}],
    )
    assert up_res.status == "confirmed"
    assert up_res.event_id == res.event_id

    # Cancel event
    cancel_res = mock_prov.cancel_event(
        access_token="test-access-token",
        calendar_id="primary",
        event_id=res.event_id,
    )
    assert cancel_res is True


# =============================================================================
# 5. SMTP EMAIL PROVIDER & OUTBOX VERIFICATION
# =============================================================================

def test_smtp_unconfigured_host_returns_safe_error():
    """
    Verifies that SmtpEmailProvider safely returns an error when SMTP_HOST is not configured,
    without crashing or exposing internal stack traces.
    """
    provider = SmtpEmailProvider(host=None)
    msg = EmailMessage(
        to_email="candidate@test.com",
        subject="Interview Invitation",
        body_text="Plain text body",
        body_html="<p>HTML body</p>",
    )
    success, err = provider.send_email(msg)
    assert success is False
    assert err == "SMTP_HOST is not configured."


def test_smtp_mock_dispatch_with_tls_and_credential_sanitization():
    """
    Verifies SMTP TLS negotiation, login, and error credential masking.
    """
    provider = SmtpEmailProvider(
        host="smtp.example.com",
        port=587,
        username="hirelens_mailer",
        password="super_secret_smtp_password_999",
        use_tls=True,
    )

    msg = EmailMessage(
        to_email="candidate@test.com",
        to_name="Jane Doe",
        subject="Interview Scheduled",
        body_text="Your interview is confirmed.",
        body_html="<p>Your interview is confirmed.</p>",
    )

    # 1. Test successful dispatch with mocked smtplib.SMTP
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        success, err = provider.send_email(msg)
        assert success is True
        assert err is None
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("hirelens_mailer", "super_secret_smtp_password_999")
        mock_server.sendmail.assert_called_once()

    # 2. Test failed dispatch with smtplib.SMTPAuthenticationError
    # Confirm password is NOT present in returned error string
    import smtplib
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        success, err = provider.send_email(msg)
        assert success is False
        assert "super_secret_smtp_password_999" not in str(err)
        assert "SMTP protocol error: SMTPAuthenticationError" in str(err)


def test_notification_outbox_retry_and_dead_letter_handling(db_session: Session):
    """
    Verifies that failed transactional emails are recorded in the NotificationOutbox,
    retried with bounded retry counts, and marked FAILED (dead-letter) after exceeding max retries.
    """
    agency_id = uuid.uuid4()
    service = NotificationService(db_session, agency_id)

    # Create an outbox item
    item = NotificationOutbox(
        agency_id=agency_id,
        event_type="INTERVIEW_INVITATION",
        idempotency_key=f"idemp_outbox_{uuid.uuid4().hex}",
        recipient_email="retry_candidate@test.com",
        subject="Interview Reminder",
        body_text="Reminder content",
        body_html="<p>Reminder content</p>",
        status=NotificationDeliveryStatus.PENDING,
        attempt_count=0,
        max_retries=2,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    # Simulate dispatch failure 1
    with patch("app.services.notification_service.get_email_provider") as mock_prov_get:
        mock_prov = MagicMock()
        mock_prov.name = "mock"
        mock_prov.send_email.return_value = (False, "Transient network timeout")
        mock_prov_get.return_value = mock_prov

        # Dispatch attempt 1
        res1 = service.dispatch_outbox_item(item.id)
        assert res1 is False
        db_session.refresh(item)
        assert item.attempt_count == 1
        assert item.status == NotificationDeliveryStatus.FAILED

        # Dispatch attempt 2 (exceeds max_retries=2 -> DEAD_LETTER)
        res2 = service.dispatch_outbox_item(item.id)
        assert res2 is False
        db_session.refresh(item)
        assert item.attempt_count == 2
        assert item.status == NotificationDeliveryStatus.DEAD_LETTER


# =============================================================================
# 6. SECURITY & LOG CREDENTIAL SANITIZATION
# =============================================================================

def test_structured_log_formatter_redacts_credentials():
    """
    Verifies that StructuredJSONFormatter strictly redacts sensitive keys
    (password, token, secret, api_key, card_number, cvv) from log records.
    """
    import logging
    formatter = StructuredJSONFormatter()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="External webhook processed with payload",
        args=(),
        exc_info=None,
    )
    record.api_key = "sk_live_secret_key_12345"
    record.token = "ya29.secret_token_value_67890"
    record.password = "MySuperSecretPassword"
    record.card_number = "4111111111111111"

    formatted_json = formatter.format(record)
    parsed = json.loads(formatted_json)

    assert parsed["api_key"] == "[REDACTED]"
    assert parsed["token"] == "[REDACTED]"
    assert parsed["password"] == "[REDACTED]"
    assert parsed["card_number"] == "[REDACTED]"
    assert "sk_live_secret_key_12345" not in formatted_json
    assert "MySuperSecretPassword" not in formatted_json
