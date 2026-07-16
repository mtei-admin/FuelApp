"""Session timeout and workday expiry policy."""
import os
from datetime import datetime, timedelta
from typing import Optional

SESSION_IDLE_MINUTES = int(os.environ.get("SESSION_IDLE_MINUTES", "60"))
WORKDAY_END_HOUR = int(os.environ.get("WORKDAY_END_HOUR", "18"))
WORKDAY_END_MINUTE = int(os.environ.get("WORKDAY_END_MINUTE", "0"))

_TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"


def workday_session_expires_at(now: Optional[datetime] = None) -> str:
    """
    Return session expiry at the end of the current workday.

    If login is after today's workday end, expiry is the next calendar day's
    workday end.

    Args:
        now: Reference time (defaults to local now).

    Returns:
        Timestamp string YYYY-MM-DD HH:MM:SS.
    """
    current = now or datetime.now()
    end = current.replace(
        hour=WORKDAY_END_HOUR,
        minute=WORKDAY_END_MINUTE,
        second=0,
        microsecond=0,
    )
    if current >= end:
        end = end + timedelta(days=1)
    return end.strftime(_TIMESTAMP_FMT)


def seconds_until_timestamp(timestamp: str) -> int:
    """Seconds from now until timestamp; minimum 60 for cookie max_age."""
    try:
        target = datetime.strptime(timestamp, _TIMESTAMP_FMT)
    except ValueError:
        return 3600
    delta = target - datetime.now()
    return max(int(delta.total_seconds()), 60)


def is_session_idle_expired(
    last_seen_at: Optional[str],
    idle_minutes: int = SESSION_IDLE_MINUTES,
) -> bool:
    """
    Return True when last activity exceeds the idle limit.

    Args:
        last_seen_at: Last API activity timestamp.
        idle_minutes: Inactivity limit in minutes.

    Returns:
        True if the session should be invalidated for idleness.
    """
    if not last_seen_at:
        return True
    try:
        seen_at = datetime.strptime(last_seen_at, _TIMESTAMP_FMT)
    except ValueError:
        return True
    return datetime.now() - seen_at > timedelta(minutes=idle_minutes)
