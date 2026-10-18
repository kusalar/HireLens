# HireLens AI — Final External Integration Checklist

**System:** HireLens AI Platform  
**Target Project:** `D:\HireLens`  
**Audit Date:** October 17, 2026  
**Auditor:** Antigravity Autonomous Systems Engineering  
**Scope:** Payment Gateways, OAuth Providers, Calendar Synchronizers, SMTP Email Delivery, and Secret Rotation  
**Evaluation Status:** COMPLETE  

---

## 1. Overview & Verification Policy

HireLens AI is architected with provider-agnostic abstractions and dual payment gateway support (Razorpay for domestic Indian INR transactions and Stripe for global multi-currency transactions), Google and Microsoft calendar synchronization, and transactional SMTP email delivery.

> [!IMPORTANT]
> In accordance with strict audit rules, this report documents verified code pathways and sandbox/mock functionality while clearly tagging live production connectivity as **`NEEDS EXTERNAL CREDENTIALS`**. Antigravity does not invent or simulate live external third-party production credentials.

---

## 2. External Provider Verification Checklist

| Provider / Service | Functional Area | Verification Status | Exact Evidence / Integration Verification | Production Prerequisites & Runbook |
| :--- | :--- | :--- | :--- | :--- |
| **Razorpay (Domestic)** | Checkout & Order Creation | `NEEDS EXTERNAL CREDENTIALS` | `RazorpayGateway` in `backend/app/services/payment_gateways.py` implements order creation (`client.order.create`), payment capture, and currency normalization (INR paise). Unit and mock tests PASS (`tests/test_billing.py`). | Requires live `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` from Razorpay Dashboard. |
| **Razorpay (Webhooks)** | Payment & Subscription Webhooks | `NEEDS EXTERNAL CREDENTIALS` | Endpoint `POST /api/v1/billing/webhooks/razorpay` verifies HMAC SHA256 signature using `RAZORPAY_WEBHOOK_SECRET`. Handles `payment.captured`, `subscription.charged`, `subscription.cancelled`. Signature verification logic verified PASS (`tests/test_billing.py`). | In Razorpay Dashboard -> Settings -> Webhooks: add webhook URL `https://api.hirelens.ai/api/v1/billing/webhooks/razorpay` with secret. |
| **Stripe (Global)** | Checkout Sessions & Invoices | `NEEDS EXTERNAL CREDENTIALS` | `StripeGateway` in `backend/app/services/payment_gateways.py` implements Checkout Session creation (`stripe.checkout.Session.create`), customer mapping, and customer portal redirection. Mock tests PASS (`tests/test_billing.py`). | Requires live `STRIPE_PUBLISHABLE_KEY` and `STRIPE_SECRET_KEY` from Stripe Dashboard. |
| **Stripe (Webhooks)** | Subscription Lifecycle Webhooks | `NEEDS EXTERNAL CREDENTIALS` | Endpoint `POST /api/v1/billing/webhooks/stripe` verifies `Stripe-Signature` header via `stripe.Webhook.construct_event`. Handles `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`. Replay protection and signature verification verified PASS (`tests/test_billing.py`). | In Stripe Dashboard -> Developers -> Webhooks: add webhook endpoint `https://api.hirelens.ai/api/v1/billing/webhooks/stripe` and copy `whsec_...` signing secret. |
| **Google OAuth 2.0** | Sign-In & User Identity | `NEEDS EXTERNAL CREDENTIALS` | Implemented in `backend/app/api/v1/endpoints/oauth.py`. Exchanges Google authorization code for identity tokens (`email`, `name`, `sub`). Automated unit tests pass with mock tokens. | Requires Google Cloud Console project with OAuth 2.0 Client ID and Authorized Redirect URI `https://app.hirelens.ai/oauth/callback/google`. |
| **Google Calendar** | Interview Booking & Event Sync | `NEEDS EXTERNAL CREDENTIALS` | Service `GoogleCalendarService` in `backend/app/services/calendar_service.py` syncs interview slots, generates Google Meet links, and detects calendar conflicts via Google Calendar API v3. OAuth token encryption verified PASS (`tests/test_calendar_integrations.py`). | Requires Google Cloud verification for scope `https://www.googleapis.com/auth/calendar.events`. |
| **Microsoft OAuth 2.0** | Azure AD / Office 365 Sign-In | `NEEDS EXTERNAL CREDENTIALS` | Implemented in `backend/app/api/v1/endpoints/oauth.py` using MSAL / Microsoft Identity Platform endpoints. Automated unit tests pass with mock tokens. | Requires Azure Portal App Registration with Client ID, Secret, and Redirect URI `https://app.hirelens.ai/oauth/callback/microsoft`. |
| **Microsoft Outlook / Graph** | Outlook Calendar & Teams Links | `NEEDS EXTERNAL CREDENTIALS` | Service `OutlookCalendarService` in `backend/app/services/calendar_service.py` synchronizes events, creates Teams conference links, and resolves participant busy windows via Microsoft Graph API `/me/calendar/events`. Token encryption verified PASS (`tests/test_calendar_integrations.py`). | Requires Azure App permissions: `Calendars.ReadWrite`, `User.Read`. |
| **SMTP Delivery** | Transactional Notification Emails | `NEEDS EXTERNAL CREDENTIALS` | Service `EmailService` in `backend/app/services/notification_service.py` formats candidate invites, interview reminders, and invoice notifications. Celery worker dispatches emails asynchronously with exponential retry logic. Mock dispatch tests PASS (`tests/test_notifications.py`). | Requires production SMTP relay (SendGrid, AWS SES, Postmark, or Mailgun): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS`. |
| **AI Inference Provider** | LLM Copilot & Resume Parsing | `NEEDS EXTERNAL CREDENTIALS` | Service `AIService` in `backend/app/services/ai_service.py` supports dual modes: local Ollama (`http://localhost:11434`) and Hosted API (`https://api.openai.com/v1`). Fallback heuristics and grounding guards verified PASS (`tests/test_copilot.py`). | Configure `AI_PROVIDER=hosted`, `HOSTED_AI_API_KEY=sk-...`, and `HOSTED_AI_MODEL=gpt-4o-mini` in `.env`. |
| **Production Secret Rotation** | Zero-Downtime Secret Rotation | `PASS` | Runbook documented below in Section 3. Application architecture supports dual-key token transition and dynamic secret reloading upon process restart. | Follow documented step-by-step procedure. |

