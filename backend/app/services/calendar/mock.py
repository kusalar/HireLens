import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.services.calendar.base import (
    BaseCalendarProvider,
    CalendarEventResult,
    CalendarAuthException,
    CalendarRateLimitException,
    CalendarProviderException,
)


class MockCalendarProvider(BaseCalendarProvider):
    """
    Deterministic Mock Calendar Provider for automated tests and offline development.
    Simulates Google and Microsoft behavior without external network calls.
    """

    def __init__(self, provider_name: str = "mock"):
        self.provider_name = provider_name
        self.events: Dict[str, Dict[str, Any]] = {}
        # Fault injection hooks for testing error recovery and retries
        self.should_fail_auth: bool = False
        self.should_rate_limit: bool = False
        self.should_fail_transient: bool = False

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return f"https://auth.hirelens.mock/oauth/authorize?response_type=code&client_id=mock_client&redirect_uri={redirect_uri}&state={state}&scope=calendar"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        if self.should_fail_auth or code == "invalid_code":
            raise CalendarAuthException("Invalid OAuth authorization code.")
        
        return {
            "access_token": f"mock_access_token_{uuid.uuid4().hex[:12]}",
            "refresh_token": f"mock_refresh_token_{uuid.uuid4().hex[:16]}",
            "expires_in": 3600,
            "account_id": "mock_user_12345",
            "account_email": "recruiter@example.com",
        }

    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        if self.should_fail_auth or refresh_token == "revoked_refresh_token":
            raise CalendarAuthException("Refresh token revoked or expired.")

        return {
            "access_token": f"mock_refreshed_token_{uuid.uuid4().hex[:12]}",
            "refresh_token": refresh_token,
            "expires_in": 3600,
        }

    def list_calendars(self, access_token: str) -> List[Dict[str, Any]]:
        if self.should_fail_auth:
            raise CalendarAuthException("Unauthorized access token.")

        return [
            {"id": "primary", "name": "Primary Calendar", "primary": True, "read_only": False},
            {"id": "interviews_cal", "name": "HireLens Interviews", "primary": False, "read_only": False},
        ]

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
        if self.should_fail_auth:
            raise CalendarAuthException("Invalid credentials.")
        if self.should_rate_limit:
            raise CalendarRateLimitException("Rate limit reached.", retry_after=5)
        if self.should_fail_transient:
            raise CalendarProviderException("Transient network timeout.", status_code=503, is_transient=True)

        event_id = f"mock_evt_{uuid.uuid4().hex[:16]}"
        meeting_link = None
        if generate_meeting:
            if "microsoft" in self.provider_name.lower():
                meeting_link = f"https://teams.microsoft.com/l/meetup-join/mock-{event_id}"
            else:
                meeting_link = f"https://meet.google.com/mock-{event_id[:3]}-{event_id[3:7]}-{event_id[7:10]}"

        event_data = {
            "id": event_id,
            "calendar_id": calendar_id,
            "title": title,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "timezone": timezone_str,
            "attendees": attendees,
            "location": location,
            "meeting_link": meeting_link,
            "status": "confirmed",
        }
        self.events[event_id] = event_data

        return CalendarEventResult(
            event_id=event_id,
            status="confirmed",
            start_time=start_time,
            end_time=end_time,
            timezone=timezone_str,
            title=title,
            meeting_link=meeting_link,
            html_link=f"https://calendar.hirelens.mock/event/{event_id}",
            raw_response=event_data,
        )

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
        if self.should_fail_auth:
            raise CalendarAuthException("Invalid credentials.")
        if self.should_rate_limit:
            raise CalendarRateLimitException("Rate limit reached.", retry_after=5)
        if self.should_fail_transient:
            raise CalendarProviderException("Transient network timeout.", status_code=503, is_transient=True)

        event_data = self.events.get(event_id, {
            "id": event_id,
            "calendar_id": calendar_id,
        })
        event_data.update({
            "title": title,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "timezone": timezone_str,
            "attendees": attendees,
            "location": location,
            "meeting_link": meeting_link or event_data.get("meeting_link"),
            "status": "confirmed",
        })
        self.events[event_id] = event_data

        return CalendarEventResult(
            event_id=event_id,
            status="confirmed",
            start_time=start_time,
            end_time=end_time,
            timezone=timezone_str,
            title=title,
            meeting_link=event_data.get("meeting_link"),
            html_link=f"https://calendar.hirelens.mock/event/{event_id}",
            raw_response=event_data,
        )

    def cancel_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
    ) -> bool:
        if self.should_fail_auth:
            raise CalendarAuthException("Invalid credentials.")
        if self.should_rate_limit:
            raise CalendarRateLimitException("Rate limit reached.", retry_after=5)

        if event_id in self.events:
            self.events[event_id]["status"] = "cancelled"
        return True

    def get_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
    ) -> Optional[CalendarEventResult]:
        if self.should_fail_auth:
            raise CalendarAuthException("Invalid credentials.")

        event_data = self.events.get(event_id)
        if not event_data:
            return None

        return CalendarEventResult(
            event_id=event_id,
            status=event_data.get("status", "confirmed"),
            start_time=event_data["start_time"],
            end_time=event_data["end_time"],
            timezone=event_data["timezone"],
            title=event_data["title"],
            meeting_link=event_data.get("meeting_link"),
            html_link=f"https://calendar.hirelens.mock/event/{event_id}",
            raw_response=event_data,
        )
