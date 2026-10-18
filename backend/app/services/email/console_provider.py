import logging
from typing import Optional, Tuple
from app.services.email.base import EmailProvider, EmailMessage

logger = logging.getLogger(__name__)


class ConsoleEmailProvider(EmailProvider):
    """Development-safe provider that logs delivery attempts without contacting external servers."""

    @property
    def name(self) -> str:
        return "console"

    def send_email(self, message: EmailMessage) -> Tuple[bool, Optional[str]]:
        try:
            logger.info(
                "[CONSOLE EMAIL DELIVERED] To: %s <%s> | Subject: %s | Length HTML: %d, Text: %d",
                message.to_name or "Recipient",
                message.to_email,
                message.subject,
                len(message.body_html),
                len(message.body_text),
            )
            return True, None
        except Exception as exc:
            logger.error("Failed to log console email to %s: %s", message.to_email, exc)
            return False, str(exc)
