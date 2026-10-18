import zoneinfo
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, status

DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_ZONEINFO = zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)
UTC_ZONEINFO = timezone.utc


def validate_timezone(tz_name: Optional[str]) -> zoneinfo.ZoneInfo:
    """Validate and return a zoneinfo.ZoneInfo object.
    Defaults to Asia/Kolkata if None or empty.
    Raises HTTP 400 for invalid IANA timezone identifiers.
    """
    if not tz_name or not tz_name.strip():
        return DEFAULT_ZONEINFO

    trimmed = tz_name.strip()
    try:
        return zoneinfo.ZoneInfo(trimmed)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid IANA timezone identifier: '{tz_name}'. "
                "HireLens AI defaults to 'Asia/Kolkata'. Examples: 'Asia/Kolkata', 'UTC', 'America/New_York'."
            ),
        )


def parse_and_normalize_to_utc(
    dt: datetime,
    tz_name: Optional[str] = None,
) -> datetime:
    """Centralized datetime normalizer for HireLens AI.

    Rules:
    1. If `dt` already has timezone information (e.g. +05:30 or Z), it is converted to UTC.
    2. If `dt` is naive, it is interpreted as local time in `tz_name` (defaulting to Asia/Kolkata),
       then converted to UTC.
    3. Guarantees that internal storage is always UTC timezone-aware.

    Example:
        dt = 2026-10-20 14:00:00 (naive)
        tz_name = 'Asia/Kolkata' (+05:30)
        output = 2026-10-20 08:30:00+00:00 (UTC)
    """
    if dt is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Timestamp cannot be null.",
        )

    tz = validate_timezone(tz_name)

    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        # Datetime already has an explicit offset or is UTC
        return dt.astimezone(UTC_ZONEINFO)

    # Naive datetime: interpret in specified timezone (default Asia/Kolkata)
    # Using fold=0 for DST transitions
    dt_with_fold = dt.replace(fold=0) if hasattr(dt, "replace") else dt
    localized = dt_with_fold.replace(tzinfo=tz)
    return localized.astimezone(UTC_ZONEINFO)


def convert_utc_to_timezone(
    dt: datetime,
    tz_name: Optional[str] = None,
) -> datetime:
    """Convert a UTC or timezone-aware datetime to the target timezone (defaults to Asia/Kolkata)."""
    if dt is None:
        return None

    tz = validate_timezone(tz_name)

    if dt.tzinfo is None:
        # Assume UTC if stored without offset
        dt = dt.replace(tzinfo=UTC_ZONEINFO)

    return dt.astimezone(tz)


def get_kolkata_day_bounds(dt: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """Calculate the start and end of a calendar day in Asia/Kolkata, returned in UTC.

    In Asia/Kolkata (UTC+05:30):
    Start of Day: 00:00:00 IST -> 18:30:00 UTC (previous calendar day)
    End of Day:   23:59:59.999999 IST -> 18:29:59.999999 UTC (current calendar day)

    This ensures that dashboard metrics and 'Today' interview queries strictly
    respect Indian Standard Time calendar days.
    """
    if dt is None:
        dt = datetime.now(UTC_ZONEINFO)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_ZONEINFO)

    # Convert to Kolkata local time
    kolkata_dt = dt.astimezone(DEFAULT_ZONEINFO)

    start_local = kolkata_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = kolkata_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    start_utc = start_local.astimezone(UTC_ZONEINFO)
    end_utc = end_local.astimezone(UTC_ZONEINFO)

    return start_utc, end_utc


def format_ist(dt: datetime, include_seconds: bool = False) -> str:
    """Format a datetime in Indian Standard Time (IST).
    Example: '20 Oct 2026, 02:00 PM IST'
    """
    if dt is None:
        return ""

    ist_dt = convert_utc_to_timezone(dt, DEFAULT_TIMEZONE)
    fmt = "%d %b %Y, %I:%M:%S %p IST" if include_seconds else "%d %b %Y, %I:%M %p IST"
    return ist_dt.strftime(fmt)
