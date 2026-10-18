# HireLens AI — Final Razorpay Sandbox Verification Report

**System:** HireLens AI Platform  
**Target Project:** `D:\HireLens`  
**Audit Date:** October 18, 2026  
**Auditor:** Antigravity Autonomous Security & Integration Engineering  
**Scope:** Razorpay Gateway Adapter, Checkout Order Generation, HMAC-SHA256 Signature Verification, Webhook Deduplication, Subscription & Invoice Synchronization  
**Status:** **OPERATIONAL & CODE VERIFIED (REQUIRES MERCHANT CREDENTIAL INJECTION)**

---

## 1. Executive Summary

The Razorpay integration provides domestic Indian payment processing (INR) supporting both monthly and annual subscription tiers. Architectural verification was performed via unit, adapter, and API tests (`tests/test_external_integrations_sandbox.py` and `tests/test_billing.py`).

All cryptographic verification algorithms, checkout session generation, forged signature protections, webhook replay defenses, and subscription upgrade lifecycles are **100% verified and passing**.

---

## 2. Configuration & Parameter Audit

| Configuration Parameter | Environment Variable | Current Value | Required For Production |
| :--- | :--- | :--- | :--- |
| **Merchant Key ID** | `RAZORPAY_KEY_ID` | Not set / Unconfigured | Merchant identification in standard checkout. |
| **Merchant Key Secret** | `RAZORPAY_KEY_SECRET` | Not set / Unconfigured | Server-side HMAC-SHA256 verification of `order_id\|payment_id`. |
| **Webhook Secret** | `RAZORPAY_WEBHOOK_SECRET` | Not set / Unconfigured | Authenticating incoming webhook payloads via `X-Razorpay-Signature`. |
| **Default Currency** | Hardcoded in adapter | `INR` | Strict INR enforcement for Indian domestic regulatory compliance. |

---

## 3. Verification Assessment Matrix

| Verification Item | Classification | Actual Evidence & Test Results | Precise Remediation Steps |
| :--- | :--- | :--- | :--- |
| **1. Unconfigured Credentials Guard** | `PASS` | `test_razorpay_unconfigured_credentials_rejection`: When `RAZORPAY_KEY_ID` or `RAZORPAY_KEY_SECRET` is unset, adapter returns HTTP 503 Service Unavailable, safely instructing the client to use MOCK mode in non-production environments. | Keep default behavior; inject valid test keys when activating sandbox testing. |
| **2. Checkout Order Creation** | `PASS` | `test_razorpay_sandbox_checkout_order_creation`: Generates structured checkout session containing `session_id`, `order_id` (prefixed `order_rzp_`), `publishable_key`, `amount` in standard currency units and paise calculation, and `currency: INR`. | Inject `RAZORPAY_KEY_ID` in production `.env`. |
| **3. Payment Signature Verification** | `PASS` | `test_razorpay_signature_verification_and_forgery_rejection`: Correctly computes `hmac.new(key_secret, f"{order_id}\|{payment_id}".encode(), sha256).hexdigest()`. Matches signature via constant-time `hmac.compare_digest()`. | No code changes needed. |
| **4. Forged Signature Rejection** | `PASS` | `test_razorpay_signature_verification_and_forgery_rejection`: Tampered or forged signatures are rejected with `is_valid=False` and clear error description without altering database state. | No code changes needed. |
| **5. Webhook Signature Verification** | `PASS` | `test_razorpay_webhook_signature_and_deduplication`: Verifies `X-Razorpay-Signature` header over raw body bytes against `RAZORPAY_WEBHOOK_SECRET`. Invalid signatures return HTTP 400 Bad Request. | Configure webhook endpoint in Razorpay Dashboard pointing to `/api/v1/billing/webhooks/RAZORPAY`. |
| **6. Duplicate Webhook / Idempotency** | `PASS` | `test_razorpay_webhook_signature_and_deduplication`: Deduplication queries `PaymentWebhookEvent.event_id`. First submission returns `{"status": "processed"}`; replay with same event ID returns `{"status": "ignored"}`. | No code changes needed. |
| **7. Subscription & Invoice Synchronization** | `PASS` | `test_checkout_and_payment_activation`: On payment verification, subscription status updates to `ACTIVE`, period bounds extend by 30 or 365 days, `SubscriptionHistory` record is logged, and a formal GST-compliant tax invoice (`HL-INV-...`) is generated. | Ensure company legal address and GSTIN profile are updated in agency settings. |
| **8. Live Merchant API Connectivity** | `NEEDS CREDENTIALS` | Machine environment contains no live Razorpay test keys (`RAZORPAY_KEY_ID=False`, `RAZORPAY_KEY_SECRET=False`). | Generate test keys in Razorpay Dashboard and add to `.env`. |
| **9. Razorpay Dashboard Webhook Registration** | `NEEDS PROVIDER CONFIGURATION` | Webhook URL has not been registered in an active Razorpay merchant portal. | In Razorpay Dashboard -> Settings -> Webhooks, add URL: `https://<DOMAIN>/api/v1/billing/webhooks/RAZORPAY`, events: `payment.captured`, `payment.failed`, `subscription.charged`. Set secret matching `RAZORPAY_WEBHOOK_SECRET`. |

---

## 4. Operational Runbook: Enabling Razorpay Sandbox

To enable live Razorpay test transactions:

1. **Create Razorpay Account:**
   - Log into [https://dashboard.razorpay.com](https://dashboard.razorpay.com).
   - Switch toggle at top-left to **Test Mode**.
2. **Generate API Keys:**
   - Navigate to **Settings** -> **API Keys** -> **Generate Test Key**.
   - Copy **Key Id** and **Key Secret**.
3. **Configure Webhook:**
   - Navigate to **Settings** -> **Webhooks** -> **Add New Webhook**.
   - URL: `https://<YOUR_DEPLOYED_DOMAIN>/api/v1/billing/webhooks/RAZORPAY`
   - Secret: Generate a 32-character random string (e.g., `openssl rand -hex 16`).
   - Active Events:
     - `payment.authorized`
     - `payment.captured`
     - `payment.failed`
     - `subscription.charged`
4. **Deploy Environment Variables:**
   ```bash
   RAZORPAY_KEY_ID="<YOUR_RAZORPAY_KEY_ID>"
   RAZORPAY_KEY_SECRET="<YOUR_RAZORPAY_KEY_SECRET>"
   RAZORPAY_WEBHOOK_SECRET="<YOUR_RAZORPAY_WEBHOOK_SECRET>"
   ```
5. **Execute Verification Test:**
   ```bash
   pytest tests/test_external_integrations_sandbox.py -k "razorpay" -v
   ```

---

## 5. Security & Isolation Safeguards
- **Zero Log Leakage:** Key secrets and webhook secrets are never logged in plain text.
- **Timing Attack Resistance:** Constant-time `hmac.compare_digest()` prevents timing attack vectors.
- **Atomic Billing Updates:** Invoice creation and subscription activation occur within a single database transaction.
