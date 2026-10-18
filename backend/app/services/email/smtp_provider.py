import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple

from app.core.config import settings
from app.services.email.base import EmailProvider, EmailMessage

logger = logging.getLogger(__name__)


class SmtpEmailProvider(EmailProvider):
    """Production SMTP provider with TLS support and safe error masking."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.username = username or settings.SMTP_USER
        self.password = password or settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_TLS

    @property
    def name(self) -> str:
        return "smtp"

    def send_email(self, message: EmailMessage) -> Tuple[bool, Optional[str]]:
        if not self.host:
            return False, "SMTP_HOST is not configured."

        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        from_name = message.from_name or settings.EMAILS_FROM_NAME
        from_email = message.from_email or settings.EMAILS_FROM_EMAIL
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = f"{message.to_name} <{message.to_email}>" if message.to_name else message.to_email

        part_text = MIMEText(message.body_text, "plain", "utf-8")
        part_html = MIMEText(message.body_html, "html", "utf-8")
        msg.attach(part_text)
        msg.attach(part_html)

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(from_email, [message.to_email], msg.as_string())
            return True, None
        except smtplib.SMTPException as exc:
            # Mask any internal credentials from error string
            safe_err = f"SMTP protocol error: {exc.__class__.__name__}"
            logger.error("SMTP error sending to %s: %s", message.to_email, safe_err)
            return False, safe_err
        except Exception as exc:
            safe_err = f"Connection error: {exc.__class__.__name__}"
            logger.error("Error sending to %s: %s", message.to_email, safe_err)
            return False, safe_err
