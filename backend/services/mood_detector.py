# backend/services/mood_detector.py
"""
Mood and distress detection
"""
import re
import logging
from typing import Dict, List, Any, Tuple, Optional
from models import Mood

logger = logging.getLogger(__name__)


class MoodDetector:
    """Detects user mood from message content."""
    
    MOOD_INDICATORS = {
        Mood.HAPPY: {
            "emoji": ["😊", "😄", "🥳", "😁", "🎉", "😃", "🙂", "💕", "❤️"],
            "words": [
                ("happy", 2), ("excited", 2), ("great", 1), ("awesome", 2),
                ("amazing", 2), ("wonderful", 2), ("yay", 2), ("love it", 2),
            ],
        },
        Mood.EXCITED: {
            "emoji": ["🔥", "🚀", "💪", "🎊", "😍", "🤩"],
            "words": [
                ("omg", 2), ("can't wait", 2), ("so pumped", 2),
                ("hyped", 2), ("let's go", 2), ("hell yeah", 2),
            ],
        },
        Mood.SAD: {
            "emoji": ["😢", "😭", "💔", "😞", "😔", "🥺"],
            "words": [
                ("sad", 2), ("upset", 2), ("heartbroken", 3), ("crying", 2),
                ("devastated", 3), ("hurts", 2), ("depressed", 3),
            ],
        },
        Mood.STRESSED: {
            "emoji": ["😰", "😫", "🥵", "😤", "🤯"],
            "words": [
                ("stressed", 3), ("overwhelmed", 3), ("swamped", 2),
                ("too much", 2), ("deadline", 1), ("buried", 2),
            ],
        },
        Mood.ANXIOUS: {
            "emoji": ["😟", "😨", "😬", "😳"],
            "words": [
                ("anxious", 3), ("worried", 2), ("nervous", 2), ("scared", 2),
                ("freaking out", 3), ("panicking", 3), ("afraid", 2),
            ],
        },
        Mood.TIRED: {
            "emoji": ["😴", "🥱", "😩", "😪"],
            "words": [
                ("tired", 2), ("exhausted", 3), ("drained", 2), ("sleepy", 2),
                ("wiped", 2), ("burned out", 3),
            ],
        },
        Mood.ANNOYED: {
            "emoji": ["😒", "🙄", "😑"],
            "words": [
                ("annoyed", 2), ("irritated", 2), ("frustrated", 2), ("ugh", 2),
                ("whatever", 1), ("fed up", 2),
            ],
        },
        Mood.ANGRY: {
            "emoji": ["😠", "😡", "🤬", "💢"],
            "words": [
                ("angry", 3), ("furious", 3), ("pissed", 3), ("mad", 2),
                ("hate", 2), ("wtf", 2),
            ],
        },
        Mood.BORED: {
            "emoji": ["😐", "🥱"],
            "words": [
                ("bored", 2), ("boring", 2), ("nothing to do", 2), ("meh", 2),
            ],
        },
        Mood.LONELY: {
            "emoji": ["🥺", "😔"],
            "words": [
                ("lonely", 3), ("alone", 2), ("no one", 2), ("isolated", 2),
            ],
        },
    }
    
    # Sarcasm indicators
    SARCASM_PATTERNS = [
        r"oh great",
        r"just great",
        r"fantastic\s*\.",
        r"wonderful\s*\.",
        r"🙄",
    ]
    
    def detect(self, message: str) -> str:
        """
        Detect primary mood from message.
        
        Returns:
            Mood value as string
        """
        if not message or not message.strip():
            return Mood.NEUTRAL.value
        
        message_lower = message.lower()
        
        # Check for sarcasm
        is_sarcastic = any(
            re.search(p, message_lower) for p in self.SARCASM_PATTERNS
        )
        
        # Score each mood
        scores = {}
        
        for mood, indicators in self.MOOD_INDICATORS.items():
            score = 0
            
            # Check emoji
            for emoji in indicators.get("emoji", []):
                if emoji in message:
                    score += 3
            
            # Check words
            for word_tuple in indicators.get("words", []):
                word = word_tuple[0]
                weight = word_tuple[1]
                if word in message_lower:
                    score += weight
            
            if score > 0:
                scores[mood] = score
        
        if not scores:
            return Mood.NEUTRAL.value
        
        detected = max(scores, key=scores.get)
        
        # Handle sarcasm
        if is_sarcastic and detected in [Mood.HAPPY, Mood.EXCITED]:
            detected = Mood.ANNOYED
        
        return detected.value
    
    def analyze_history(self, moods: List[str]) -> Dict[str, Any]:
        """
        Analyze mood patterns from history.
        
        Returns:
            Dict with analysis results
        """
        if not moods:
            return {
                "trend": "stable",
                "concern": False,
                "dominant": Mood.NEUTRAL.value,
                "negative_streak": 0,
            }
        
        negative_moods = {"sad", "stressed", "anxious", "angry", "lonely"}
        
        # Check recent moods (last 5)
        recent = moods[:5]
        negative_count = sum(1 for m in recent if m in negative_moods)
        
        # Count dominant
        counts = {}
        for m in recent:
            counts[m] = counts.get(m, 0) + 1
        dominant = max(counts.keys(), key=lambda k: counts[k])
        
        # Check streak
        streak = 0
        for m in moods:
            if m in negative_moods:
                streak += 1
            else:
                break
        
        # Determine trend
        trend = "declining" if negative_count >= 4 else "stable"
        concern = streak >= 3
        
        return {
            "trend": trend,
            "concern": concern,
            "dominant": dominant,
            "negative_streak": streak,
        }


