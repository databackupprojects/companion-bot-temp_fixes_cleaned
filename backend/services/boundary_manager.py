# backend/services/boundary_manager.py
"""
Boundary detection and management
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from constants import SPACE_BOUNDARY_COOLDOWN_HOURS
from models.sql_models import UserBoundary
from models import BoundaryType

logger = logging.getLogger(__name__)


class BoundaryDetector:
    """Detects boundary requests in user messages."""
    
    # Topic-specific stop patterns
    STOP_PATTERNS = [
        (r"stop asking (?:me )?about (.+)", BoundaryType.TOPIC),
        (r"stop (?:talking|mentioning|bringing up) (?:about )?(.+)", BoundaryType.TOPIC),
        (r"don'?t (?:ask|mention|talk|bring up) (?:about )?(.+)", BoundaryType.TOPIC),
        (r"i don'?t (?:want|wanna|need) to (?:talk|hear|discuss) about (.+)", BoundaryType.TOPIC),
        (r"let'?s not (?:talk|discuss) (?:about )?(.+)", BoundaryType.TOPIC),
        (r"can we not (?:talk|discuss) (?:about )?(.+)", BoundaryType.TOPIC),
        (r"enough (?:about|with) (?:the )?(.+)", BoundaryType.TOPIC),
        (r"no more (.+) (?:talk|questions|stuff)", BoundaryType.TOPIC),
        (r"please (?:stop|don'?t) (?:asking|talking) (?:about )?(.+)", BoundaryType.TOPIC),
    ]
    
    # Space/reduce contact patterns — TRIGGERS 24-HOUR HARD STOP
    SPACE_PATTERNS = [
        (r"leave me alone", BoundaryType.BEHAVIOR),
        (r"stop messaging me", BoundaryType.BEHAVIOR),
        (r"stop texting me", BoundaryType.BEHAVIOR),
        (r"too many messages", BoundaryType.FREQUENCY),
        (r"give me (?:some )?space", BoundaryType.BEHAVIOR),
        (r"back off", BoundaryType.BEHAVIOR),
        (r"i need (?:some )?(?:space|time|a break)", BoundaryType.BEHAVIOR),
        (r"chill (?:out )?(?:with the messages)?", BoundaryType.FREQUENCY),
        (r"not (?:right )?now", BoundaryType.BEHAVIOR),
        (r"go away", BoundaryType.BEHAVIOR),
        (r"shut up", BoundaryType.BEHAVIOR),
    ]
    
    # Timing preference patterns
    TIMING_PATTERNS = [
        (r"no (?:more )?morning messages?", "no_morning_messages"),
        (r"don'?t message me (?:in the )?morning", "no_morning_messages"),
        (r"no messages? (?:at|after|late at) night", "no_late_messages"),
        (r"don'?t (?:text|message) me (?:so )?late", "no_late_messages"),
    ]
    
    # Retraction patterns
    SPACE_RETRACTION_PATTERNS = [
        r"(?:i'?m |im )?back",
        r"(?:i'?m |im )?here",
        r"(?:i'?m |im )?ready",
        r"(?:okay |ok )?(?:i'?m |im )?(?:good|fine|better) now",
        r"(?:never ?mind|nvm)",
        r"(?:i'?m |im )?sorry",
        r"miss(?:ed)? you",
        r"hey again",
    ]
    
    def detect_boundary(self, message: str) -> Optional[Tuple[BoundaryType, str]]:
        """
        Detect if message contains a boundary request.
        
        Returns:
            Tuple of (BoundaryType, boundary_value) or None
        """
        if not message:
            return None
        
        message_lower = message.lower().strip()
        
        # Check timing preferences first
        for pattern, timing_value in self.TIMING_PATTERNS:
            if re.search(pattern, message_lower):
                return (BoundaryType.TIMING, timing_value)
        
        # Check space/behavior requests (triggers 24-hour stop)
        for pattern, boundary_type in self.SPACE_PATTERNS:
            if re.search(pattern, message_lower):
                return (boundary_type, "reduce_messages")
        
        # Check topic-specific stops
        for pattern, boundary_type in self.STOP_PATTERNS:
            match = re.search(pattern, message_lower)
            if match:
                topic = self._clean_topic(match.group(1))
                if topic:
                    return (BoundaryType.TOPIC, topic)
        
        return None
    
    def detect_retraction(self, message: str) -> Optional[str]:
        """
        Detect if user is retracting a space boundary.
        
        Returns:
            "space" for space boundary retraction, or None
        """
        if not message:
            return None
        
        message_lower = message.lower().strip()
        
        for pattern in self.SPACE_RETRACTION_PATTERNS:
            if re.search(pattern, message_lower):
                return "space"
        
        return None
    
    def _clean_topic(self, topic: str) -> str:
        """Clean up extracted topic string."""
        if not topic:
            return ""
        
        topic = topic.strip().lower()
        
        # Remove common suffixes
        for suffix in [r"\s*anymore$", r"\s*please$", r"\s*!+$", r"\s*\.+$"]:
            topic = re.sub(suffix, "", topic)
        
        topic = topic.strip()
        
        # Skip too short or generic
        if len(topic) < 2 or topic in ["it", "that", "this", "them", "thing"]:
            return ""
        
        return topic
    
    def is_space_boundary(self, boundary_type: BoundaryType) -> bool:
        """Check if boundary type triggers 24-hour hard stop."""
        return boundary_type in [BoundaryType.BEHAVIOR, BoundaryType.FREQUENCY]


class BoundaryManager:
    """
    Manages user boundaries with 24-hour hard stop.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.detector = BoundaryDetector()
    
    async def process_message(
        self, 
        user_id: str, 
        message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process message for boundary requests and retractions.
        Also marks user_initiated_after for space boundaries.
        
        Returns:
            Dict with boundary information or None
        """
        
        # Mark user initiated (breaks the seal on space boundary)
        await self._mark_user_initiated(user_id)
        
        # Check for retractions first
        retracted = self.detector.detect_retraction(message)
        if retracted == "space":
            deactivated = await self._deactivate_space_boundary(user_id)
            if deactivated:
                return {
                    "action": "boundary_retracted",
                    "type": "behavior",
                    "value": "space",
                    "is_space_boundary": True,
                    "hint": "[BOUNDARY_RETRACTED: space]"
                }
        
        # Check for new boundaries
        result = self.detector.detect_boundary(message)
        if not result:
            return None
        
        boundary_type, boundary_value = result
        
        # Check if already exists
        existing = await self.db.execute(
            select(UserBoundary.id)
            .where(
                UserBoundary.user_id == user_id,
                UserBoundary.boundary_type == boundary_type.value,
                UserBoundary.boundary_value == boundary_value,
                UserBoundary.active == True
            )
        )
        
        if existing.scalar_one_or_none():
            return None
        
        # Save new boundary
        new_boundary = UserBoundary(
            user_id=user_id,
            boundary_type=boundary_type.value,
            boundary_value=boundary_value,
            active=True
        )
        
        self.db.add(new_boundary)
        await self.db.commit()
        
        logger.info(f"Boundary saved: {user_id} | {boundary_type.value}={boundary_value}")
        
        is_space = self.detector.is_space_boundary(boundary_type)
        
        return {
            "action": "boundary_set",
            "type": boundary_type.value,
            "value": boundary_value,
            "is_space_boundary": is_space,
            "hint": f"[BOUNDARY_SET: {boundary_type.value}={boundary_value}]"
        }
    
    async def _mark_user_initiated(self, user_id: str):
        """Mark user initiated after space boundary - FIXED."""
        from sqlalchemy import update
        from uuid import UUID
        
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        
        stmt = update(UserBoundary).where(
            UserBoundary.user_id == user_uuid,
            UserBoundary.boundary_type.in_(['behavior', 'frequency']),
            UserBoundary.boundary_value == 'reduce_messages',
            UserBoundary.active == True,
            UserBoundary.user_initiated_after == None
        ).values(user_initiated_after=datetime.utcnow())
        
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _deactivate_space_boundary(self, user_id: str) -> bool:
        """Deactivate space/frequency boundaries."""
        result = await self.db.execute(
            update(UserBoundary)
            .where(
                UserBoundary.user_id == user_id,
                UserBoundary.boundary_type.in_(['behavior', 'frequency']),
                UserBoundary.active == True
            )
            .values(active=False)
        )
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def check_space_allows_proactive(self, user_id: str) -> Tuple[bool, str]:
        """
        Check if space boundary allows proactive messages.
        
        24-HOUR HARD STOP LOGIC:
        - Boundary set, < 24 hours, user silent → BLOCK
        - Boundary set, < 24 hours, user initiated → ALLOW
        - Boundary set, > 24 hours → ALLOW
        - No boundary → ALLOW
        """
        result = await self.db.execute(
            select(UserBoundary.created_at, UserBoundary.user_initiated_after)
            .where(
                UserBoundary.user_id == user_id,
                UserBoundary.boundary_type.in_(['behavior', 'frequency']),
                UserBoundary.boundary_value == 'reduce_messages',
                UserBoundary.active == True
            )
            .order_by(UserBoundary.created_at.desc())
            .limit(1)
        )
        
        boundary = result.fetchone()
        
        if not boundary:
            return (True, "no_boundary")
        
        boundary_created, user_initiated_after = boundary
        
        # User broke the seal
        if user_initiated_after:
            return (True, "user_initiated")
        
        # Check if 24 hours passed
        hours_since = (datetime.utcnow() - boundary_created).total_seconds() / 3600
        
        if hours_since >= SPACE_BOUNDARY_COOLDOWN_HOURS:
            return (True, "cooldown_expired")
        
        # HARD STOP
        remaining = SPACE_BOUNDARY_COOLDOWN_HOURS - hours_since
        return (False, f"hard_stop_{remaining:.1f}h_remaining")
    
    async def check_message_violates(self, user_id: Union[str, UUID], message: str) -> Tuple[bool, Optional[str]]:
        """Check if a bot message would violate any topic boundary."""
        if not message:
            return (False, None)
        
        # Convert user_id to UUID if it's a string
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        
        result = await self.db.execute(
            select(UserBoundary.boundary_value)
            .where(
                UserBoundary.user_id == user_uuid,
                UserBoundary.active == True,
                UserBoundary.boundary_type == 'topic'
            )
        )
        
        boundaries = [row[0] for row in result.fetchall()]
        if not boundaries:
            return (False, None)
        
        message_lower = message.lower()
        for boundary_value in boundaries:
            boundary_lower = boundary_value.lower()
            # Use word boundary for short terms
            if len(boundary_lower) <= 4:
                if re.search(r'\b' + re.escape(boundary_lower) + r'\b', message_lower):
                    return (True, boundary_value)
            elif boundary_lower in message_lower:
                return (True, boundary_value)
        
        return (False, None)
    
    async def get_active_boundaries(self, user_id: Union[str, UUID]) -> List[str]:
        """Get all active boundaries for context."""
        # Convert user_id to UUID if it's a string
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        
        result = await self.db.execute(
            select(UserBoundary.boundary_type, UserBoundary.boundary_value)
            .where(
                UserBoundary.user_id == user_uuid,
                UserBoundary.active == True
            )
        )
        
        return [f"{row[0]}: {row[1]}" for row in result.fetchall()]
    
    async def get_timing_boundaries(self, user_id: str) -> List[str]:
        """Get timing-related boundaries."""
        result = await self.db.execute(
            select(UserBoundary.boundary_value)
            .where(
                UserBoundary.user_id == user_id,
                UserBoundary.boundary_type == 'timing',
                UserBoundary.active == True
            )
        )
        
        return [row[0] for row in result.fetchall()]
    
    async def create_boundary(
        self, 
        user_id: str, 
        boundary_type: str, 
        boundary_value: str
    ) -> bool:
        """Manually create a boundary."""
        try:
            # Check if already exists
            existing = await self.db.execute(
                select(UserBoundary.id)
                .where(
                    UserBoundary.user_id == user_id,
                    UserBoundary.boundary_type == boundary_type,
                    UserBoundary.boundary_value == boundary_value,
                    UserBoundary.active == True
                )
            )
            
            if existing.scalar_one_or_none():
                return False
            
            # Create new boundary
            boundary = UserBoundary(
                user_id=user_id,
                boundary_type=boundary_type,
                boundary_value=boundary_value,
                active=True
            )
            
            self.db.add(boundary)
            await self.db.commit()
            
            logger.info(f"Manual boundary created: {user_id} | {boundary_type}={boundary_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating boundary: {e}")
            await self.db.rollback()
            return False
    
    async def delete_boundary(self, user_id: str, boundary_id: str) -> bool:
        """Delete (deactivate) a boundary."""
        try:
            from uuid import UUID
            boundary_uuid = UUID(boundary_id)
            
            result = await self.db.execute(
                update(UserBoundary)
                .where(
                    UserBoundary.id == boundary_uuid,
                    UserBoundary.user_id == user_id
                )
                .values(active=False)
            )
            
            await self.db.commit()
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Error deleting boundary: {e}")
            await self.db.rollback()
            return False
    
    async def get_all_boundaries(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all boundaries for a user."""
        result = await self.db.execute(
            select(UserBoundary)
            .where(UserBoundary.user_id == user_id)
            .order_by(UserBoundary.created_at.desc())
        )
        
        boundaries = result.scalars().all()
        
        return [
            {
                "id": str(boundary.id),
                "boundary_type": boundary.boundary_type,
                "boundary_value": boundary.boundary_value,
                "active": boundary.active,
                "created_at": boundary.created_at,
                "user_initiated_after": boundary.user_initiated_after
            }
            for boundary in boundaries
        ]