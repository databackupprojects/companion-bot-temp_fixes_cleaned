# backend/utils/timezone.py
"""
Timezone utility functions for consistent UTC storage and timezone conversion.
All times are stored as UTC in the database.
Conversion to user timezone happens only for display/communication.
"""
from datetime import datetime, timedelta
import pytz
from typing import Optional


def get_utc_now() -> datetime:
    """Get current UTC time (naive datetime)."""
    return datetime.utcnow()


def get_utc_now_aware() -> datetime:
    """Get current UTC time (timezone-aware datetime)."""
    return datetime.now(pytz.UTC)


def to_user_timezone(utc_datetime: datetime, user_timezone: str = "UTC") -> datetime:
    """
    Convert UTC datetime to user's timezone.
    
    Args:
        utc_datetime: Datetime in UTC (can be naive or aware)
        user_timezone: User's timezone string (e.g., 'America/New_York')
        
    Returns:
        Datetime in user's timezone (timezone-aware)
    """
    try:
        tz = pytz.timezone(user_timezone)
        
        # If datetime is naive, assume it's UTC
        if utc_datetime.tzinfo is None:
            utc_aware = pytz.UTC.localize(utc_datetime)
        else:
            utc_aware = utc_datetime.astimezone(pytz.UTC) if utc_datetime.tzinfo != pytz.UTC else utc_datetime
        
        # Convert to user timezone
        return utc_aware.astimezone(tz)
    except (pytz.exceptions.UnknownTimeZoneError, AttributeError):
        # Fallback to UTC
        if utc_datetime.tzinfo is None:
            return pytz.UTC.localize(utc_datetime)
        return utc_datetime


def to_utc(local_datetime: datetime, user_timezone: str = "UTC") -> datetime:
    """
    Convert local datetime (in user's timezone) to UTC.
    
    Args:
        local_datetime: Datetime in user's timezone (naive)
        user_timezone: User's timezone string (e.g., 'America/New_York')
        
    Returns:
        Datetime in UTC (naive)
    """
    try:
        tz = pytz.timezone(user_timezone)
        
        # If datetime is naive, assume it's in the user's timezone
        if local_datetime.tzinfo is None:
            local_aware = tz.localize(local_datetime)
        else:
            local_aware = local_datetime.astimezone(tz) if local_datetime.tzinfo != tz else local_datetime
        
        # Convert to UTC and return as naive
        return local_aware.astimezone(pytz.UTC).replace(tzinfo=None)
    except (pytz.exceptions.UnknownTimeZoneError, AttributeError):
        # Fallback to UTC
        if local_datetime.tzinfo is None:
            return local_datetime
        return local_datetime.astimezone(pytz.UTC).replace(tzinfo=None)


def format_for_user(utc_datetime: datetime, user_timezone: str = "UTC", format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format UTC datetime for display to user in their timezone.
    
    Args:
        utc_datetime: Datetime in UTC
        user_timezone: User's timezone string
        format_str: Datetime format string
        
    Returns:
        Formatted datetime string in user's timezone
    """
    user_time = to_user_timezone(utc_datetime, user_timezone)
    return user_time.strftime(format_str)


def is_valid_timezone(timezone_str: str) -> bool:
    """Check if timezone string is valid."""
    try:
        pytz.timezone(timezone_str)
        return True
    except (pytz.exceptions.UnknownTimeZoneError, AttributeError):
        return False


def get_user_current_time(user_timezone: str = "UTC") -> datetime:
    """Get current time in user's timezone (timezone-aware)."""
    utc_now = get_utc_now_aware()
    return to_user_timezone(utc_now, user_timezone)


def time_until_reset(user_timezone: str = "UTC") -> timedelta:
    """Calculate time until next daily reset (midnight) in user's timezone."""
    user_now = get_user_current_time(user_timezone)
    tomorrow = user_now + timedelta(days=1)
    reset_time = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    return reset_time - user_now
