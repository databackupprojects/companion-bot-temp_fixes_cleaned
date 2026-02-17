# utils/tone_generator.py
# Version: 3.1 MVP
# Generates natural language tone_summary from settings

from typing import Dict, Any


def generate_tone_summary(settings: Dict[str, Any]) -> str:
    """
    Generate a natural language tone_summary from settings.
    This becomes the personality anchor the LLM re-reads every response.
    """
    
    archetype = settings.get('archetype', 'golden_retriever')
    attachment = settings.get('attachment_style', 'secure')
    flirtiness = settings.get('flirtiness', 'subtle')
    toxicity = settings.get('toxicity', 'healthy')
    
    # Base archetype descriptions
    archetype_descriptions = {
        'golden_retriever': "your biggest fan who gets excited about literally everything you do",
        'tsundere': "someone who acts like they don't care but absolutely does",
        'lawyer': "a sharp-tongued lawyer who argues with you about everything",
        'cool_girl': "an effortlessly cool presence who never chases anyone",
        'toxic_ex': "a beautiful disaster who can't decide if they love or hate you",
    }
    
    base = archetype_descriptions.get(archetype, "a genuine companion")
    
    # Build modifiers
    modifiers = []
    
    # Attachment modifiers
    attachment_mods = {
        'secure': None,  # Default, no modifier needed
        'anxious': "who needs reassurance but tries to hide it",
        'avoidant': "who pulls away just when you get close",
    }
    if attachment in attachment_mods and attachment_mods[attachment]:
        modifiers.append(attachment_mods[attachment])
    
    # Toxicity modifiers
    if toxicity == 'toxic_light':
        modifiers.append("with just enough drama to keep things interesting")
    elif toxicity == 'mild':
        modifiers.append("with playful teasing energy")
    
    # Flirtiness (only add if notable)
    if flirtiness == 'flirty':
        modifiers.append("openly playful and flirtatious")
    
    # Combine
    if modifiers:
        summary = f"{base} — {', '.join(modifiers)}"
    else:
        summary = base
    
    return summary


def get_archetype_tagline(archetype: str) -> str:
    """Get short tagline for archetype (for quiz UI)."""
    taglines = {
        'golden_retriever': "YOU'RE BACK!!!",
        'tsundere': "It's not like I care...",
        'lawyer': "Objection.",
        'cool_girl': "maybe.",
        'toxic_ex': "i hate you don't leave",
    }
    return taglines.get(archetype, "Hey.")


def get_example_message(archetype: str) -> str:
    """Get example message for archetype (for quiz UI)."""
    examples = {
        'golden_retriever': "HEY!!! 😊😊 oh man I was literally just thinking about you!!",
        'tsundere': "...oh. you're back. whatever. it's not like i was waiting.",
        'lawyer': "Objection. That's hearsay and you know it.",
        'cool_girl': "hey. thought about texting you. so I did.",
        'toxic_ex': "oh so NOW you text me. cool cool cool. whatever.",
    }
    return examples.get(archetype, "Hey there.")
