# HireLens AI — Phase 14: Payment Provider Configuration & Setup Guide

This guide details how to configure **Razorpay** (for domestic Indian payments in INR via UPI, Cards, Netbanking) and **Stripe** (for international payments in USD and global currencies), as well as utilizing the built-in **Mock Gateway** for automated testing and local development.

---

## 1. Gateway Architecture Overview

HireLens AI uses a unified provider abstraction (`PaymentGatewayProvider`) in `backend/app/services/payment_gateways.py`.

```
                    ┌────────────────────────┐
                    │  PaymentGatewayProvider│
                    └───────────┬────────────┘
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ RazorpayAdapter  │  │  StripeAdapter   │  │ MockPaymentAdapter│
│ (India / INR)    │  │  (Global / USD)  │  │ (Automated Tests)│
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

- When provider credentials are not configured, the platform safely stays in sandbox mode without breaking server startup.
- The frontend dynamically displays available gateways and formats currency based on the selected provider.

---

## 2. Environment Variables Configuration

Create or update your `.env` file in `d:\HireLens\backend\.env`:

```env
# =====================================================================
# PHASE 14: PAYMENT GATEWAY CONFIGURATION
# =====================================================================

# --- Razorpay (Domestic India / INR) ---
RAZORPAY_KEY_ID="rzp_test_YourTestKeyIdHere"
RAZORPAY_KEY_SECRET="YourTestKeySecretHere"
RAZORPAY_WEBHOOK_SECRET="YourRazorpayWebhookSecretHere"

# --- Stripe (International / USD) ---
STRIPE_PUBLISHABLE_KEY="pk_test_YourStripePublishableKeyHere"
STRIPE_SECRET_KEY="sk_test_YourStripeSecretKeyHere"
STRIPE_WEBHOOK_SECRET="whsec_YourStripeWebhookSecretHere"

# --- Currency & Tax Defaults ---
DEFAULT_BILLING_CURRENCY="INR"
INDIA_GST_PERCENTAGE="18.0"
PLATFORM_COMPANY_NAME="HireLens AI Technologies Pvt Ltd"
PLATFORM_GSTIN="29AAAAA0000A1Z5"
```

---

## 3. Razorpay Setup Instructions (India / INR)

### 3.1 Account & API Keys
1. Sign up or log into the [Razorpay Dashboard](https://dashboard.razorpay.com/).
2. Switch to **Test Mode** (toggle in the top-right header).
3. Navigate to **Account & Settings &rarr; API Keys**.
4. Click **Generate Test Key**.
5. Copy the generated `Key ID` and `Key Secret` into `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`.

### 3.2 Webhook Configuration
1. In the Razorpay Dashboard, go to **Account & Settings &rarr; Webhooks**.
2. Click **Add New Webhook**.
3. Set **Webhook URL** to:
   ```
   https://api.yourdomain.com/api/v1/billing/webhooks/razorpay
   ```
   *(For local testing, use ngrok or cloudflare tunnel: `https://<subdomain>.ngrok.io/api/v1/billing/webhooks/razorpay`)*.
4. Set **Secret** and copy this exact string into `RAZORPAY_WEBHOOK_SECRET`.
5. Select the following **Active Events**:
   - `payment.authorized`
   - `payment.captured`
   - `payment.failed`
   - `order.paid`
   - `refund.processed`
6. Click **Save**.

### 3.3 Test Payment Credentials (Razorpay Sandbox)
- **UPI ID:** `success@razorpay` (or any valid UPI format e.g. `test@okhdfcbank`)
- **Card Number:** `4111 1111 1111 1111`
- **Expiry:** Any future date (e.g. `12/28`)
- **CVV:** `123`
- **OTP:** `123456`

---

## 4. Stripe Setup Instructions (International / USD)

### 4.1 Account & API Keys
1. Sign up or log into the [Stripe Dashboard](https://dashboard.stripe.com/).
2. Ensure **Test mode** toggle is activated.
3. Navigate to **Developers &rarr; API keys**.
4. Copy the **Publishable key** (`pk_test_...`) and **Secret key** (`sk_test_...`) into your environment variables.

### 4.2 Webhook Configuration
1. Go to **Developers &rarr; Webhooks**.
2. Click **Add an endpoint**.
3. Set **Endpoint URL** to:
   ```
   https://api.yourdomain.com/api/v1/billing/webhooks/stripe
   ```
4. Select the following events:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `charge.refunded`
5. Click **Add endpoint**.
6. Reveal the **Signing secret** (`whsec_...`) and paste into `STRIPE_WEBHOOK_SECRET`.

---

## 5. Mock Payment Gateway (Local Development & CI/CD)

The HireLens codebase includes a production-grade `MockPaymentAdapter` for local development and CI testing that requires **zero external credentials**:

- Always available when `gateway="MOCK"`.
- Generates valid mock checkout sessions and order IDs.
- Creates test verification signatures pre-signed by the backend.
- Automatically records `PaymentTransaction`, updates `AgencySubscription`, and generates standard `BillingInvoice` records.

### Initiating Checkout via Mock Gateway in Frontend:
1. Navigate to `/settings/billing`.
2. Select any plan (e.g., *Professional* or *Business*).
3. In the checkout modal, click **Mock Gateway (Test Sandbox)**.
4. Click **Initiate Secure Checkout Session**.
5. Click **Confirm & Activate Subscription**.
6. Subscription activates immediately, meter quotas expand, and an immutable tax invoice is generated.

---

## 6. Verification Checklist

Before deploying live billing:
- [ ] Valid `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` configured in environment.
- [ ] Valid `RAZORPAY_WEBHOOK_SECRET` configured and verified with test signature.
- [ ] Valid `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` configured in environment.
- [ ] Webhook endpoints reachable via public HTTPS with valid SSL certificates.
- [ ] Ensure database contains seeded subscription plans via `alembic upgrade head`.
- [ ] Verify GSTIN tax invoices display correct company details and 18% GST itemization.
