from typing import Optional
from app.core.config import settings
from app.services.email.base import EmailProvider
from app.services.email.console_provider import ConsoleEmailProvider
from app.services.email.smtp_provider import SmtpEmailProvider
from app.services.email.mock_provider import mock_email_provider


def get_email_provider(override_name: Optional[str] = None) -> EmailProvider:
    provider_type = (override_name or settings.EMAIL_PROVIDER or "console").lower().strip()

    if provider_type == "mock":
        return mock_email_provider
    elif provider_type == "smtp":
        return SmtpEmailProvider()
    else:
        return ConsoleEmailProvider()
