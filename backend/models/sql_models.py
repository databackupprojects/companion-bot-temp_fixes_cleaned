# backend/models/sql_models.py
"""
SQLAlchemy ORM models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from database import Base
from sqlalchemy import Index
from enum import Enum as PyEnum

class UserRoleEnum(str, PyEnum):
    """User role enum."""
    ADMIN = "admin"
    USER = "user"

class User(Base):
    """User model."""
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True, index=True)
    username = Column(String(100), nullable=True)
    name = Column(String(100), nullable=True)  # User's name from quiz
    email = Column(String(255), unique=True, nullable=True)
    
    # Subscription
    tier = Column(String(20), default="free", index=True)
    tier_expires_at = Column(DateTime, nullable=True)
    
    # Limits
    messages_today = Column(Integer, default=0)
    proactive_count_today = Column(Integer, default=0)
    
    # Activity
    last_active_at = Column(DateTime, nullable=True)
    is_active_today = Column(Boolean, default=False)
    
    # Timezone
    timezone = Column(String(50), default="UTC")
    
    # Safety consent
    spice_consent = Column(Boolean, default=False)
    spice_consent_at = Column(DateTime, nullable=True)
    
    # Reset tracking
    last_daily_reset = Column(DateTime, nullable=True)
    
    # Web authentication
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    role = Column(String(20), default=UserRoleEnum.USER.value, nullable=False)
    
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    bot_settings = relationship("BotSettings", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    boundaries = relationship("UserBoundary", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")
    moods = relationship("MoodHistory", back_populates="user", cascade="all, delete-orphan")
    proactive_logs = relationship("ProactiveLog", back_populates="user", cascade="all, delete-orphan")
    schedules = relationship("UserSchedule", back_populates="user", cascade="all, delete-orphan", foreign_keys="UserSchedule.user_id")
    proactive_sessions = relationship("ProactiveSession", back_populates="user", cascade="all, delete-orphan")
    greeting_preference = relationship("GreetingPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")

class BotSettings(Base):
    """Bot settings model - supports multiple bots per user."""
    __tablename__ = "bot_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    # Configuration token (link back to quiz config)
    quiz_token = Column(String(32), nullable=True, unique=True, index=True)
    
    # Core variables
    bot_name = Column(String(50), default="Dot", index=True)
    bot_gender = Column(String(20), default="female")
    archetype = Column(String(50), default="golden_retriever", index=True)
    attachment_style = Column(String(20), default="secure")
    flirtiness = Column(String(20), default="subtle")
    toxicity = Column(String(20), default="healthy")
    tone_summary = Column(Text, nullable=True)
    
    # Advanced variables (JSONB)
    advanced_settings = Column(JSON, default=dict)
    
    # Bot status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="bot_settings")
    
    # Indexes
    __table_args__ = (
        Index('idx_bot_settings_user_active', user_id, is_active),
        Index('idx_bot_settings_user_primary', user_id, is_primary),
        {"extend_existing": True},
    )

class Message(Base):
    """Message model."""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bot_settings.id", ondelete="CASCADE"), nullable=True)
    role = Column(String(10), nullable=False)  # 'user' or 'bot'
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="reactive")  # 'reactive' or 'proactive'
    
    # Question tracking
    is_question = Column(Boolean, default=False)
    question_topic = Column(String(200), nullable=True)
    question_answered = Column(Boolean, default=False)
    
    # Mood
    detected_mood = Column(String(20), nullable=True)
    
    # Memory
    summarized = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", back_populates="messages")
    bot = relationship("BotSettings", foreign_keys=[bot_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_messages_user_created', user_id, created_at.desc()),
        Index('idx_messages_bot_created', bot_id, created_at.desc()),
        Index('idx_messages_unsummarized', user_id, summarized),
        {"extend_existing": True},
    )

class UserBoundary(Base):
    """User boundary model."""
    __tablename__ = "user_boundaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    boundary_type = Column(String(20), nullable=False)  # 'topic', 'behavior', 'timing', 'frequency'
    boundary_value = Column(String(200), nullable=False)
    active = Column(Boolean, default=True)
    
    # 24-hour hard stop tracking
    user_initiated_after = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="boundaries")
    
    # Indexes
    __table_args__ = (
        Index('idx_boundaries_user_active', user_id, active),
        {"extend_existing": True},
    )

class UserMemory(Base):
    """User memory model."""
    __tablename__ = "user_memory"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    category = Column(String(50), index=True)
    fact = Column(Text, nullable=False)
    importance = Column(Integer, default=1)  # 1-5 scale
    source_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="memories")
    
    # Indexes
    __table_args__ = (
        Index('idx_memory_user_importance', user_id, importance.desc()),
        Index('idx_memory_user_category', user_id, category),
        {"extend_existing": True},
    )

class MoodHistory(Base):
    """Mood history model."""
    __tablename__ = "mood_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    mood = Column(String(20), nullable=False)
    
    detected_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="moods")
    
    # Indexes
    __table_args__ = (
        Index('idx_mood_user_time', user_id, detected_at.desc()),
        {"extend_existing": True},
    )

class ProactiveLog(Base):
    """Proactive log model."""
    __tablename__ = "proactive_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    message_content = Column(Text)
    message_category = Column(String(50))  # e.g., 'morning_secure'
    
    sent_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="proactive_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_proactive_user_time', user_id, sent_at.desc()),
        {"extend_existing": True},
    )

# backend/models/sql_models.py - Add to QuizConfig class
class QuizConfig(Base):
    """Quiz configuration model."""
    __tablename__ = "quiz_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(32), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    config_data = Column(JSON, nullable=False)  # Make sure this is JSON type
    tone_summary = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    __table_args__ = {"extend_existing": True}

class SupportRequest(Base):
    """Support request model."""
    __tablename__ = "support_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    context = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    __table_args__ = {"extend_existing": True}

class AnalyticsEvent(Base):
    """Analytics event model."""
    __tablename__ = "analytics_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    event_name = Column(String(100), nullable=False, index=True)
    properties = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_analytics_user_event', user_id, event_name, created_at.desc()),
        {"extend_existing": True},
    )

class TierSettings(Base):
    """Tier configuration model for bot limits and features."""
    __tablename__ = "tier_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tier_name = Column(String(20), unique=True, nullable=False, index=True)  # 'free', 'plus', 'premium'
    max_bots = Column(Integer, default=1, nullable=False)
    max_messages_per_day = Column(Integer, default=20, nullable=False)
    max_proactive_per_day = Column(Integer, default=1, nullable=False)
    features = Column(JSON, default=dict)  # Additional features configuration
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    __table_args__ = {"extend_existing": True}


class UserSchedule(Base):
    """User schedule model - stores meetings, events, and important dates mentioned by user."""
    __tablename__ = "user_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bot_settings.id", ondelete="CASCADE"), nullable=True)
    
    # Schedule details
    event_name = Column(String(255), nullable=False)  # e.g., "Project Meeting", "Team Standup"
    description = Column(Text, nullable=True)  # Optional details about the event
    
    # Time information (stored in UTC, will be converted to user's timezone for display)
    start_time = Column(DateTime, nullable=False, index=True)  # When the event starts
    end_time = Column(DateTime, nullable=True)  # When the event ends (if provided)
    
    # Channel where it was discussed
    channel = Column(String(20), default="web")  # 'web' or 'telegram'
    
    # Proactive behavior tracking
    preparation_reminder_sent = Column(Boolean, default=False)  # Reminder before event
    preparation_reminder_sent_at = Column(DateTime, nullable=True)
    
    event_completed_sent = Column(Boolean, default=False)  # Message after event completed
    event_completed_sent_at = Column(DateTime, nullable=True)
    
    followup_sent = Column(Boolean, default=False)  # Followup on next interaction
    followup_sent_at = Column(DateTime, nullable=True)
    
    # Status tracking
    is_completed = Column(Boolean, default=False)  # Mark if user confirmed completion
    completed_at = Column(DateTime, nullable=True)
    
    # Message reference for context
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="schedules", foreign_keys=[user_id])
    bot = relationship("BotSettings", foreign_keys=[bot_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_schedule_user_start_time', user_id, start_time),
        Index('idx_schedule_status', user_id, is_completed),
        {"extend_existing": True},
    )


class ProactiveSession(Base):
    """Track proactive interactions to avoid repetition."""
    __tablename__ = "proactive_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bot_settings.id", ondelete="CASCADE"), nullable=True)
    
    # Session tracking
    session_type = Column(String(50), nullable=False, index=True)  # 'morning_greeting', 'meeting_prep', 'meeting_followup', etc.
    reference_id = Column(UUID(as_uuid=True), nullable=True)  # Links to related entity (e.g., UserSchedule.id)
    
    # Message tracking
    message_content = Column(Text, nullable=True)  # What was sent
    channel = Column(String(20), default="web")  # 'web' or 'telegram'
    
    # Status
    sent_at = Column(DateTime, default=func.now(), index=True)
    acknowledged_at = Column(DateTime, nullable=True)  # When user acknowledged
    
    # Metadata - note: Column name is 'metadata' in DB, but accessed as context_metadata in Python
    context_metadata = Column("metadata", JSON, default=dict)  # Store any additional context
    
    # Relationships
    user = relationship("User", back_populates="proactive_sessions")
    
    # Indexes
    __table_args__ = (
        Index('idx_proactive_session_user_type', user_id, session_type, sent_at.desc()),
        {"extend_existing": True},
    )


class GreetingPreference(Base):
    """Store user's greeting and communication preferences."""
    __tablename__ = "greeting_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    
    # Greeting preferences
    prefer_proactive = Column(Boolean, default=True)  # Does user want proactive messages?
    preferred_greeting_time = Column(String(20), default="morning")  # 'morning', 'afternoon', 'evening'
    
    # Do not disturb settings
    dnd_start_hour = Column(Integer, nullable=True)  # 0-23, e.g., 22 for 10 PM
    dnd_end_hour = Column(Integer, nullable=True)    # 0-23, e.g., 8 for 8 AM
    
    # Frequency preferences
    max_proactive_per_day = Column(Integer, default=3)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    __table_args__ = {"extend_existing": True}