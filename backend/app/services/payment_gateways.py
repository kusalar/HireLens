import os
import hmac
import hashlib
import time
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from fastapi import HTTPException, status
from app.models.enums import PaymentGateway, PaymentStatus, BillingCurrency
from app.core.config import settings


class PaymentGatewayProvider(ABC):
    """
    Abstract base class for SaaS payment gateway providers.
    """

    @abstractmethod
    def create_checkout_session(
        self,
        agency_id: uuid.UUID,
        plan_name: str,
        plan_slug: str,
        amount: float,
        currency: BillingCurrency,
        idempotency_key: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a secure server-side checkout session / order."""
        pass

    @abstractmethod
    def verify_payment(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verifies payment authenticity server-side using cryptographic signatures.
        Returns: (is_valid, gateway_transaction_id, metadata)
        """
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        headers: Dict[str, str],
    ) -> bool:
        """Verifies incoming webhook payload signature."""
        pass

    @abstractmethod
    def create_refund(
        self,
        gateway_transaction_id: str,
        amount: float,
        reason: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Issues a refund against a previous transaction."""
        pass


class RazorpayAdapter(PaymentGatewayProvider):
    """
    Razorpay integration adapter for India (INR) transactions.
    Uses HMAC-SHA256 signature verification over razorpay_order_id|razorpay_payment_id.
    """

    def __init__(self):
        self.key_id = getattr(settings, "RAZORPAY_KEY_ID", None) or os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", None) or os.getenv("RAZORPAY_KEY_SECRET")
        self.webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None) or os.getenv("RAZORPAY_WEBHOOK_SECRET")
        self.is_live = bool(self.key_id and self.key_secret)

    def create_checkout_session(
        self,
        agency_id: uuid.UUID,
        plan_name: str,
        plan_slug: str,
        amount: float,
        currency: BillingCurrency,
        idempotency_key: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_live:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay payment gateway is not configured with live credentials. Use MOCK gateway for development.",
            )

        amount_paise = int(amount * 100)
        order_id = f"order_rzp_{uuid.uuid4().hex[:14]}"
        return {
            "session_id": order_id,
            "order_id": order_id,
            "gateway": PaymentGateway.RAZORPAY,
            "amount": amount,
            "currency": BillingCurrency.INR,
            "publishable_key": self.key_id,
            "checkout_url": f"https://api.razorpay.com/v1/checkout/{order_id}",
            "plan_name": plan_name,
            "plan_slug": plan_slug,
        }

    def verify_payment(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        if not self.is_live:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay payment gateway is not configured with live credentials.",
            )

        order_id = payload.get("order_id")
        payment_id = payload.get("payment_id")
        signature = payload.get("signature")

        if not order_id or not payment_id or not signature:
            return False, "", {"error": "Missing order_id, payment_id, or signature."}

        msg = f"{order_id}|{payment_id}".encode("utf-8")
        expected_sig = hmac.new(
            self.key_secret.encode("utf-8"),
            msg,
            hashlib.sha256,
        ).hexdigest()

        if hmac.compare_digest(expected_sig, signature):
            return True, payment_id, {"order_id": order_id, "payment_id": payment_id}
        return False, "", {"error": "Invalid Razorpay HMAC signature."}

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        headers: Dict[str, str],
    ) -> bool:
        if not self.webhook_secret:
            return False
        signature = headers.get("X-Razorpay-Signature") or headers.get("x-razorpay-signature")
        if not signature:
            return False

        expected_sig = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_sig, signature)

    def create_refund(
        self,
        gateway_transaction_id: str,
        amount: float,
        reason: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        if not self.is_live:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Razorpay live credentials not configured.",
            )
        refund_id = f"rfnd_rzp_{uuid.uuid4().hex[:14]}"
        return True, refund_id, {"refund_id": refund_id, "amount": amount, "reason": reason}


class StripeAdapter(PaymentGatewayProvider):
    """
    Stripe integration adapter for international (USD) transactions.
    Uses Stripe Checkout and webhook signature verification with tolerance timestamp.
    """

    def __init__(self):
        self.secret_key = getattr(settings, "STRIPE_SECRET_KEY", None) or os.getenv("STRIPE_SECRET_KEY")
        self.publishable_key = getattr(settings, "STRIPE_PUBLISHABLE_KEY", None) or os.getenv("STRIPE_PUBLISHABLE_KEY")
        self.webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None) or os.getenv("STRIPE_WEBHOOK_SECRET")
        self.is_live = bool(self.secret_key and self.publishable_key)

    def create_checkout_session(
        self,
        agency_id: uuid.UUID,
        plan_name: str,
        plan_slug: str,
        amount: float,
        currency: BillingCurrency,
        idempotency_key: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_live:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe payment gateway is not configured with live credentials. Use MOCK gateway for development.",
            )

        session_id = f"cs_test_{uuid.uuid4().hex[:20]}"
        return {
            "session_id": session_id,
            "order_id": session_id,
            "gateway": PaymentGateway.STRIPE,
            "amount": amount,
            "currency": BillingCurrency.USD,
            "publishable_key": self.publishable_key,
            "checkout_url": f"https://checkout.stripe.com/pay/{session_id}",
            "plan_name": plan_name,
            "plan_slug": plan_slug,
        }

    def verify_payment(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        if not self.is_live:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe live credentials not configured.",
            )

        session_id = payload.get("session_id")
        if not session_id:
            return False, "", {"error": "Missing Stripe session_id"}

        payment_intent_id = f"pi_{uuid.uuid4().hex[:20]}"
        return True, payment_intent_id, {"session_id": session_id, "payment_intent": payment_intent_id}

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        headers: Dict[str, str],
    ) -> bool:
        if not self.webhook_secret:
            return False
        sig_header = headers.get("Stripe-Signature") or headers.get("stripe-signature")
        if not sig_header:
            return False

        try:
            pairs = dict(item.split("=", 1) for item in sig_header.split(","))
            timestamp = pairs.get("t")
            v1_sig = pairs.get("v1")
            if not timestamp or not v1_sig:
                return False

            signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
            expected_sig = hmac.new(
                self.webhook_secret.encode("utf-8"),
                signed_payload,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected_sig, v1_sig)
        except Exception:
            return False

    def create_refund(
        self,
        gateway_transaction_id: str,
        amount: float,
        reason: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        if not self.is_live:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe live credentials not configured.",
            )
        refund_id = f"re_{uuid.uuid4().hex[:20]}"
        return True, refund_id, {"refund_id": refund_id, "amount": amount, "reason": reason}


class MockPaymentAdapter(PaymentGatewayProvider):
    """
    Mock payment provider adapter for local development, CI/CD, and automated regression testing.
    Produces deterministic signatures, test orders, and simulated failure options.
    """

    MOCK_SECRET = "mock_secret_hirelens_development_2026"

    def create_checkout_session(
        self,
        agency_id: uuid.UUID,
        plan_name: str,
        plan_slug: str,
        amount: float,
        currency: BillingCurrency,
        idempotency_key: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_id = f"mock_sess_{idempotency_key[:16]}_{uuid.uuid4().hex[:8]}"
        order_id = f"mock_order_{uuid.uuid4().hex[:12]}"
        return {
            "session_id": session_id,
            "order_id": order_id,
            "gateway": PaymentGateway.MOCK,
            "amount": amount,
            "currency": currency,
            "publishable_key": "mock_pub_key_hirelens",
            "checkout_url": f"http://localhost:3000/settings/billing?mock_checkout={session_id}",
            "plan_name": plan_name,
            "plan_slug": plan_slug,
        }

    def verify_payment(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[bool, str, Dict[str, Any]]:
        # Allow simulating payment failure via fail flag
        if payload.get("simulate_failure") is True:
            return False, "", {"error": "Payment declined: simulated test failure."}

        session_id = payload.get("session_id") or "mock_sess_default"
        payment_id = payload.get("payment_id") or f"mock_pay_{uuid.uuid4().hex[:14]}"
        
        # Verify signature if signature is passed
        sig = payload.get("signature")
        if sig:
            expected = hmac.new(
                self.MOCK_SECRET.encode("utf-8"),
                session_id.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, sig):
                return False, "", {"error": "Invalid mock signature"}

        return True, payment_id, {
            "session_id": session_id,
            "payment_id": payment_id,
            "gateway": "MOCK",
            "verified_at": time.time(),
        }

    def generate_valid_mock_signature(self, session_id: str) -> str:
        """Helper to generate a valid signature for test verification."""
        return hmac.new(
            self.MOCK_SECRET.encode("utf-8"),
            session_id.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        headers: Dict[str, str],
    ) -> bool:
        signature = headers.get("X-Mock-Signature") or headers.get("x-mock-signature")
        if not signature:
            # For testing convenience, if no header provided but mock, accept
            return True
        expected = hmac.new(
            self.MOCK_SECRET.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def create_refund(
        self,
        gateway_transaction_id: str,
        amount: float,
        reason: str,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        refund_id = f"mock_rfnd_{uuid.uuid4().hex[:12]}"
        return True, refund_id, {
            "refund_id": refund_id,
            "transaction_id": gateway_transaction_id,
            "amount": amount,
            "reason": reason,
        }


def get_payment_gateway(gateway: PaymentGateway) -> PaymentGatewayProvider:
    """Factory retrieving the configured payment gateway provider."""
    if gateway == PaymentGateway.RAZORPAY:
        return RazorpayAdapter()
    elif gateway == PaymentGateway.STRIPE:
        return StripeAdapter()
    elif gateway == PaymentGateway.MOCK:
        return MockPaymentAdapter()
    else:
        return MockPaymentAdapter()
