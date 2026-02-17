# backend/models/enums.py
from enum import Enum

class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"

class ProactiveMessageType(str, Enum):
    MORNING = "morning"
    RANDOM = "random"
    EVENING = "evening"

class BlockReason(str, Enum):
    COOLDOWN_NOT_MET = "cooldown_not_met"
    DAILY_LIMIT_REACHED = "daily_limit_reached"
    PENDING_QUESTIONS = "pending_questions"
    SPACE_BOUNDARY_HARD_STOP = "space_boundary_hard_stop"
    LATE_NIGHT = "late_night"
    TIMING_BOUNDARY = "timing_boundary"
    ATTACHMENT_SKIPPED = "attachment_skipped"
    LLM_ERROR = "llm_error"
    LLM_NO_SEND = "llm_no_send"
    EMPTY_RESPONSE = "empty_response"
    BOUNDARY_VIOLATION = "boundary_violation"