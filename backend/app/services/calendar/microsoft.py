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


class MicrosoftOutlookProvider(BaseCalendarProvider):
    """Microsoft Outlook Calendar Provider using Microsoft Graph v1.0 REST API."""

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.client_id = client_id or settings.MICROSOFT_CLIENT_ID
        self.client_secret = client_secret or settings.MICROSOFT_CLIENT_SECRET
        self.tenant_id = tenant_id or settings.MICROSOFT_TENANT_ID or "common"
        self.timeout = timeout

    @property
    def auth_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"

    @property
    def token_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id or "",
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(settings.MICROSOFT_CALENDAR_SCOPES),
            "state": state,
        }
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(self.token_url, data=data)
                if res.status_code in (400, 401):
                    raise CalendarAuthException(f"Microsoft token exchange failed: {res.text}")
                res.raise_for_status()
                token_data = res.json()

                access_token = token_data.get("access_token")
                account_id = None
                account_email = None
                if access_token:
                    headers = {"Authorization": f"Bearer {access_token}"}
                    me_res = client.get(f"{self.GRAPH_BASE}/me", headers=headers)
                    if me_res.status_code == 200:
                        profile = me_res.json()
                        account_id = profile.get("id")
                        account_email = profile.get("mail") or profile.get("userPrincipalName")

                return {
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in", 3600),
                    "account_id": account_id,
                    "account_email": account_email,
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (400, 401):
                raise CalendarAuthException(f"Microsoft token exchange rejected: {e.response.text}")
            raise CalendarProviderException(f"Microsoft Graph error: {str(e)}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error contacting Microsoft: {str(e)}", is_transient=True)

    def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(self.token_url, data=data)
                if res.status_code in (400, 401):
                    raise CalendarAuthException(f"Microsoft token refresh rejected: {res.text}")
                res.raise_for_status()
                token_data = res.json()
                return {
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token") or refresh_token,
                    "expires_in": token_data.get("expires_in", 3600),
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (400, 401):
                raise CalendarAuthException(f"Microsoft refresh token invalid or revoked: {e.response.text}")
            raise CalendarProviderException(f"Microsoft token refresh error: {str(e)}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error refreshing Microsoft token: {str(e)}", is_transient=True)

    def list_calendars(self, access_token: str) -> List[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{self.GRAPH_BASE}/me/calendars"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 401:
                    raise CalendarAuthException("Microsoft access token invalid or expired.")
                if res.status_code == 429:
                    raise CalendarRateLimitException("Microsoft Graph rate limit exceeded.")
                res.raise_for_status()
                items = res.json().get("value", [])
                calendars = []
                for item in items:
                    calendars.append({
                        "id": item.get("id"),
                        "name": item.get("name", "Outlook Calendar"),
                        "primary": item.get("isDefaultCalendar", False),
                        "read_only": not item.get("canEdit", True),
                    })
                return calendars
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise CalendarAuthException("Microsoft access token invalid or expired.")
            raise CalendarProviderException(f"Failed to list Microsoft calendars: {str(e)}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error listing Microsoft calendars: {str(e)}", is_transient=True)

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
        if calendar_id and calendar_id != "primary":
            url = f"{self.GRAPH_BASE}/me/calendars/{calendar_id}/events"
        else:
            url = f"{self.GRAPH_BASE}/me/events"

        event_body: Dict[str, Any] = {
            "subject": title,
            "body": {
                "contentType": "HTML",
                "content": description,
            },
            "start": {
                "dateTime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": timezone_str,
            },
            "end": {
                "dateTime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": timezone_str,
            },
            "attendees": [
                {
                    "emailAddress": {"address": a.get("email"), "name": a.get("name")},
                    "type": "required",
                }
                for a in attendees if a.get("email")
            ],
        }
        if location:
            event_body["location"] = {"displayName": location}

        if generate_meeting:
            event_body["isOnlineMeeting"] = True
            event_body["onlineMeetingProvider"] = "teamsForBusiness"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, json=event_body)
                if res.status_code == 401:
                    raise CalendarAuthException("Microsoft access token invalid or expired.")
                if res.status_code == 429:
                    raise CalendarRateLimitException("Microsoft Graph rate limit exceeded.")
                res.raise_for_status()
                data = res.json()

                meeting_link = None
                online_meeting = data.get("onlineMeeting")
                if online_meeting:
                    meeting_link = online_meeting.get("joinUrl")

                return CalendarEventResult(
                    event_id=data.get("id"),
                    status="confirmed",
                    start_time=start_time,
                    end_time=end_time,
                    timezone=timezone_str,
                    title=data.get("subject", title),
                    meeting_link=meeting_link,
                    html_link=data.get("webLink"),
                    raw_response=data,
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise CalendarAuthException("Microsoft access token invalid or expired.")
            raise CalendarProviderException(f"Failed to create Microsoft event: {e.response.text}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error creating Microsoft event: {str(e)}", is_transient=True)

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
        url = f"{self.GRAPH_BASE}/me/events/{event_id}"

        event_body: Dict[str, Any] = {
            "subject": title,
            "body": {
                "contentType": "HTML",
                "content": description,
            },
            "start": {
                "dateTime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": timezone_str,
            },
            "end": {
                "dateTime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": timezone_str,
            },
            "attendees": [
                {
                    "emailAddress": {"address": a.get("email"), "name": a.get("name")},
                    "type": "required",
                }
                for a in attendees if a.get("email")
            ],
        }
        if location:
            event_body["location"] = {"displayName": location}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.patch(url, headers=headers, json=event_body)
                if res.status_code == 401:
                    raise CalendarAuthException("Microsoft access token invalid or expired.")
                if res.status_code == 429:
                    raise CalendarRateLimitException("Microsoft Graph rate limit exceeded.")
                res.raise_for_status()
                data = res.json()

                existing_meeting = meeting_link
                online_meeting = data.get("onlineMeeting")
                if online_meeting and online_meeting.get("joinUrl"):
                    existing_meeting = online_meeting.get("joinUrl")

                return CalendarEventResult(
                    event_id=data.get("id"),
                    status="confirmed",
                    start_time=start_time,
                    end_time=end_time,
                    timezone=timezone_str,
                    title=data.get("subject", title),
                    meeting_link=existing_meeting,
                    html_link=data.get("webLink"),
                    raw_response=data,
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise CalendarAuthException("Microsoft access token invalid or expired.")
            raise CalendarProviderException(f"Failed to update Microsoft event: {e.response.text}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error updating Microsoft event: {str(e)}", is_transient=True)

    def cancel_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
    ) -> bool:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{self.GRAPH_BASE}/me/events/{event_id}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.delete(url, headers=headers)
                if res.status_code in (200, 204, 404):
                    return True
                if res.status_code == 401:
                    raise CalendarAuthException("Microsoft access token invalid or expired.")
                if res.status_code == 429:
                    raise CalendarRateLimitException("Microsoft Graph rate limit exceeded.")
                res.raise_for_status()
                return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return True
            raise CalendarProviderException(f"Failed to cancel Microsoft event: {str(e)}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error cancelling Microsoft event: {str(e)}", is_transient=True)

    def get_event(
        self,
        access_token: str,
        calendar_id: str,
        event_id: str,
    ) -> Optional[CalendarEventResult]:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{self.GRAPH_BASE}/me/events/{event_id}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 404:
                    return None
                if res.status_code == 401:
                    raise CalendarAuthException("Microsoft access token invalid or expired.")
                res.raise_for_status()
                data = res.json()

                meeting_link = None
                online_meeting = data.get("onlineMeeting")
                if online_meeting:
                    meeting_link = online_meeting.get("joinUrl")

                start_raw = data.get("start", {}).get("dateTime")
                end_raw = data.get("end", {}).get("dateTime")
                st = datetime.fromisoformat(start_raw) if start_raw else datetime.now()
                et = datetime.fromisoformat(end_raw) if end_raw else datetime.now()

                return CalendarEventResult(
                    event_id=data.get("id"),
                    status="confirmed",
                    start_time=st,
                    end_time=et,
                    timezone=data.get("start", {}).get("timeZone", "UTC"),
                    title=data.get("subject", ""),
                    meeting_link=meeting_link,
                    html_link=data.get("webLink"),
                    raw_response=data,
                )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise CalendarProviderException(f"Failed to get Microsoft event: {str(e)}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            raise CalendarProviderException(f"Network error fetching Microsoft event: {str(e)}", is_transient=True)
