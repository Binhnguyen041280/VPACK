"""
Timezone utilities for V_Track.
All datetime operations should use UTC internally.
Created: Phase 3 - Timezone & UTC-aware
"""

from datetime import datetime, timezone
from typing import Optional
import pytz

# Constants
UTC = pytz.UTC
DEFAULT_TIMEZONE = pytz.timezone('Asia/Ho_Chi_Minh')


def now_utc() -> datetime:
    """Get current time in UTC (timezone-aware)."""
    return datetime.now(UTC)


def now_local(tz_name: str = 'Asia/Ho_Chi_Minh') -> datetime:
    """Get current time in specified timezone."""
    tz = pytz.timezone(tz_name)
    return datetime.now(tz)


def to_utc(dt: datetime, source_tz: str = None) -> datetime:
    """
    Convert datetime to UTC.

    Args:
        dt: datetime to convert
        source_tz: source timezone name (e.g., 'Asia/Ho_Chi_Minh')
                   If None, assumes dt is already timezone-aware

    Returns:
        UTC datetime (timezone-aware)
    """
    if dt is None:
        return None

    # If naive datetime, localize it first
    if dt.tzinfo is None:
        if source_tz:
            tz = pytz.timezone(source_tz)
            dt = tz.localize(dt)
        else:
            # Assume UTC if no timezone specified
            dt = UTC.localize(dt)

    return dt.astimezone(UTC)


def from_utc(dt: datetime, target_tz: str = 'Asia/Ho_Chi_Minh') -> datetime:
    """
    Convert UTC datetime to target timezone.

    Args:
        dt: UTC datetime
        target_tz: target timezone name

    Returns:
        datetime in target timezone
    """
    if dt is None:
        return None

    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = UTC.localize(dt)

    tz = pytz.timezone(target_tz)
    return dt.astimezone(tz)


def parse_iso_utc(iso_string: str) -> Optional[datetime]:
    """
    Parse ISO format string to UTC datetime.

    Args:
        iso_string: ISO format string (e.g., '2024-01-15T10:30:00Z')

    Returns:
        UTC datetime (timezone-aware)
    """
    if not iso_string:
        return None

    try:
        # Handle different ISO formats
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'

        dt = datetime.fromisoformat(iso_string)

        # Ensure UTC
        if dt.tzinfo is None:
            dt = UTC.localize(dt)
        else:
            dt = dt.astimezone(UTC)

        return dt
    except Exception:
        return None


def to_iso_utc(dt: datetime) -> Optional[str]:
    """
    Convert datetime to ISO format string in UTC.

    Args:
        dt: datetime to convert

    Returns:
        ISO format string with Z suffix
    """
    if dt is None:
        return None

    utc_dt = to_utc(dt)
    return utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def format_local(dt: datetime, tz_name: str = 'Asia/Ho_Chi_Minh', fmt: str = '%d/%m/%Y %H:%M') -> str:
    """
    Format datetime for display in local timezone.

    Args:
        dt: datetime to format
        tz_name: target timezone
        fmt: strftime format

    Returns:
        Formatted string
    """
    if dt is None:
        return ''

    local_dt = from_utc(dt, tz_name)
    return local_dt.strftime(fmt)


def is_expired(expiry_dt: datetime) -> bool:
    """
    Check if datetime has expired (compared to now UTC).

    Args:
        expiry_dt: expiry datetime

    Returns:
        True if expired
    """
    if expiry_dt is None:
        return False

    utc_expiry = to_utc(expiry_dt)
    return now_utc() > utc_expiry


def from_firestore_timestamp(timestamp) -> Optional[datetime]:
    """
    Convert Firestore timestamp to UTC datetime.

    Args:
        timestamp: Firestore Timestamp object

    Returns:
        UTC datetime (timezone-aware)
    """
    if timestamp is None:
        return None

    if hasattr(timestamp, 'timestamp'):
        # Firestore Timestamp object
        return datetime.fromtimestamp(timestamp.timestamp(), tz=UTC)
    elif isinstance(timestamp, datetime):
        return to_utc(timestamp)
    elif isinstance(timestamp, str):
        return parse_iso_utc(timestamp)

    return None


def to_firestore_timestamp(dt: datetime) -> Optional[datetime]:
    """
    Convert datetime to Firestore-compatible format.

    For Cloud Functions using firebase_admin, return datetime directly.
    Firestore will handle the conversion.

    Args:
        dt: datetime to convert

    Returns:
        UTC datetime for Firestore
    """
    if dt is None:
        return None

    return to_utc(dt)


def days_until_expiry(expiry_dt: datetime) -> int:
    """
    Calculate days until expiry.

    Args:
        expiry_dt: expiry datetime

    Returns:
        Number of days until expiry (negative if expired)
    """
    if expiry_dt is None:
        return 999999  # Effectively never expires

    utc_expiry = to_utc(expiry_dt)
    delta = utc_expiry - now_utc()
    return delta.days


def days_since_expired(expiry_dt: datetime) -> int:
    """
    Calculate days since expired.

    Args:
        expiry_dt: expiry datetime

    Returns:
        Number of days since expiry (negative if not expired)
    """
    return -days_until_expiry(expiry_dt)


# Test utilities
if __name__ == "__main__":
    print("Testing timezone_utils...")

    # Test now_utc
    utc_now = now_utc()
    print(f"now_utc(): {utc_now}")
    assert utc_now.tzinfo is not None, "now_utc should return timezone-aware datetime"

    # Test to_utc
    naive_dt = datetime(2024, 1, 15, 10, 30, 0)
    utc_dt = to_utc(naive_dt)
    print(f"to_utc(naive): {utc_dt}")
    assert utc_dt.tzinfo is not None, "to_utc should return timezone-aware datetime"

    # Test to_iso_utc
    iso_str = to_iso_utc(utc_now)
    print(f"to_iso_utc(): {iso_str}")
    assert iso_str.endswith('Z'), "ISO string should end with Z"

    # Test parse_iso_utc
    parsed = parse_iso_utc(iso_str)
    print(f"parse_iso_utc(): {parsed}")
    assert parsed is not None, "parse_iso_utc should return datetime"

    # Test is_expired
    future = now_utc() + datetime.timedelta(days=1) if hasattr(datetime, 'timedelta') else datetime.now(UTC)
    from datetime import timedelta
    future = now_utc() + timedelta(days=1)
    past = now_utc() - timedelta(hours=1)
    print(f"is_expired(future): {is_expired(future)}")
    print(f"is_expired(past): {is_expired(past)}")

    print("All tests passed!")
