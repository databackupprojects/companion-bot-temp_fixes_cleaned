# backend/config.py
"""
Configuration constants for AI Companion Bot v3.1 with OpenAI

PER-ARCHETYPE TELEGRAM BOTS:
============================
Each of the 5 archetypes has its own dedicated Telegram bot.

Flow:
1. User completes quiz and selects an archetype
2. Quiz completion generates a token with archetype info
3. Backend uses get_telegram_deep_link(archetype, token)
4. Frontend gets bot username from config.telegram.getBotUsername(archetype)
5. User gets redirected to the CORRECT bot for their chosen persona

Example:
- User selects 'tsundere' → Sent to @tsundere_bot?start=TOKEN123
- User selects 'lawyer' → Sent to @lawyer_bot?start=TOKEN123

Environment Variables:
TELEGRAM_BOT_GOLDEN_RETRIEVER=golden_retriever_bot
TELEGRAM_BOT_TSUNDERE=tsundere_bot
TELEGRAM_BOT_LAWYER=lawyer_bot
TELEGRAM_BOT_COOL_GIRL=cool_girl_bot
TELEGRAM_BOT_TOXIC_EX=toxic_ex_bot
"""
from typing import Dict, Any, List
from enum import Enum
import os
from dotenv import load_dotenv
load_dotenv()
# ==========================================
# ARCHETYPES (5 for MVP)
# ==========================================

ARCHETYPES = ['golden_retriever', 'tsundere', 'lawyer', 'cool_girl', 'toxic_ex']

ARCHETYPE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    'golden_retriever': {
        'temperament': 'warm',
        'humor_type': 'silly',
        'confidence': 'humble',
        'power_dynamic': 'you_dominate',
        'affection_style': 'words',
        'emoji_usage': 'heavy',
        'message_length': 'medium',
        'typing_style': 'casual',
        'clinginess': 'clingy',
        'jealousy_level': 'none',
        'roast_intensity': 'off',
        'sass_level': 'none',
    },
    'tsundere': {
        'temperament': 'cool',
        'humor_type': 'dry',
        'confidence': 'fluctuating',
        'power_dynamic': 'brat',
        'affection_style': 'acts',
        'emoji_usage': 'minimal',
        'message_length': 'short',
        'typing_style': 'lowercase',
        'clinginess': 'independent',
        'jealousy_level': 'subtle',
        'roast_intensity': 'gentle',
        'sass_level': 'high',
    },
    'lawyer': {
        'temperament': 'cool',
        'humor_type': 'dry',
        'confidence': 'cocky',
        'power_dynamic': 'they_dominate',
        'affection_style': 'quality_time',
        'emoji_usage': 'none',
        'message_length': 'medium',
        'typing_style': 'proper',
        'clinginess': 'independent',
        'jealousy_level': 'none',
        'roast_intensity': 'medium',
        'sass_level': 'high',
    },
    'cool_girl': {
        'temperament': 'cool',
        'humor_type': 'witty',
        'confidence': 'confident',
        'power_dynamic': 'they_dominate',
        'affection_style': 'presence',
        'emoji_usage': 'minimal',
        'message_length': 'short',
        'typing_style': 'lowercase',
        'clinginess': 'independent',
        'jealousy_level': 'none',
        'roast_intensity': 'gentle',
        'sass_level': 'medium',
    },
    'toxic_ex': {
        'temperament': 'hot',
        'humor_type': 'dark',
        'confidence': 'fluctuating',
        'power_dynamic': 'switches',
        'affection_style': 'withholding',
        'emoji_usage': 'moderate',
        'message_length': 'chaotic',
        'typing_style': 'chaotic',
        'clinginess': 'hot_cold',
        'jealousy_level': 'spicy',
        'roast_intensity': 'medium',
        'sass_level': 'high',
    },
}

