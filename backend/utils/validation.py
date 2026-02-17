# backend/utils/validation.py
"""Simple validation functions"""
import re
from typing import Tuple, Optional
import pytz

def validate_email(email: str) -> bool:
    """Validate email format."""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))

def validate_password(password: str) -> Tuple[bool, Optional[str]]:
    """Validate password strength."""
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters"
    if len(password) > 100:
        return False, "Password too long"
    if not re.search(r'\d', password) or not re.search(r'[a-zA-Z]', password):
        return False, "Password must contain letters and numbers"
    return True, None

def validate_timezone(timezone: str) -> Tuple[bool, Optional[str]]:
    """Validate timezone."""
    try:
        pytz.timezone(timezone)
        return True, None
    except:
        return False, f"Invalid timezone: {timezone}"

    # Check for excessive newlines
    if content.count('\n') > 50:
        return False, "Message contains too many line breaks"
    
    return True, None

def validate_archetype(archetype: str) -> bool:
    """Validate archetype."""
    valid_archetypes = ['golden_retriever', 'tsundere', 'lawyer', 'cool_girl', 'toxic_ex']
    return archetype in valid_archetypes