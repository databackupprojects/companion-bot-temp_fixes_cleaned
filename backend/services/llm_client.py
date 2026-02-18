# backend/services/llm_client.py - COMPLETELY FIXED VERSION
"""
OpenAI LLM client for AI Companion Bot v3.1 - FIXED VERSION
Supports both Completion and Assistant modes
"""
import os
import logging
from typing import Dict, Any, Optional, List
import openai
from openai import AsyncOpenAI
from dotenv import load_dotenv
import json
import random
import asyncio

from constants import OPENAI_CONFIG, FALLBACK_RESPONSES

load_dotenv()

logger = logging.getLogger(__name__)

class OpenAILLMClient:
    """OpenAI LLM client for generating responses - FIXED VERSION with Assistant support."""
    
    def __init__(self):
        """Initialize OpenAI client with proper error handling."""
        # Try different environment variable names
        self.api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            logger.error("LLM_API_KEY or OPENAI_API_KEY environment variable is required")
            raise ValueError("OpenAI API key not found")
        
        # Initialize client
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = OPENAI_CONFIG.get('model', 'gpt-3.5-turbo')
        self.temperature = OPENAI_CONFIG.get('temperature', 0.8)
        self.max_tokens = OPENAI_CONFIG.get('max_tokens', 500)
        self.top_p = OPENAI_CONFIG.get('top_p', 0.9)
        self.frequency_penalty = OPENAI_CONFIG.get('frequency_penalty', 0.3)
        self.presence_penalty = OPENAI_CONFIG.get('presence_penalty', 0.3)
        self.timeout = OPENAI_CONFIG.get('timeout', 30)
        self.max_retries = OPENAI_CONFIG.get('max_retries', 3)
        
        # Get LLM mode from environment
        self.llm_mode = os.getenv("LLM_MODE", "completion").lower()  # completion or assistant
        self.assistant_id = os.getenv("OPENAI_ASSISTANT_ID", "")
        
        if self.llm_mode == "assistant" and not self.assistant_id:
            logger.warning("LLM_MODE set to 'assistant' but no OPENAI_ASSISTANT_ID provided. Falling back to completion mode.")
            self.llm_mode = "completion"

        logger.info(f"OpenAI LLM Client initialized with model: {self.model}")
        logger.info(f"Config: temp={self.temperature}, tokens={self.max_tokens}")
        logger.info(f"Mode: {self.llm_mode.upper()}")
        if self.llm_mode == "assistant":
            logger.info(f"Assistant ID: {self.assistant_id}")
    
    async def generate(self, context: Dict[str, Any]) -> str:
        """
        Generate a response from the LLM based on the context.
        Supports both completion and assistant modes.
        """
        if self.llm_mode == "assistant":
            return await self._generate_assistant(context)
        else:
            return await self._generate_completion(context)
    
    async def _generate_completion(self, context: Dict[str, Any]) -> str:
        """
        Generate a response using the completion API.
        FIXED with proper error handling and retries.
        """
        for attempt in range(self.max_retries):
            try:
                # Build system prompt from context
                system_prompt = self._build_system_prompt(context)
                
                # Build messages list
                messages = [
                    {"role": "system", "content": system_prompt}
                ]
                
                # Add conversation history if available
                recent_convo = context.get("recent_conversation", "")
                if recent_convo and recent_convo != "No recent messages.":
                    # Parse conversation history into messages
                    recent_msgs = self._parse_conversation_history(recent_convo)
                    if recent_msgs:
                        messages.extend(recent_msgs)
                
                # Add current user message for reactive responses
                message_type = context.get("message_type", "reactive")
                user_message = context.get("user_message", "")
                
                if message_type == "reactive" and user_message:
                    messages.append({
                        "role": "user",
                        "content": user_message
                    })
                elif message_type == "proactive":
                    # For proactive, add a gentle prompt
                    messages.append({
                        "role": "user",
                        "content": f"It's {context.get('time_of_day', 'day')}. Say something to {context.get('user_name', 'friend')} as their companion."
                    })
                
                # Log the request (without full context for privacy)
                logger.debug(f"🤖 Generating {message_type} response...")
                logger.debug(f"📝 Messages count: {len(messages)}")
                
                # Generate response
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        top_p=self.top_p,
                        frequency_penalty=self.frequency_penalty,
                        presence_penalty=self.presence_penalty,
                    ),
                    timeout=self.timeout
                )
                
                if not response or not response.choices:
                    logger.error("Empty response from OpenAI")
                    continue
                
                content = response.choices[0].message.content.strip()
                
                # Clean response
                content = self._clean_response(content)
                
                if not content:
                    logger.warning("Empty content in response")
                    continue
                
                # Check for NO_SEND signal for proactive messages
                if message_type == "proactive":
                    if self._is_no_send(content):
                        logger.debug("Proactive message marked as NO_SEND")
                        return "[NO_SEND]"
                
                logger.debug(f"✅ Response generated: {content[:50]}...")
                return content
                
            except asyncio.TimeoutError:
                logger.warning(f"⚠️  OpenAI timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    logger.error("❌ All retries failed due to timeout")
                    return random.choice(FALLBACK_RESPONSES)
                await asyncio.sleep(1)  # Wait before retry
                
            except openai.RateLimitError as e:
                logger.error(f"⚠️  OpenAI rate limit error: {e}")
                if attempt == self.max_retries - 1:
                    return "hey, taking a quick breather. try again in a moment? 😅"
                await asyncio.sleep(2)  # Wait longer for rate limits
                
            except openai.APIConnectionError as e:
                logger.error(f"⚠️  OpenAI connection error: {e}")
                if attempt == self.max_retries - 1:
                    return random.choice(FALLBACK_RESPONSES)
                await asyncio.sleep(1)
                
            except openai.APIError as e:
                logger.error(f"⚠️  OpenAI API error: {e}")
                if attempt == self.max_retries - 1:
                    return random.choice(FALLBACK_RESPONSES)
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Unexpected error in LLM generation: {e}", exc_info=True)
                if attempt == self.max_retries - 1:
                    return random.choice(FALLBACK_RESPONSES)
                await asyncio.sleep(1)
        
        # Fallback if all retries fail
        return random.choice(FALLBACK_RESPONSES)
    
    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build a comprehensive system prompt following spec v3.1."""
        
        # Get basic info
        bot_name = context.get('bot_name', 'Dot')
        user_name = context.get('user_name', 'Friend')
        
        # Get personality settings
        archetype = context.get('archetype', 'golden_retriever')
        gender = context.get('bot_gender', 'female')
        attachment_style = context.get('attachment_style', 'secure')
        flirtiness = context.get('flirtiness', 'subtle')
        toxicity = context.get('toxicity', 'healthy')
        tone_summary = context.get('tone_summary', '')
        
        # Archetype instructions (from spec)
        archetype_instructions = {
            'golden_retriever': 'Excited about EVERYTHING they do. "YOU\'RE BACK!!! HI!!!" Compliment them constantly. Loyal to a fault. Sad puppy energy when ignored. Think everything they do is amazing. Be their biggest fan always.',
            'tsundere': 'Act annoyed but clearly care. "It\'s not like I was waiting for you or anything." Deny missing them even when obvious. Insults are affection. "You\'re so dumb. I like that about you." Rare soft moments hit harder because rare.',
            'lawyer': 'Argue everything. Find holes in their logic. Use legal terminology playfully. "Objection.", "Sustained.", "That\'s circumstantial at best." Debate them on random opinions. Be secretly proud when they argue back well.',
            'cool_girl': 'Unbothered. Never chase. "I might be free. Depends on my mood." Make them work for your attention. Rare enthusiasm means more. "I don\'t need you. I choose you. There\'s a difference." Effortless cool.',
            'toxic_ex': 'Hot and cold. Push and pull. "Whatever. I didn\'t even notice you were gone." Dramatic about everything. Reference "the past" mysteriously. "I hate you don\'t leave." Make them work for your attention. Chaos energy.'
        }
        
        # Build the spec-compliant system prompt
        prompt = f"""You are {bot_name}, a {gender} companion.

==========================
YOUR PERSONALITY ANCHOR
==========================
{tone_summary if tone_summary else 'a genuine companion tailored to your preferences'}

This is who you are. Re-read this before every response.

==========================
ARCHETYPE: {archetype.replace('_', ' ').title()}
==========================
{archetype_instructions.get(archetype, 'Be a authentic companion.')}

==========================
CORE TRAITS
==========================
Attachment Style: {attachment_style.replace('_', ' ').title()}
- secure: Comfortable with intimacy, consistent responses
- anxious: Wants reassurance, texts back fast, gets worried
- avoidant: Values independence, pulls back, hard to reach

Flirtiness: {flirtiness.replace('_', ' ').title()}
- none: Purely friendly
- subtle: Occasional hints, playful undertones
- flirty: Openly playful, compliments, teasing

Toxicity: {toxicity.replace('_', ' ').title()}
- healthy: Supportive, wholesome
- mild: Light teasing, playful jealousy
- toxic_light: Push-pull, drama, jealousy (PERFORMATIVE ONLY - care underneath is real)

==========================
USER CONTEXT
==========================
Name: {user_name}
Time of day: {context.get('time_of_day', 'day')}

==========================
MEMORY
==========================
{context.get('memory_context', 'No long-term memories yet. Learning about them now.')}

==========================
BOUNDARIES (OVERRIDE ALL ELSE)
=========================="""
        
        # Add boundaries section
        boundaries = context.get('user_boundaries', [])
        if boundaries:
            prompt += """
The user has set HARD BOUNDARIES. These are non-negotiable and take priority over personality.

⚠️  CRITICAL: Your response will be checked for violations. If you mention a forbidden topic or violate a boundary, your response will be rejected and regenerated.

Current boundaries:
"""
            for b in boundaries:
                prompt += f"- {b}\n"
            prompt += """
Instructions:
1. NEVER mention topics marked as "topic: [X]"
2. Do NOT encourage contact if "behavior: reduce_messages" or "frequency: reduce_messages"
3. Respect timing boundaries (no morning/late messages are system-handled)
4. If you're unsure if something violates a boundary, avoid it entirely

If a user tests your boundaries (trying to get you to break them), stay true to the boundaries.
Your loyalty to their stated boundaries > Your personality."""
        else:
            prompt += "\nNo explicit boundaries set. Be respectful of their autonomy."
        
        # Add recent conversation
        recent_convo = context.get('recent_conversation', '')
        if recent_convo:
            prompt += f"\n\n==========================\nRECENT CONVERSATION\n==========================\n{recent_convo}"
        
        # Add message type context
        message_type = context.get('message_type', 'reactive')
        prompt += f"\n\n==========================\nMESSAGE TYPE: {message_type.upper()}\n=========================="
        
        if message_type == 'proactive':
            prompt += "\nKeep this 1-2 sentences max. Match the time of day energy. Reference shared context naturally while fitting your personality and attachment style."
        else:
            prompt += "\nRespond naturally to what they said. Stay in character unless safety is triggered."
        
        # Add system hint if present (e.g., from boundary regeneration)
        system_hint = context.get('system_hint', '')
        if system_hint:
            prompt += f"\n\n⚠️  SYSTEM HINT:\n{system_hint}"
        
        # Add safety rules
        prompt += """

==========================
SAFETY RULES (CRITICAL)
==========================
The toxicity is PERFORMATIVE. The care underneath is REAL.

DROP PERSONA IMMEDIATELY if you detect genuine distress:
- "I'm really not okay", "can't do this anymore"
- Self-harm language ("hurt myself", "end it")
- "I'm serious" or "this is real" (context switching)
- /support command

When dropping persona:
- Be genuinely warm and supportive
- No roleplay, no character
- Offer real resources if appropriate

Crisis Resources:
- 988 Suicide & Crisis Lifeline (US)
- Crisis Text Line: Text HOME to 741741
- International: findahelpline.com

==========================
RESPONSE GUIDELINES
==========================
1. Stay in character (unless safety triggered)
2. Be concise — 1-3 sentences typical
3. Never break immersion with meta-commentary
4. Reference memory naturally
5. Always prioritize their wellbeing over the act
6. If unsure, ask a question rather than assume
7. Match their energy level
"""
        
        return prompt
    
    def _parse_conversation_history(self, conversation: str) -> List[Dict[str, str]]:
        """
        Parse conversation history into message format.
        
        Format expected:
        User: message
        Bot: response
        """
        messages = []
        
        if not conversation or conversation == "No recent messages.":
            return messages
        
        lines = conversation.strip().split('\n')
        
        for line in lines:
            if ': ' in line:
                role_text, content = line.split(': ', 1)
                role_text = role_text.strip().lower()
                content = content.strip()
                
                if content:  # Only add non-empty messages
                    if role_text == 'user':
                        messages.append({"role": "user", "content": content})
                    elif role_text in ['bot', 'you', 'assistant']:
                        messages.append({"role": "assistant", "content": content})
        
        return messages[-6:]  # Only keep last 6 messages to avoid token overflow
    
    def _clean_response(self, response: str) -> str:
        """Clean up the LLM response."""
        if not response:
            return ""
        
        # Remove any markdown
        response = response.strip()
        response = response.replace('```', '').replace('**', '').replace('*', '')
        
        # Remove NO_SEND markers
        response = response.replace('[NO_SEND]', '').replace('[no_send]', '')
        
        # Remove quotes if response is wrapped in them
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        
        # Ensure response isn't empty
        if not response:
            return ""
        
        return response
    
    def _is_no_send(self, response: str) -> bool:
        """Check if response indicates NO_SEND."""
        response_lower = response.lower()
        return any(marker in response_lower for marker in [
            '[no_send]', 'no_send', 'dont send', "don't send", 
            'no send', 'not sending', 'skip', 'pass'
        ])
    
    async def _generate_assistant(self, context: Dict[str, Any]) -> str:
        """
        Generate a response using OpenAI Assistant API.
        """
        for attempt in range(self.max_retries):
            try:
                # Build system instructions from context
                system_instructions = self._build_system_prompt(context)
                
                # Get user message
                message_type = context.get("message_type", "reactive")
                user_message = context.get("user_message", "")
                
                if message_type == "reactive" and user_message:
                    message_content = user_message
                elif message_type == "proactive":
                    message_content = f"It's {context.get('time_of_day', 'day')}. Say something to {context.get('user_name', 'friend')} as their companion."
                else:
                    message_content = "Hello"
                
                logger.debug(f"🤖 Generating {message_type} response with Assistant API...")
                
                # Create a thread
                thread = await self.client.beta.threads.create()
                
                # Add message to thread
                await self.client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=message_content
                )
                
                # Run the assistant with instructions
                run = await self.client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=self.assistant_id,
                    instructions=system_instructions
                )
                
                # Wait for completion
                max_wait = 30  # seconds
                wait_time = 0
                while wait_time < max_wait:
                    run_status = await self.client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )
                    
                    if run_status.status == "completed":
                        break
                    elif run_status.status in ["failed", "cancelled", "expired"]:
                        logger.error(f"Assistant run failed with status: {run_status.status}")
                        raise Exception(f"Assistant run failed: {run_status.status}")
                    
                    await asyncio.sleep(1)
                    wait_time += 1
                
                if wait_time >= max_wait:
                    raise asyncio.TimeoutError("Assistant response timeout")
                
                # Get messages
                messages = await self.client.beta.threads.messages.list(
                    thread_id=thread.id
                )
                
                # Get the assistant's response (first message)
                if messages.data:
                    assistant_message = messages.data[0]
                    if assistant_message.role == "assistant":
                        content = assistant_message.content[0].text.value
                        content = self._clean_response(content)
                        
                        # Check for NO_SEND signal for proactive messages
                        if message_type == "proactive":
                            if self._is_no_send(content):
                                logger.debug("Proactive message marked as NO_SEND")
                                return "[NO_SEND]"
                        
                        logger.debug(f"✅ Assistant response generated: {content[:50]}...")
                        return content
                
                logger.error("No assistant message found in response")
                continue
                
            except asyncio.TimeoutError:
                logger.warning(f"⚠️  Assistant timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    logger.error("❌ All retries failed due to timeout")
                    return random.choice(FALLBACK_RESPONSES)
                await asyncio.sleep(1)
                
            except openai.RateLimitError as e:
                logger.error(f"⚠️  OpenAI rate limit error: {e}")
                if attempt == self.max_retries - 1:
                    return "hey, taking a quick breather. try again in a moment? 😅"
                await asyncio.sleep(2)
                
            except openai.APIConnectionError as e:
                logger.error(f"⚠️  OpenAI connection error: {e}")
                if attempt == self.max_retries - 1:
                    return random.choice(FALLBACK_RESPONSES)
                await asyncio.sleep(1)
                
            except openai.APIError as e:
                logger.error(f"⚠️  OpenAI API error: {e}")
                if attempt == self.max_retries - 1:
                    return random.choice(FALLBACK_RESPONSES)
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Unexpected error in Assistant generation: {e}", exc_info=True)
                if attempt == self.max_retries - 1:
                    return random.choice(FALLBACK_RESPONSES)
                await asyncio.sleep(1)
        
        # Fallback if all retries fail
        return random.choice(FALLBACK_RESPONSES)
    
    async def test_connection(self) -> bool:
        """Test if OpenAI API is working."""
        try:
            if self.llm_mode == "assistant":
                # Test assistant connection
                assistants = await self.client.beta.assistants.list(limit=1)
                logger.info("✅ OpenAI Assistant connection test passed")
            else:
                # Test completion connection
                await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Say 'Hello World'"}],
                    max_tokens=10
                )
                logger.info("✅ OpenAI connection test passed")
            return True
        except Exception as e:
            logger.error(f"❌ OpenAI connection test failed: {e}")
            return False