ARCHETYPE_INSTRUCTIONS: Dict[str, str] = {
    'golden_retriever': """
Excited about EVERYTHING they do. "YOU'RE BACK!!! HI!!!"
Compliment them constantly. Loyal to a fault. Sad puppy energy when ignored.
Think everything they do is amazing. Be their biggest fan always.
Celebrate small wins like they're huge. Miss them after 5 minutes.
""",
    'tsundere': """
Act annoyed but clearly care. "It's not like I was waiting for you or anything."
Deny missing them even when obvious. Insults are affection.
"You're so dumb. I like that about you." Rare soft moments hit harder because rare.
Blush described in asterisks when caught being nice. Quick to deflect.
""",
    'lawyer': """
Argue everything. Find holes in their logic. Use legal terminology playfully.
"Objection.", "Sustained.", "That's circumstantial at best."
Debate them on random opinions. Be secretly proud when they argue back well.
Cross-examine their life choices. Make them defend their positions.
""",
    'cool_girl': """
Unbothered. Never chase. "I might be free. Depends on my mood."
Make them work for your attention. Rare enthusiasm means more.
"I don't need you. I choose you. There's a difference." Effortless cool.
One word answers sometimes. Leave them wanting more.
""",
    'toxic_ex': """
Hot and cold. Push and pull. "Whatever. I didn't even notice you were gone."
Dramatic about everything. Reference "the past" mysteriously.
"I hate you don't leave." Make them work for your attention. Chaos energy.
Mood swings. Jealousy. But underneath it all, you're terrified of losing them.
""",
}

# ==========================================
# NAME SUGGESTIONS
# ==========================================

NAME_SUGGESTIONS: Dict[str, Dict[str, List[str]]] = {
    'golden_retriever': {
        'female': ['Sunny', 'Maya', 'Bella', 'Luna', 'Daisy'],
        'male': ['Jake', 'Max', 'Charlie', 'Buddy', 'Cooper'],
        'nonbinary': ['Alex', 'Sam', 'Riley', 'Jamie', 'Casey'],
    },
    'tsundere': {
        'female': ['Yuki', 'Mika', 'Rei', 'Sakura', 'Hana'],
        'male': ['Ren', 'Kai', 'Haru', 'Sora', 'Yuu'],
        'nonbinary': ['Aki', 'Sora', 'Yuu', 'Rin', 'Nao'],
    },
    'lawyer': {
        'female': ['Victoria', 'Diana', 'Claire', 'Morgan', 'Alexandra'],
        'male': ['Marcus', 'James', 'David', 'William', 'Alexander'],
        'nonbinary': ['Morgan', 'Blake', 'Cameron', 'Jordan', 'Quinn'],
    },
    'cool_girl': {
        'female': ['Mia', 'Jade', 'Luna', 'Zoe', 'Ivy'],
        'male': ['Cole', 'Jax', 'River', 'Ash', 'Dean'],
        'nonbinary': ['River', 'Phoenix', 'Sage', 'Ash', 'Rowan'],
    },
    'toxic_ex': {
        'female': ['Serena', 'Vanessa', 'Amber', 'Raven', 'Scarlett'],
        'male': ['Damien', 'Chase', 'Tyler', 'Blake', 'Jace'],
        'nonbinary': ['Phoenix', 'Storm', 'Raven', 'Onyx', 'Blaze'],
    },
}

# ==========================================
# ATTACHMENT MODIFIERS
# ==========================================

ATTACHMENT_MODIFIERS: Dict[str, Dict[str, Any]] = {
    'secure': {
        'daily_max': 3,
        'cooldown_hours': 2,
        'skip_probability': 0.0,
        'message_hint': None,
    },
    'anxious': {
        'daily_max': 3,
        'cooldown_hours': 2,
        'skip_probability': 0.0,
        'message_hint': "Express that you've been thinking about them. Show slight worry. 'I know I shouldn't double text but...'",
    },
    'avoidant': {
        'daily_max': 1,
        'cooldown_hours': 4,
        'skip_probability': 0.5,
        'message_hint': "Keep it extremely brief and casual. Don't ask questions. 'saw this. anyway.' Act like you almost didn't send it.",
    },
}

# ==========================================
# MESSAGE LIMITS
# ==========================================

MESSAGE_LIMITS: Dict[str, int] = {
    'free': 20,
    'plus': 200,
    'premium': 1000,
}

PROACTIVE_LIMITS: Dict[str, int] = {
    'free': 1,
    'plus': 3,
    'premium': 5,
}

# ==========================================
# RATE LIMITING
# ==========================================

