from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class CalendarProviderException(Exception):
    """Base exception for calendar provider operations."""
    def __init__(self, message: str, status_code: int = 500, is_transient: bool = False, retry_after: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.is_transient = is_transient
        self.retry_after = retry_after


class CalendarAuthException(CalendarProviderException):
    """Exception raised when OAuth authorization fails or token is revoked."""
    def __init__(self, message: str):
        super().__init__(message, status_code=401, is_transient=False)


class CalendarRateLimitException(CalendarProviderException):
    """Exception raised when provider rate limit is exceeded."""
    def __init__(self, message: str, retry_after: Optional[int] = 60):
        super().__init__(message, status_code=429, is_transient=True, retry_after=retry_after)


class CalendarEventResult:
    """Standardized result returned by calendar provider adapters."""
    def __init__(
        self,
        event_id: str,
        status: str,
        start_time: datetime,
        end_time: datetime,
        timezone: str,
        title: str,
        meeting_link: Optional[str] = None,
        html_link: Optional[str] = None,
        raw_response: Optional[Dict[str, Any]] = None,
    ):
        self.event_id = event_id
        self.status = status
        self.start_time = start_time
        self.end_time = end_time
        self.timezone = timezone
        self.title = title
        self.meeting_link = meeting_link
        self.html_link = html_link
        self.raw_response = raw_response or {}


class BaseCalendarProvider(ABC):
    """Abstract interface for external calendar providers."""

    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Construct the OAuth authorization code URL."""
        pass

    @abstractmethod
    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for tokens.
        Expected return dictionary:
        {
            "access_token": str,
            "refresh_token": Optional[str],
            "expires_in": int (seconds),
            "account_id": Optional[str],
            "account_email": Optional[str],
        }
        """
        pass

    @abstractmethod
    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh expired access token.
        Expected return dictionary:
        {
            "access_token": str,
            "refresh_token": Optional[str],
            "expires_in": int,
        }
        """
        pass

    @abstractmethod
    def list_calendars(self, access_token: str) -> List[Dict[str, Any]]:
        """
        List calendars available in the user's account.
        Returns list of dicts: [{"id": str, "name": str, "primary": bool, "read_only": bool}]
        """
        pass

    @abstractmethod
    def create_event(
        self,
        access_token: str,
        calendar_id: str,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        timezone_str: str,
        attendees: List[Dict[str, str]],
        location: Optional[str] = None,
        generate_meeting: bool = False,
    ) -> CalendarEventResult:
        """Create a new calendar event."""
        pass

    @abstractmethod
    def update_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        timezone_str: str,
        attendees: List[Dict[str, str]],
        location: Optional[str] = None,
        meeting_link: Optional[str] = None,
    ) -> CalendarEventResult:
        """Update an existing calendar event."""
        pass

    @abstractmethod
    def cancel_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
    ) -> bool:
        """Cancel or remove an event from the calendar."""
        pass

    @abstractmethod
    def get_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
    ) -> Optional[CalendarEventResult]:
        """Fetch event details from external provider."""
        pass