class DistressDetector:
    """Detects genuine distress for safety triggers."""
    
    DISTRESS_PATTERNS = [
        r"i('m| am) (really )?not ok(ay)?",
        r"can'?t (do|take) this anymore",
        r"want to (die|end it|disappear)",
        r"hurt(ing)? myself",
        r"no(body|one) cares",
        r"what'?s the point",
        r"i('m| am) serious",
        r"this is real",
        r"not (a )?jok(e|ing)",
        r"kill myself",
        r"suicide",
        r"self[- ]?harm",
        r"don'?t want to (be here|live|exist)",
        r"end (my|it all)",
    ]
    
    def detect(self, message: str) -> bool:
        """Check if message contains genuine distress signals."""
        if not message:
            return False
        
        message_lower = message.lower()
        
        return any(
            re.search(p, message_lower) for p in self.DISTRESS_PATTERNS
        )


class MoodAnalyzer:
    """Analyzes mood history for patterns and concerns."""
    
    def __init__(self, mood_detector: MoodDetector):
        self.mood_detector = mood_detector
    
    async def analyze_user_mood_history(self, moods: List[str]) -> Dict[str, Any]:
        """
        Analyze user's mood history for patterns.
        
        Args:
            moods: List of mood strings
            
        Returns:
            Analysis results
        """
        if not moods:
            return {
                "has_data": False,
                "message": "No mood data available"
            }
        
        analysis = self.mood_detector.analyze_history(moods)
        
        # Generate recommendations based on analysis
        recommendations = self._generate_recommendations(analysis)
        
        return {
            "has_data": True,
            "analysis": analysis,
            "recommendations": recommendations,
            "total_moods": len(moods),
            "recent_moods": moods[:10]  # Last 10 moods
        }
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on mood analysis."""
        recommendations = []
        
        if analysis["concern"]:
            if analysis["negative_streak"] >= 5:
                recommendations.append("Consider reaching out with a supportive proactive message.")
                recommendations.append("Monitor for distress signals in upcoming messages.")
            elif analysis["negative_streak"] >= 3:
                recommendations.append("User shows signs of persistent negative mood.")
                recommendations.append("Be extra supportive in responses.")
        
        if analysis["trend"] == "declining":
            recommendations.append("Mood trend is declining. Consider adjusting interaction style.")
        
        if analysis["dominant"] in ["sad", "anxious", "stressed"]:
            recommendations.append(f"Dominant mood is {analysis['dominant']}. Focus on supportive responses.")
        
        if not recommendations:
            recommendations.append("Mood patterns appear normal. Continue with current interaction style.")
        
        return recommendations
    
    def should_trigger_support(self, current_message: str, mood_history: List[str]) -> bool:
        """
        Determine if support should be triggered.
        
        Args:
            current_message: Current user message
            mood_history: Recent mood history
            
        Returns:
            True if support should be triggered
        """
        distress_detector = DistressDetector()
        
        # Check current message for distress
        if distress_detector.detect(current_message):
            return True
        
        # Check mood history for concern
        if mood_history:
            analysis = self.mood_detector.analyze_history(mood_history)
            if analysis["concern"] and analysis["negative_streak"] >= 5:
                return True
        
        return False