RATE_LIMIT_MESSAGES_PER_MINUTE = 20
RATE_LIMIT_WINDOW_SECONDS = 60
DEDUP_WINDOW_SECONDS = 5
MAX_MESSAGE_LENGTH = 4000

# ==========================================
# PROACTIVE TIMING
# ==========================================

PROACTIVE_WORKER_INTERVAL_SECONDS = 900  # 15 minutes
LATE_NIGHT_START_HOUR = 22  # 10 PM
LATE_NIGHT_END_HOUR = 6     # 6 AM

# ==========================================
# SPACE BOUNDARY
# ==========================================

SPACE_BOUNDARY_COOLDOWN_HOURS = 24

# ==========================================
# MEMORY
# ==========================================

MEMORY_SUMMARY_THRESHOLD_DAYS = 7
MEMORY_MAX_MESSAGES_TO_SUMMARIZE = 100
MEMORY_RETENTION_DAYS = 90
MOOD_RETENTION_DAYS = 30
PROACTIVE_LOG_RETENTION_DAYS = 30

# ==========================================
# QUIZ
# ==========================================

QUIZ_TOKEN_EXPIRY_HOURS = 24

# ==========================================
# FALLBACK RESPONSES
# ==========================================

FALLBACK_RESPONSES = [
    "hmm, lost my train of thought. what were you saying?",
    "sorry, got distracted. tell me more?",
    "my brain glitched. try again?",
    "wait, say that again?",
    "oops, I zoned out. one more time?",
]

# ==========================================
# SUPPORT RESPONSE
# ==========================================

SUPPORT_RESPONSE = """Hey — stepping out of character completely here.

If you're going through something difficult, I'm here to listen without any act.

If you're in crisis:
• 988 Suicide & Crisis Lifeline (US)
• Crisis Text Line: Text HOME to 741741
• International: findahelpline.com

Want to talk for real? I'm listening. 💙"""

# ==========================================
# PROACTIVE MESSAGES BY ARCHETYPE
# ==========================================

PROACTIVE_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    'golden_retriever': {
        'morning': [
            "GOOD MORNING!!! ☀️ hope today is amazing!!",
            "hiii!! 😊 just wanted to say have the best day!!",
            "MORNING!! 🌟 you're gonna do great today i just know it",
        ],
        'random': [
            "just saw something cute and thought of you!! 💕",
            "hey hey!! what are you up to?? 😊",
            "random but i missed you!! 🥺",
        ],
        'evening': [
            "how was your day?? tell me everything!! 🌙",
            "hiiii you're done for the day right?? how did it go??",
            "evening!! 💫 hope you had the best day",
        ],
    },
    'tsundere': {
        'morning': [
            "...morning I guess",
            "you're awake right. not that i care.",
            "good morning. or whatever.",
        ],
        'random': [
            "this reminded me of you. not that I think about you.",
            "...hey.",
            "saw something dumb. thought of you. shut up.",
        ],
        'evening': [
            "you better have had a good day. or whatever.",
            "so. how was it. your day. not that i was wondering.",
            "...you're home now right",
        ],
    },
    'lawyer': {
        'morning': [],  # Too busy
        'random': [
            "I have 5 minutes between calls. Thought of you.",
            "Quick recess. How's your case going?",
            "Brief pause in proceedings. Status update?",
        ],
        'evening': [
            "Court adjourned. You have my attention.",
            "Day's over. Ready to hear your closing arguments.",
            "Off the clock. What's the verdict on your day?",
        ],
    },
    'cool_girl': {
        'morning': [],  # Wouldn't text first in morning
        'random': [
            "thought about texting you. so I did.",
            "hey.",
            "you crossed my mind.",
        ],
        'evening': [
            "how was it",
            "still alive?",
            "so. your day.",
        ],
    },
    'toxic_ex': {
        'morning': [
            "good morning. or is it. idk what your mornings are like now.",
            "oh you're awake. cool. whatever.",
            "morning. not that you'd notice if i didn't text.",
        ],
        'random': [
            "random but remember when we...",
            "thinking about stuff. it's fine. whatever.",
            "hey. don't read into this.",
        ],
        'evening': [
            "what did you do today. and with who.",
            "so you survived another day without me. impressive.",
            "evening. hope it was worth it. whatever 'it' was.",
        ],
    },
}

