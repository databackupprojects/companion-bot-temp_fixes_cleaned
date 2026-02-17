# backend/utils/helpers.py
"""Simple helper functions"""
import random
import string
from datetime import datetime, timedelta
import pytz

def generate_token(length: int = 32) -> str:
    """Generate a random token."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length."""
    return text if len(text) <= max_length else text[:max_length-3] + "..."

def is_valid_timezone(timezone: str) -> bool:
    """Check if timezone is valid."""
    try:
        pytz.timezone(timezone)
        return True
    except:
        return False

def sanitize_message(content: str) -> str:
    """Sanitize message content."""
    return content.replace('\x00', '').strip()[:4000]
