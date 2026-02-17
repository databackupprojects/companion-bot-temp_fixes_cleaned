# backend/models/models.py - Create this file
"""
Pydantic models for request/response validation - FIXED VERSION
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

# ==========================================
# ENUMS
# ==========================================

class Archetype(str, Enum):
    GOLDEN_RETRIEVER = "golden_retriever"
    TSUNDERE = "tsundere"
    LAWYER = "lawyer"
    COOL_GIRL = "cool_girl"
    TOXIC_EX = "toxic_ex"

class Gender(str, Enum):
    FEMALE = "female"
    MALE = "male"
    NONBINARY = "nonbinary"

class AttachmentStyle(str, Enum):
    SECURE = "secure"
    ANXIOUS = "anxious"
    AVOIDANT = "avoidant"

class Flirtiness(str, Enum):
    NONE = "none"
    SUBTLE = "subtle"
    FLIRTY = "flirty"

class Toxicity(str, Enum):
    HEALTHY = "healthy"
    MILD = "mild"
    TOXIC_LIGHT = "toxic_light"

class Tier(str, Enum):
    FREE = "free"
    PLUS = "plus"
    PREMIUM = "premium"

class MessageRole(str, Enum):
    USER = "user"
    BOT = "bot"

class MessageType(str, Enum):
    REACTIVE = "reactive"
    PROACTIVE = "proactive"

class BoundaryType(str, Enum):
    TOPIC = "topic"
    BEHAVIOR = "behavior"
    TIMING = "timing"
    FREQUENCY = "frequency"

class Mood(str, Enum):
    HAPPY = "happy"
    EXCITED = "excited"
    NEUTRAL = "neutral"
    TIRED = "tired"
    STRESSED = "stressed"
    SAD = "sad"
    ANXIOUS = "anxious"
    ANNOYED = "annoyed"
    ANGRY = "angry"
    LONELY = "lonely"
    BORED = "bored"

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

# ==========================================
# USER MODELS
# ==========================================

class UserBase(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    tier: Tier = Tier.FREE

class UserCreate(UserBase):
    password: Optional[str] = None
    telegram_id: Optional[int] = None
    timezone: Optional[str] = "UTC"  # ADDED THIS FIELD

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    tier: Optional[Tier] = None
    timezone: Optional[str] = None
    spice_consent: Optional[bool] = None

class UserResponse(UserBase):
    id: uuid.UUID
    telegram_id: Optional[int] = None
    messages_today: int = 0
    proactive_count_today: int = 0
    last_active_at: Optional[datetime] = None
    timezone: str = "UTC"
    spice_consent: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ==========================================
# BOT SETTINGS MODELS
# ==========================================
# BOT SETTINGS MODELS
# ==========================================

class BotSettingsBase(BaseModel):
    bot_name: str = "Dot"
    bot_gender: Gender = Gender.FEMALE
    archetype: Archetype = Archetype.GOLDEN_RETRIEVER
    attachment_style: AttachmentStyle = AttachmentStyle.SECURE
    flirtiness: Flirtiness = Flirtiness.SUBTLE
    toxicity: Toxicity = Toxicity.HEALTHY
    advanced_settings: Dict[str, Any] = Field(default_factory=dict)

class BotSettingsCreate(BotSettingsBase):
    pass

class BotSettingsUpdate(BaseModel):
    bot_name: Optional[str] = None
    bot_gender: Optional[Gender] = None
    # archetype cannot be changed once created
    attachment_style: Optional[AttachmentStyle] = None
    flirtiness: Optional[Flirtiness] = None
    toxicity: Optional[Toxicity] = None
    advanced_settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None

class BotSettingsResponse(BotSettingsBase):
    id: uuid.UUID
    user_id: uuid.UUID
    tone_summary: Optional[str] = None
    is_active: bool = True
    is_primary: bool = False
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class BotListResponse(BaseModel):
    """Response model for listing all user's bots."""
    bots: List[BotSettingsResponse]
    total: int
    primary_bot_id: Optional[uuid.UUID] = None

# ==========================================
# TIER SETTINGS MODELS
# ==========================================

class TierSettingsBase(BaseModel):
    tier_name: str
    max_bots: int = 1
    max_messages_per_day: int = 20
    max_proactive_per_day: int = 1
    features: Dict[str, Any] = Field(default_factory=dict)

class TierSettingsCreate(TierSettingsBase):
    pass

class TierSettingsUpdate(BaseModel):
    max_bots: Optional[int] = None
    max_messages_per_day: Optional[int] = None
    max_proactive_per_day: Optional[int] = None
    features: Optional[Dict[str, Any]] = None

class TierSettingsResponse(TierSettingsBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ==========================================
# QUIZ MODELS
# ==========================================

class QuizData(BaseModel):
    user_name: str
    timezone: Optional[str] = "UTC"
    bot_gender: Gender
    archetype: Archetype
    bot_name: str
    attachment_style: AttachmentStyle
    flirtiness: Flirtiness
    toxicity: Toxicity
    spice_consent: bool = False
    spice_consent_at: Optional[datetime] = None
    
    @validator('spice_consent')
    def validate_spice_consent(cls, v, values):
        if values.get('toxicity') == Toxicity.TOXIC_LIGHT and not v:
            raise ValueError('spice_consent is required for toxic_light toxicity')
        return v

class QuizResponse(BaseModel):
    token: str
    deep_link: str
    bot_name: str
    archetype: str
    first_message: str
    expires_at: datetime

# ==========================================
# MESSAGE MODELS
# ==========================================

class MessageCreate(BaseModel):
    content: str
    message_type: MessageType = MessageType.REACTIVE

class MessageSend(BaseModel):
    message: str
    persona: Optional[str] = None
    bot_id: Optional[uuid.UUID] = None  # Specify which bot to chat with

class MessageResponse(BaseModel):
    id: uuid.UUID
    role: MessageRole
    content: str
    message_type: MessageType
    detected_mood: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
    page: int
    page_size: int

# ==========================================
# BOUNDARY MODELS
# ==========================================

class BoundaryCreate(BaseModel):
    boundary_type: BoundaryType
    boundary_value: str
    active: bool = True

class BoundaryResponse(BaseModel):
    id: uuid.UUID
    boundary_type: str
    boundary_value: str
    active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==========================================
# ANALYTICS MODELS
# ==========================================

class AnalyticsEventCreate(BaseModel):
    event_name: str
    properties: Dict[str, Any] = Field(default_factory=dict)

# ==========================================
# PROACTIVE MODELS
# ==========================================

class ProactiveRequest(BaseModel):
    message_type: str  # 'morning', 'random', 'evening'
    force: bool = False

# ==========================================
# AUTH MODELS
# ==========================================

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: Optional[Any] = None  # Can be UUID or string
    role: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    tier: Optional[str] = None
    expires_in: Optional[int] = None

class TokenData(BaseModel):
    user_id: Optional[uuid.UUID] = None

class LoginRequest(BaseModel):
    email: Optional[str] = None
    telegram_id: Optional[int] = None
    password: Optional[str] = None

# ==========================================
# SYSTEM MODELS
# ==========================================

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    service: str

class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)