---

## 3. Production Secret Rotation Runbook

To maintain security compliance, external credentials and internal platform secrets must be rotated every 90 days or immediately following any security incident.

### 3.1 Application Secret Key (`SECRET_KEY`)
1. Generate a new high-entropy 64-character secret:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. Update `SECRET_KEY` in production environment vault / `.env`.
3. Perform a zero-downtime rolling restart of backend services:
   ```bash
   docker compose up -d --no-deps backend celery_worker celery_beat
   ```
4. Existing user refresh tokens remain valid if session tracking table is preserved; users re-authenticate seamlessly upon token expiry.

### 3.2 Payment Gateway Webhook Secrets
1. **Stripe:**
   - In Stripe Dashboard, navigate to **Developers -> Webhooks**.
   - Under the HireLens endpoint, click **Rotate signing secret**.
   - Stripe grants a 24-hour grace window where both the old and new secrets are recognized.
   - Update `STRIPE_WEBHOOK_SECRET` in production `.env` and restart backend.
2. **Razorpay:**
   - In Razorpay Dashboard, generate a new webhook secret.
   - Update `RAZORPAY_WEBHOOK_SECRET` in `.env` and restart backend.

### 3.3 Database Password Rotation
1. Connect to PostgreSQL cluster as superuser:
   ```sql
   ALTER USER hirelens WITH PASSWORD '<NEW_STRONG_PASSWORD>';
   ```
2. Update `DATABASE_URL` in backend and worker environment configurations.
3. Restart application containers to establish new pooled connections.

---

## 4. External Integration Readiness Assessment

| Integration Group | Readiness Verdict |
| :--- | :--- |
| **Core Application & Mock Adapters** | `PASS` (Fully tested and verified in automated suites) |
| **Live External Gateway Credentials** | `NEEDS EXTERNAL CREDENTIALS` (Pending client API key provisioning) |
| **Overall Integration Verdict** | **CONDITIONAL GO** |
