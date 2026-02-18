# backend/services/meeting_extractor.py
"""
Service to extract meeting information from user messages using NLU.
Identifies mentions of meetings, events, and schedules in conversations.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class MeetingInfo:
    """Data class for extracted meeting information."""
    
    def __init__(
        self, 
        event_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None,
        confidence: float = 0.5
    ):
        self.event_name = event_name
        self.start_time = start_time
        self.end_time = end_time
        self.description = description
        self.confidence = confidence  # Confidence level 0-1


class MeetingExtractor:
    """
    Extracts meeting information from user messages.
    Uses pattern matching and NLU heuristics.
    """
    
    # Keywords that indicate meetings/events/schedules
    MEETING_KEYWORDS = {
        'meeting', 'call', 'standup', 'sync', 'conference', 'conference call',
        'video call', 'zoom', 'teams meeting', 'presentation', 'presentation',
        'appointment', 'event', 'schedule', 'interview', 'demo', 'walkthrough',
        'retrospective', 'planning', 'brainstorm', 'workshop', 'training',
        'webinar', 'session', 'announcement'
    }
    
    # Time-related keywords
    TIME_KEYWORDS = {
        'tomorrow', 'today', 'tonight', 'next week', 'next month',
        'in the morning', 'afternoon', 'evening', 'night',
        'at', 'on', 'by', 'before', 'after', 'until', 'around'
    }
    
    # Duration keywords
    DURATION_KEYWORDS = {
        'hour', 'hours', 'minute', 'minutes', 'hr', 'hrs', 'min', 'mins',
        'half', 'quarter', 'duration', 'lasting', 'lasts', 'takes'
    }
    
    def __init__(self):
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for meeting detection."""
        return {
            # Time patterns: HH:MM AM/PM or HH:MM (24-hour)
            'time_ampm': re.compile(r'\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)\b'),
            'time_24h': re.compile(r'\b(\d{1,2}):(\d{2})\b'),
            
            # Date patterns: DD/MM, MM/DD, or written dates
            'date_numeric': re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4}|\d{2})\b'),
            'date_written': re.compile(
                r'\b(January|February|March|April|May|June|July|August|September|October|November|December|'
                r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})(?:,?\s+(\d{4}))?\b',
                re.IGNORECASE
            ),
            
            # Duration patterns
            'duration': re.compile(
                r'(\d+(?:\.\d+)?)\s*(hour|hr|minute|min|half[\s-]?hour)\s*(?:and\s+(\d+)\s*(minute|min))?',
                re.IGNORECASE
            ),
            
            # Meeting mention patterns
            'meeting_mention': re.compile(
                r'(?:have|got|need|attending?|joining?)\s+(?:a\s+)?(\w+\s+)?(?:' +
                '|'.join(self.MEETING_KEYWORDS) + r')(?:\s+(?:at|on|with|tomorrow|today|next|in))?',
                re.IGNORECASE
            ),
        }
    
    def extract_meetings(self, message: str, reference_time: Optional[datetime] = None) -> List[MeetingInfo]:
        """
        Extract all meeting information from a message.
        
        Args:
            message: User's message
            reference_time: Current time for relative time calculation (defaults to now)
            
        Returns:
            List of MeetingInfo objects found in the message
        """
        if not message or not message.strip():
            return []
        
        reference_time = reference_time or datetime.utcnow()
        meetings = []
        
        # Check if message contains meeting-related keywords
        message_lower = message.lower()
        has_meeting_keyword = any(keyword in message_lower for keyword in self.MEETING_KEYWORDS)
        
        if not has_meeting_keyword:
            return []
        
        # Extract event name and time information
        event_name = self._extract_event_name(message)
        if not event_name:
            # If no specific event name found, create generic meeting mention
            event_name = "Meeting"
        
        # Extract times
        times = self._extract_times(message, reference_time)
        start_time = times.get('start_time')
        end_time = times.get('end_time')
        
        # Only create a meeting if we have at least a time
        if start_time or has_meeting_keyword:
            confidence = self._calculate_confidence(message, event_name, start_time, end_time)
            meeting = MeetingInfo(
                event_name=event_name,
                start_time=start_time,
                end_time=end_time,
                description=message[:200],  # Store original message for context
                confidence=confidence
            )
            meetings.append(meeting)
        
        return meetings
    
    def _extract_event_name(self, message: str) -> Optional[str]:
        """Extract the meeting/event name from the message."""
        message_lower = message.lower()
        
        # Look for patterns like "meeting with [name]", "standup for [project]"
        patterns = [
            r'(?:meeting|call|sync|standup)\s+(?:with|for|about)\s+(\w+(?:\s+\w+)*)',
            r'(?:meet|call)\s+(\w+(?:\s+\w+)*)',
            r'(?:have|attend)\s+(?:a\s+)?(\w+\s+(?:meeting|call|sync))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                return match.group(1).title()
        
        # Extract based on MEETING_KEYWORDS
        for keyword in sorted(self.MEETING_KEYWORDS, key=len, reverse=True):  # Longer first
            if keyword in message_lower:
                return keyword.title()
        
        return None
    
    def _extract_times(self, message: str, reference_time: datetime) -> Dict[str, Optional[datetime]]:
        """Extract start and end times from the message."""
        result = {'start_time': None, 'end_time': None}
        
        # Try to find specific times (HH:MM format)
        times = self._find_time_mentions(message, reference_time)
        
        if times:
            result['start_time'] = times[0] if times else None
            result['end_time'] = times[1] if len(times) > 1 else None
        
        # Try to extract relative times (tomorrow, next week, etc.)
        if not result['start_time']:
            relative_time = self._parse_relative_time(message, reference_time)
            if relative_time:
                result['start_time'] = relative_time
        
        return result
    
    def _find_time_mentions(self, message: str, reference_time: datetime) -> List[datetime]:
        """Find all time mentions in the message."""
        times = []
        
        # Look for AM/PM times
        for match in self.patterns['time_ampm'].finditer(message):
            hour = int(match.group(1))
            minute = int(match.group(2))
            am_pm = match.group(3).lower()
            
            if am_pm in ('pm', 'p.m.') and hour != 12:
                hour += 12
            elif am_pm in ('am', 'a.m.') and hour == 12:
                hour = 0
            
            time_obj = reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time is in the past today, assume it's tomorrow
            if time_obj < reference_time:
                time_obj += timedelta(days=1)
            
            times.append(time_obj)
        
        # Look for 24-hour times
        for match in self.patterns['time_24h'].finditer(message):
            hour = int(match.group(1))
            minute = int(match.group(2))
            
            time_obj = reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if time_obj < reference_time:
                time_obj += timedelta(days=1)
            
            times.append(time_obj)
        
        return times
    
    def _parse_relative_time(self, message: str, reference_time: datetime) -> Optional[datetime]:
        """Parse relative time expressions like 'tomorrow', 'next week', etc."""
        message_lower = message.lower()
        
        # Tomorrow
        if 'tomorrow' in message_lower:
            return reference_time + timedelta(days=1)
        
        # Today
        if 'today' in message_lower:
            return reference_time
        
        # Tonight
        if 'tonight' in message_lower:
            tonight = reference_time + timedelta(days=1)
            tonight = tonight.replace(hour=20, minute=0, second=0)  # Default 8 PM
            return tonight
        
        # Next week
        if 'next week' in message_lower:
            days_until_monday = (7 - reference_time.weekday()) % 7 or 7
            return reference_time + timedelta(days=days_until_monday)
        
        # Next [day name]
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day in enumerate(day_names):
            if day in message_lower:
                target_day = i
                current_day = reference_time.weekday()
                days_ahead = (target_day - current_day) % 7
                if days_ahead == 0:
                    days_ahead = 7
                return reference_time + timedelta(days=days_ahead)
        
        return None
    
    def _calculate_confidence(
        self,
        message: str,
        event_name: str,
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> float:
        """Calculate confidence level of the extraction."""
        confidence = 0.5
        
        # Has explicit event name
        if event_name and event_name != "Meeting":
            confidence += 0.2
        
        # Has start time
        if start_time:
            confidence += 0.2
        
        # Has end time
        if end_time:
            confidence += 0.1
        
        # Message explicitly mentions duration
        if self.patterns['duration'].search(message):
            confidence += 0.1
        
        # Cap at 1.0
        return min(confidence, 1.0)


class LLMMeetingExtractor:
    """
    Extracts meetings/events from messages using GPT-4.
    Falls back to regex-based MeetingExtractor on any failure.
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self._regex_fallback = MeetingExtractor()

    async def extract_meetings(
        self, message: str, reference_time: Optional[datetime] = None
    ) -> List[MeetingInfo]:
        """
        Extract meetings using GPT-4, falling back to regex on failure.
        """
        if not message or not message.strip():
            return []

        reference_time = reference_time or datetime.utcnow()

        try:
            return await self._extract_via_llm(message, reference_time)
        except Exception as e:
            logger.warning(
                "LLM meeting extraction failed, falling back to regex: %s", e
            )
            return self._regex_fallback.extract_meetings(message, reference_time)

    async def _extract_via_llm(
        self, message: str, reference_time: datetime
    ) -> List[MeetingInfo]:
        """Call GPT-4 to extract events as structured JSON."""
        ref_str = reference_time.strftime("%Y-%m-%d %H:%M (%A)")

        prompt = (
            "Extract any scheduled events, meetings, or appointments from the "
            "user message below. Return ONLY valid JSON in this exact format:\n"
            '{"events": [{"name": "...", "date": "YYYY-MM-DD", "time": "HH:MM", '
            '"end_time": "HH:MM", "description": "..."}]}\n'
            "Rules:\n"
            f"- Current date/time for the user is: {ref_str}\n"
            "- Resolve relative references (tomorrow, Friday, next week, etc.) "
            "to absolute dates.\n"
            '- If no events are found, return {"events": []}\n'
            "- end_time and description are optional (use null if unknown).\n"
            "- time should be in 24-hour format.\n\n"
            f"User message: {message}"
        )

        response = await self.llm_client.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        events = data.get("events", [])

        if not events:
            return []

        meetings: List[MeetingInfo] = []
        for evt in events:
            name = evt.get("name", "Event")
            date_str = evt.get("date")
            time_str = evt.get("time")
            end_time_str = evt.get("end_time")
            description = evt.get("description")

            start_time = None
            end_time = None

            if date_str and time_str:
                try:
                    start_time = datetime.strptime(
                        f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
                    )
                except ValueError:
                    pass

            if date_str and end_time_str:
                try:
                    end_time = datetime.strptime(
                        f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M"
                    )
                except ValueError:
                    pass

            meetings.append(
                MeetingInfo(
                    event_name=name,
                    start_time=start_time,
                    end_time=end_time,
                    description=description or message[:200],
                    confidence=0.9,
                )
            )

        return meetings
