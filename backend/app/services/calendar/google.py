import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings
from app.services.calendar.base import (
    BaseCalendarProvider,
    CalendarEventResult,
    CalendarAuthException,
    CalendarRateLimitException,
    CalendarProviderException,
)


class GoogleCalendarProvider(BaseCalendarProvider):
    """Google Calendar Provider adapter using Google Calendar v3 REST API."""

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.client_id = client_id or settings.GOOGLE_CLIENT_ID
        self.client_secret = client_secret or settings.GOOGLE_CLIENT_SECRET
        self.timeout = timeout

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id or "",
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(settings.GOOGLE_CALENDAR_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "include_granted_scopes": "true",
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(self.TOKEN_URL, data=data)
                if res.status_code in (400, 401):
                    raise CalendarAuthException(f"Google token exchange failed: {res.text}")
                res.raise_for_status()
                token_data = res.json()

                # Fetch user profile to get account ID and email
                access_token = token_data.get("access_token")
                account_id = None
                account_email = None
                if access_token:
                    headers = {"Authorization": f"Bearer {access_token}"}
                    profile_res = client.get(self.USERINFO_URL, headers=headers)
                    if profile_res.status_code == 200:
                        profile = profile_res.json()
                        account_id = profile.get("id")
                        account_email = profile.get("email")

                return {
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in", 3600),
                    "account_id": account_id,
                    "account_email": account_email,
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (400, 401):
                raise CalendarAuthException(f"Google token exchange rejected: {e.response.text}")
            raise CalendarProviderException(f"Google API HTTP error: {str(e)}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error contacting Google: {str(e)}", is_transient=True)

    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        data = {
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(self.TOKEN_URL, data=data)
                if res.status_code in (400, 401):
                    raise CalendarAuthException(f"Google token refresh rejected: {res.text}")
                res.raise_for_status()
                token_data = res.json()
                return {
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token") or refresh_token,
                    "expires_in": token_data.get("expires_in", 3600),
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (400, 401):
                raise CalendarAuthException(f"Google refresh token expired or revoked: {e.response.text}")
            raise CalendarProviderException(f"Google token refresh error: {str(e)}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error refreshing Google token: {str(e)}", is_transient=True)

    def list_calendars(self, access_token: str) -> List[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{self.CALENDAR_API_BASE}/users/me/calendarList"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 401:
                    raise CalendarAuthException("Google access token invalid or expired.")
                if res.status_code == 429:
                    raise CalendarRateLimitException("Google Calendar rate limit exceeded.")
                res.raise_for_status()
                items = res.json().get("items", [])
                calendars = []
                for item in items:
                    calendars.append({
                        "id": item.get("id"),
                        "name": item.get("summary", "Unnamed Calendar"),
                        "primary": item.get("primary", False),
                        "read_only": item.get("accessRole") == "reader",
                    })
                return calendars
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise CalendarAuthException("Google access token invalid or expired.")
            raise CalendarProviderException(f"Failed to list Google calendars: {str(e)}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error listing Google calendars: {str(e)}", is_transient=True)

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
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        encoded_cal_id = urllib.parse.quote(calendar_id or "primary")
        url = f"{self.CALENDAR_API_BASE}/calendars/{encoded_cal_id}/events"
        params = {}

        event_body: Dict[str, Any] = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": timezone_str,
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": timezone_str,
            },
            "attendees": [{"email": a.get("email"), "displayName": a.get("name")} for a in attendees if a.get("email")],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 15},
                ],
            },
        }
        if location:
            event_body["location"] = location

        if generate_meeting:
            params["conferenceDataVersion"] = "1"
            import uuid
            event_body["conferenceData"] = {
                "createRequest": {
                    "requestId": f"hl-{uuid.uuid4().hex[:12]}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, json=event_body, params=params)
                if res.status_code == 401:
                    raise CalendarAuthException("Google access token invalid or expired.")
                if res.status_code == 429:
                    raise CalendarRateLimitException("Google Calendar rate limit exceeded.")
                res.raise_for_status()
                data = res.json()

                meeting_link = None
                conf_data = data.get("conferenceData", {})
                for entry_point in conf_data.get("entryPoints", []):
                    if entry_point.get("entryPointType") == "video":
                        meeting_link = entry_point.get("uri")
                        break

                return CalendarEventResult(
                    event_id=data.get("id"),
                    status=data.get("status", "confirmed"),
                    start_time=start_time,
                    end_time=end_time,
                    timezone=timezone_str,
                    title=data.get("summary", title),
                    meeting_link=meeting_link,
                    html_link=data.get("htmlLink"),
                    raw_response=data,
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise CalendarAuthException("Google access token invalid or expired.")
            raise CalendarProviderException(f"Failed to create Google event: {e.response.text}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error creating Google event: {str(e)}", is_transient=True)

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
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        encoded_cal_id = urllib.parse.quote(calendar_id or "primary")
        url = f"{self.CALENDAR_API_BASE}/calendars/{encoded_cal_id}/events/{event_id}"

        event_body: Dict[str, Any] = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": timezone_str,
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": timezone_str,
            },
            "attendees": [{"email": a.get("email"), "displayName": a.get("name")} for a in attendees if a.get("email")],
        }
        if location:
            event_body["location"] = location

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.patch(url, headers=headers, json=event_body)
                if res.status_code == 401:
                    raise CalendarAuthException("Google access token invalid or expired.")
                if res.status_code == 429:
                    raise CalendarRateLimitException("Google Calendar rate limit exceeded.")
                res.raise_for_status()
                data = res.json()

                existing_meeting = meeting_link
                conf_data = data.get("conferenceData", {})
                for entry_point in conf_data.get("entryPoints", []):
                    if entry_point.get("entryPointType") == "video":
                        existing_meeting = entry_point.get("uri")
                        break

                return CalendarEventResult(
                    event_id=data.get("id"),
                    status=data.get("status", "confirmed"),
                    start_time=start_time,
                    end_time=end_time,
                    timezone=timezone_str,
                    title=data.get("summary", title),
                    meeting_link=existing_meeting,
                    html_link=data.get("htmlLink"),
                    raw_response=data,
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise CalendarAuthException("Google access token invalid or expired.")
            raise CalendarProviderException(f"Failed to update Google event: {e.response.text}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error updating Google event: {str(e)}", is_transient=True)

    def cancel_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
    ) -> bool:
        headers = {"Authorization": f"Bearer {access_token}"}
        encoded_cal_id = urllib.parse.quote(calendar_id or "primary")
        url = f"{self.CALENDAR_API_BASE}/calendars/{encoded_cal_id}/events/{event_id}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.delete(url, headers=headers)
                if res.status_code in (200, 204, 404, 410):
                    return True
                if res.status_code == 401:
                    raise CalendarAuthException("Google access token invalid or expired.")
                if res.status_code == 429:
                    raise CalendarRateLimitException("Google Calendar rate limit exceeded.")
                res.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 410):
                return True
            raise CalendarProviderException(f"Failed to cancel Google event: {str(e)}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error cancelling Google event: {str(e)}", is_transient=True)

    def get_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
    ) -> Optional[CalendarEventResult]:
        headers = {"Authorization": f"Bearer {access_token}"}
        encoded_cal_id = urllib.parse.quote(calendar_id or "primary")
        url = f"{self.CALENDAR_API_BASE}/calendars/{encoded_cal_id}/events/{event_id}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=headers)
                if res.status_code in (404, 410):
                    return None
                if res.status_code == 401:
                    raise CalendarAuthException("Google access token invalid or expired.")
                res.raise_for_status()
                data = res.json()

                meeting_link = None
                conf_data = data.get("conferenceData", {})
                for entry_point in conf_data.get("entryPoints", []):
                    if entry_point.get("entryPointType") == "video":
                        meeting_link = entry_point.get("uri")
                        break

                start_raw = data.get("start", {}).get("dateTime")
                end_raw = data.get("end", {}).get("dateTime")
                st = datetime.fromisoformat(start_raw) if start_raw else datetime.now()
                et = datetime.fromisoformat(end_raw) if end_raw else datetime.now()

                return CalendarEventResult(
                    event_id=data.get("id"),
                    status=data.get("status", "confirmed"),
                    start_time=st,
                    end_time=et,
                    timezone=data.get("start", {}).get("timeZone", "UTC"),
                    title=data.get("summary", ""),
                    meeting_link=meeting_link,
                    html_link=data.get("htmlLink"),
                    raw_response=data,
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 410):
                return None
            raise CalendarProviderException(f"Failed to get Google event: {str(e)}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error fetching Google event: {str(e)}", is_transient=True)
