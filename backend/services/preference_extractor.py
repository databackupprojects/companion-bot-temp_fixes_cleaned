# services/preference_extractor.py
# Extracts user preferences (DND hours, communication preferences) from chat using NLU

import logging
import json
import re
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class PreferenceExtractor:
    """
    Extracts user preferences from natural language using LLM.
    Focus: DND (Do Not Disturb) hours, sleep/wake times, availability.
    """
    
    # Keywords that might indicate time preference discussion
    TIME_PREFERENCE_KEYWORDS = [
        'sleep', 'wake', 'bed', 'morning', 'evening', 'night',
        'available', 'busy', 'work', 'message', 'disturb',
        'don\'t contact', 'don\'t message', 'free time',
        'usually wake', 'go to sleep', 'bedtime', 'wake up'
    ]
    
    def __init__(self, llm_client):
        """
        Initialize with LLM client for NLU.
        
        Args:
            llm_client: OpenAI LLM client instance
        """
        self.llm = llm_client
    
    def might_contain_time_preferences(self, message: str) -> bool:
        """
        Quick check if message might contain time preferences.
        Used to avoid unnecessary LLM calls.
        
        Args:
            message: User's message text
            
        Returns:
            True if message likely contains time preferences
        """
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.TIME_PREFERENCE_KEYWORDS)
    
    async def extract_dnd_preferences(self, message: str, user_timezone: str = "UTC") -> Optional[Dict[str, Any]]:
        """
        Extract DND (Do Not Disturb) hours from user message using LLM.
        
        Args:
            message: User's message text
            user_timezone: User's timezone for context
            
        Returns:
            Dict with extracted preferences or None:
            {
                "dnd_start_hour": 22,  # 10 PM (24-hour format, 0-23)
                "dnd_end_hour": 7,     # 7 AM
                "confidence": "high",   # high, medium, low
                "reasoning": "User mentioned sleeping at 10 PM and waking at 7 AM"
            }
        """
        # Quick filter
        if not self.might_contain_time_preferences(message):
            return None
        
        # Prepare prompt for LLM
        extraction_prompt = f"""You are analyzing a user message to extract their communication preferences, specifically Do Not Disturb (DND) hours.

User's message: "{message}"
User's timezone: {user_timezone}

Your task:
1. Determine if the message mentions sleep times, wake times, or when they DON'T want to be contacted
2. Extract DND hours in 24-hour format (0-23)
3. Return ONLY valid JSON

Rules:
- dnd_start_hour: Hour when DND should START (e.g., bedtime, "don't message after 10 PM" = 22)
- dnd_end_hour: Hour when DND should END (e.g., wake time, "I wake up at 7 AM" = 7)
- If only one time is mentioned, infer the other reasonably
- confidence: "high" if explicit times given, "medium" if inferred, "low" if ambiguous
- If NO time preferences found, return {{"found": false}}

Examples:
Message: "I usually sleep at 10 PM and wake up at 7 AM"
Response: {{"found": true, "dnd_start_hour": 22, "dnd_end_hour": 7, "confidence": "high", "reasoning": "Explicit sleep and wake times"}}

Message: "Don't message me after 11 PM"
Response: {{"found": true, "dnd_start_hour": 23, "dnd_end_hour": 7, "confidence": "medium", "reasoning": "Explicit DND start, assumed 7 AM wake"}}

Message: "I wake up at 6 AM"
Response: {{"found": true, "dnd_start_hour": 22, "dnd_end_hour": 6, "confidence": "medium", "reasoning": "Explicit wake time, assumed 10 PM sleep"}}

Message: "I'm available from 9 AM to 10 PM"
Response: {{"found": true, "dnd_start_hour": 22, "dnd_end_hour": 9, "confidence": "high", "reasoning": "Explicit availability window"}}

Message: "What's the weather today?"
Response: {{"found": false}}

Now analyze the user's message and return ONLY valid JSON:"""

        try:
            # Call LLM for extraction
            response = await self.llm.generate_response(
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=200
            )
            
            # Parse JSON response
            response_text = response.strip()
            
            # Try to extract JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            # Validate result
            if not result.get("found", False):
                return None
            
            # Validate hours are in valid range
            dnd_start = result.get("dnd_start_hour")
            dnd_end = result.get("dnd_end_hour")
            
            if dnd_start is not None and (dnd_start < 0 or dnd_start > 23):
                logger.warning(f"Invalid dnd_start_hour: {dnd_start}")
                return None
            
            if dnd_end is not None and (dnd_end < 0 or dnd_end > 23):
                logger.warning(f"Invalid dnd_end_hour: {dnd_end}")
                return None
            
            logger.info(
                f"✓ Extracted DND preferences: start={dnd_start}, end={dnd_end}, "
                f"confidence={result.get('confidence')}, reason={result.get('reasoning')}"
            )
            
            return {
                "dnd_start_hour": dnd_start,
                "dnd_end_hour": dnd_end,
                "confidence": result.get("confidence", "medium"),
                "reasoning": result.get("reasoning", "")
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}, response: {response_text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Error extracting DND preferences: {e}")
            return None
    
    async def extract_proactive_preference(self, message: str) -> Optional[bool]:
        """
        Detect if user wants to enable/disable proactive messages.
        
        Args:
            message: User's message text
            
        Returns:
            True to enable, False to disable, None if not mentioned
        """
        message_lower = message.lower()
        
        # Disable patterns
        disable_patterns = [
            "don't send proactive",
            "disable proactive",
            "stop proactive",
            "no proactive message",
            "don't message me proactively",
            "turn off proactive"
        ]
        
        # Enable patterns
        enable_patterns = [
            "enable proactive",
            "send proactive",
            "start proactive",
            "yes to proactive message",
            "turn on proactive",
            "i want proactive"
        ]
        
        for pattern in disable_patterns:
            if pattern in message_lower:
                logger.info(f"✓ User wants to DISABLE proactive messages: '{pattern}' found")
                return False
        
        for pattern in enable_patterns:
            if pattern in message_lower:
                logger.info(f"✓ User wants to ENABLE proactive messages: '{pattern}' found")
                return True
        
        return None
