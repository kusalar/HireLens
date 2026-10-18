from typing import List, Optional, Tuple
from app.services.email.base import EmailProvider, EmailMessage


class MockEmailProvider(EmailProvider):
    """In-memory mock provider for testing email event dispatch, templates, and idempotency."""

    def __init__(self):
        self.sent_messages: List[EmailMessage] = []
        self.fail_next: bool = False
        self.failure_reason: str = "Simulated provider failure"

    @property
    def name(self) -> str:
        return "mock"

    def send_email(self, message: EmailMessage) -> Tuple[bool, Optional[str]]:
        if self.fail_next:
            self.fail_next = False
            return False, self.failure_reason

        self.sent_messages.append(message)
        return True, None

    def clear(self):
        self.sent_messages.clear()
        self.fail_next = False


# Global singleton instance for unit test assertions
mock_email_provider = MockEmailProvider()