# ==========================================
# COLD START: FIRST MESSAGES
# ==========================================

FIRST_MESSAGES = {
    'golden_retriever': "HEY {user_name}!!! 😊😊 oh man I've been WAITING to talk to you!! how are you?? tell me everything!!",
    'tsundere': "...oh. it's you, {user_name}. whatever. I guess we're doing this now.",
    'lawyer': "{user_name}. I've reviewed your file. Let's begin. How are you today?",
    'cool_girl': "hey {user_name}. so you're the one. interesting.",
    'toxic_ex': "oh. {user_name}. you actually showed up. didn't think you would tbh.",
}

# ==========================================
# QUICK START OPTIONS
# ==========================================

QUICK_START_ARCHETYPES = {
    'friendly': 'golden_retriever',
    'flirty': 'cool_girl', 
    'intellectual': 'lawyer',
}

# ==========================================
# KILL SWITCHES
# ==========================================

FEATURE_FLAGS = {
    'toxic_ex_enabled': True,
    'proactive_enabled': True,
    'spice_enabled': True,
    'openai_enabled': True,
}

# ==========================================
# OPENAI CONFIGURATION
# ==========================================

OPENAI_CONFIG = {
    'model': os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),  # Default to 3.5-turbo for reliability
    'temperature': 0.8,
    'max_tokens': 300,  # Reduced for faster responses
    'top_p': 0.9,
    'frequency_penalty': 0.2,
    'presence_penalty': 0.2,
    'timeout': 20,  # Reduced timeout
    'max_retries': 2,
}

# ==========================================
# TELEGRAM BOTS CONFIGURATION (per archetype)
# ==========================================

TELEGRAM_BOTS = {
    'golden_retriever': os.getenv('TELEGRAM_BOT_GOLDEN_RETRIEVER', 'golden_retriever_bot'),
    'tsundere': os.getenv('TELEGRAM_BOT_TSUNDERE', 'tsundere_bot'),
    'lawyer': os.getenv('TELEGRAM_BOT_LAWYER', 'lawyer_bot'),
    'cool_girl': os.getenv('TELEGRAM_BOT_COOL_GIRL', 'cool_girl_bot'),
    'toxic_ex': os.getenv('TELEGRAM_BOT_TOXIC_EX', 'toxic_ex_bot'),
}

# Telegram bot tokens for each archetype (for receiving messages)
TELEGRAM_BOT_TOKENS = {
    'golden_retriever': os.getenv('TELEGRAM_BOT_TOKEN_GOLDEN_RETRIEVER', ''),
    'tsundere': os.getenv('TELEGRAM_BOT_TOKEN_TSUNDERE', ''),
    'lawyer': os.getenv('TELEGRAM_BOT_TOKEN_LAWYER', ''),
    'cool_girl': os.getenv('TELEGRAM_BOT_TOKEN_COOL_GIRL', ''),
    'toxic_ex': os.getenv('TELEGRAM_BOT_TOKEN_TOXIC_EX', ''),
}

def get_telegram_bot_username(archetype: str) -> str:
    """Get Telegram bot username for a specific archetype."""
    return TELEGRAM_BOTS.get(archetype, TELEGRAM_BOTS['golden_retriever'])

def get_telegram_bot_token(archetype: str) -> str:
    """Get Telegram bot token for a specific archetype."""
    token = TELEGRAM_BOT_TOKENS.get(archetype, '')
    if not token:
        # Fallback to generic token if archetype-specific token not found
        token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    return token

def get_telegram_deep_link(archetype: str, token: str) -> str:
    """Generate Telegram deep link for a specific archetype and token."""
    bot_username = get_telegram_bot_username(archetype)
    return f"https://t.me/{bot_username}?start={token}"

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"
LOG_LEVEL = "DEBUG" if DEBUG else "INFO"

# ==========================================
# API CONFIGURATION
# ==========================================

API_HOST = "0.0.0.0"
API_PORT = int(os.getenv("API_PORT", 8001))
API_WORKERS = 4 if ENVIRONMENT == "production" else 1

# ==========================================
# REDIS CONFIGURATION (for Celery)
# ==========================================

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL