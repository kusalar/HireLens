from typing import Union, Optional
from app.core.config import settings
from app.models.enums import CalendarProviderType
from app.services.calendar.base import BaseCalendarProvider
from app.services.calendar.mock import MockCalendarProvider
from app.services.calendar.google import GoogleCalendarProvider
from app.services.calendar.microsoft import MicrosoftOutlookProvider

# Shared mock instance for test predictability
_default_mock_provider = MockCalendarProvider("mock")
_mock_providers = {
    "google": MockCalendarProvider("google"),
    "microsoft": MockCalendarProvider("microsoft"),
    "mock": _default_mock_provider,
}


def get_calendar_provider(
    provider_type: Union[CalendarProviderType, str],
    force_mock: Optional[bool] = None,
) -> BaseCalendarProvider:
    """
    Factory function returning the appropriate calendar adapter.
    Falls back to deterministic MockCalendarProvider if credentials are not configured or force_mock=True.
    """
    if isinstance(provider_type, CalendarProviderType):
        p_name = provider_type.value.lower()
    else:
        p_name = str(provider_type).lower()

    use_mock = force_mock
    if use_mock is None:
        use_mock = settings.USE_MOCK_CALENDAR_PROVIDER

    if p_name == "google":
        if use_mock or not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
            return _mock_providers["google"]
        return GoogleCalendarProvider()

    if p_name in ("microsoft", "outlook"):
        if use_mock or not (settings.MICROSOFT_CLIENT_ID and settings.MICROSOFT_CLIENT_SECRET):
            return _mock_providers["microsoft"]
        return MicrosoftOutlookProvider()

    return _mock_providers.get("mock", _default_mock_provider)


def get_mock_provider_instance(provider_name: str = "mock") -> MockCalendarProvider:
    """Retrieve internal mock instance for test assertions and fault injection."""
    return _mock_providers.get(provider_name.lower(), _default_mock_provider)
