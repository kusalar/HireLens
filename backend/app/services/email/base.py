from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class EmailMessage:
    to_email: str
    subject: str
    body_html: str
    body_text: str
    to_name: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None


class EmailProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'console', 'smtp', 'mock')."""
        pass

    @abstractmethod
    def send_email(self, message: EmailMessage) -> Tuple[bool, Optional[str]]:
        """Send an email message.
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        pass
