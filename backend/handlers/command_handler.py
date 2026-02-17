# handlers/command_handler.py
# Version: 3.1 MVP
# Bot command handlers including /support

import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any

from constants import SUPPORT_RESPONSE, FIRST_MESSAGES
from handlers.user_helpers import get_or_create_user
from utils.tone_generator import generate_tone_summary
from utils.timezone import get_utc_now

logger = logging.getLogger(__name__)


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown."""
    # Escape special Markdown characters
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


class CommandHandler:
    """Handles Telegram bot commands."""
    
    def __init__(self, db, analytics):
        self.db = db
        self.analytics = analytics
    
    async def handle(
        self, 
        telegram_id: int, 
        command: str, 
        args: str = "",
        archetype: Optional[str] = None
    ) -> Optional[str]:
        """Route command to handler.
        
        Args:
            telegram_id: Telegram user ID
            command: Command name (without /)
            args: Command arguments
            archetype: Optional persona archetype
        """
        try:
            # Always ensure session is clean before starting
            try:
                await self.db.rollback()
            except:
                pass
            
            user = await get_or_create_user(
                self.db,
                telegram_id,
                archetype,
                log_context="[Command] ",
            )
            user_id = user['id']
            
            command = command.lower().strip()
            
            handlers = {
                "start": self._handle_start,
                "support": self._handle_support,
                "settings": self._handle_settings,
                "personality": self._handle_personality,
                "summary": self._handle_summary,
                "forget": self._handle_forget,
                "boundaries": self._handle_boundaries,
                "reset": self._handle_reset,
                "schedule": self._handle_schedule,
                "help": self._handle_help,
            }
            
            handler = handlers.get(command)
            if handler:
                try:
                    # Try to call handler with archetype parameter
                    try:
                        logger.debug(f"Calling handler {command} with archetype={archetype}")
                        result = await handler(user_id, user, args, archetype)
                        return result
                    except TypeError as te:
                        # Handler doesn't accept archetype, try without it
                        logger.debug(f"Handler {command} doesn't accept archetype, retrying without it")
                        result = await handler(user_id, user, args)
                        return result
                        
                except Exception as handler_error:
                    logger.error(f"❌ Error in command handler {command}: {handler_error}", exc_info=True)
                    try:
                        await self.db.rollback()
                    except:
                        pass
                    return f"oops, something went wrong with that command. try again?"
            
            return "hmm, I don't know that command. try /help?"
        
        except Exception as e:
            logger.error(f"Fatal error in handle(): {e}", exc_info=True)
            try:
                await self.db.rollback()
            except:
                pass
            return "something went wrong. please try again."
    
    async def _ensure_bot_settings(self, user_id: str, archetype: Optional[str] = None) -> Optional[Any]:
        """Get archetype-specific BotSettings, or any settings if archetype not specified.
        
        NOTE: Does NOT create default settings - just returns what exists.
        Default creation should only happen during quiz completion.
        """
        from sqlalchemy import select
        from models.sql_models import BotSettings
        import uuid
        
        if not archetype:
            archetype = 'golden_retriever'
        
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            
            # Try to get archetype-specific settings first
            stmt = select(BotSettings).where(
                BotSettings.user_id == user_uuid,
                BotSettings.archetype == archetype
            )
            result = await self.db.execute(stmt)
            settings = result.scalar_one_or_none()
            
            if settings:
                return settings
            
            # If no archetype-specific settings, try to get ANY settings for this user
            # This handles the case where user completed quiz from a different telegram bot
            stmt = select(BotSettings).where(BotSettings.user_id == user_uuid)
            result = await self.db.execute(stmt)
            settings = result.scalar_one_or_none()
            
            return settings
                
        except Exception as e:
            logger.error(f"Error in _ensure_bot_settings: {e}")
            return None
    
    async def _handle_start(self, user_id: str, user: Dict, args: str, archetype: Optional[str] = None) -> str:
        """Handle /start command, possibly with config token."""
        
        if args:
            # Config token from quiz - will link telegram_id to browser user data
            # Returns the CORRECT user_id to use (web user id, not telegram temp user)
            linked_user_id = await self._apply_config_token(user_id, args, archetype)
            if linked_user_id:
                from sqlalchemy import select
                from models.sql_models import BotSettings, User
                import uuid
                
                # Use the LINKED user_id, not the temporary telegram user_id
                user_uuid = uuid.UUID(linked_user_id)
                
                # Fetch updated settings after token applied
                stmt = select(BotSettings).where(BotSettings.user_id == user_uuid)
                if archetype:
                    stmt = stmt.where(BotSettings.archetype == archetype)
                result = await self.db.execute(stmt)
                settings = result.scalar_one_or_none()
                
                if settings:
                    await self.analytics.bot_started(user_id, True, settings.archetype)
                    
                    name = settings.bot_name or 'Dot'
                    resolved_archetype = settings.archetype or 'golden_retriever'
                    summary = settings.tone_summary or 'your new companion'
                    
                    # Use cold start first message
                    first_msg = FIRST_MESSAGES.get(resolved_archetype, "hey! I'm {user_name}'s new companion 💫")
                    
                    # Get user name
                    user_stmt = select(User).where(User.id == user_uuid)
                    user_result = await self.db.execute(user_stmt)
                    user_obj = user_result.scalar_one_or_none()
                    user_name = user_obj.name if user_obj and user_obj.name else 'friend'
                    
                    return first_msg.format(user_name=user_name)
        
        default_archetype = archetype or 'golden_retriever'
        await self.analytics.bot_started(user_id, False, default_archetype)
        
        if user.get('name'):
            return f"hey {user['name']}! good to see you again 😊"
        else:
            return "hey there! I'm excited to get to know you 😊\n\nwhat should I call you?"
    
    async def _apply_config_token(self, user_id: str, token: str, archetype: Optional[str] = None) -> Optional[str]:
        """Apply configuration from quiz token - FIXED for SQLAlchemy.
        
        This COPIES bot configuration from web user to telegram user.
        A single telegram user can have multiple bots from different web sources.
        Returns the telegram user's ID if successful, None otherwise.
        """
        from sqlalchemy import select
        from models.sql_models import QuizConfig, BotSettings, User
        from datetime import datetime
        import uuid
        import json
        
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            
            try:
                # Get the quiz config
                stmt = select(QuizConfig).where(
                    QuizConfig.token == token,
                    QuizConfig.used_at.is_(None),
                    QuizConfig.expires_at > get_utc_now()
                )
                result = await self.db.execute(stmt)
                config = result.scalar_one_or_none()
                
                if not config:
                    logger.error(f"No valid config found for token: {token}")
                    return None
                
                # Parse config data
                try:
                    if isinstance(config.config_data, str):
                        data = json.loads(config.config_data)
                    else:
                        data = config.config_data
                        
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to parse config data: {e}")
                    return None
                
                # Get tone summary
                tone_summary = config.tone_summary
                if not tone_summary:
                    from utils.tone_generator import generate_tone_summary
                    tone_summary = generate_tone_summary(data)
                
                # Get the telegram user (current user executing /start command)
                telegram_user_stmt = select(User).where(User.id == user_uuid)
                telegram_user_result = await self.db.execute(telegram_user_stmt)
                telegram_user = telegram_user_result.scalar_one_or_none()
                
                if not telegram_user:
                    logger.error(f"Telegram user not found: {user_uuid}")
                    return None
                
                # Check if a bot with this quiz_token already exists for this telegram user
                settings_stmt = select(BotSettings).where(
                    BotSettings.user_id == user_uuid,
                    BotSettings.quiz_token == token
                )
                settings_result = await self.db.execute(settings_stmt)
                bot_settings = settings_result.scalar_one_or_none()
                
                if bot_settings:
                    # Update existing bot settings
                    logger.info(f"Updating existing bot for telegram user {user_uuid} with token {token}")
                else:
                    # Create NEW bot settings for this telegram user
                    # This allows one telegram user to have multiple bots from different web sources
                    bot_settings = BotSettings(
                        user_id=user_uuid,
                        archetype=data.get('archetype', 'golden_retriever')
                    )
                    self.db.add(bot_settings)
                    logger.info(f"Creating new bot for telegram user {user_uuid} from quiz token")
                
                # Apply quiz configuration to this bot
                bot_settings.quiz_token = token
                bot_settings.bot_name = data.get('bot_name', 'Dot')
                bot_settings.bot_gender = data.get('bot_gender', 'female')
                bot_settings.archetype = data.get('archetype', 'golden_retriever')
                bot_settings.attachment_style = data.get('attachment_style', 'secure')
                bot_settings.flirtiness = data.get('flirtiness', 'subtle')
                bot_settings.toxicity = data.get('toxicity', 'healthy')
                bot_settings.tone_summary = tone_summary
                bot_settings.is_active = True
                bot_settings.updated_at = datetime.utcnow()
                
                # Set as primary if this is the only bot for this user
                count_stmt = select(BotSettings).where(BotSettings.user_id == user_uuid)
                count_result = await self.db.execute(count_stmt)
                all_bots = count_result.scalars().all()
                if len(all_bots) == 0:
                    bot_settings.is_primary = True
                
                # Update telegram user profile with data from quiz
                if data.get('user_name') and not telegram_user.name:
                    telegram_user.name = data.get('user_name')
                telegram_user.spice_consent = data.get('spice_consent', False)
                if data.get('spice_consent'):
                    telegram_user.spice_consent_at = datetime.utcnow()
                
                # Mark quiz token as used and link to telegram user
                config.used_at = datetime.utcnow()
                config.telegram_user_id = user_uuid  # Track which telegram user used this
                
                await self.db.commit()
                
                logger.info(f"✅ Applied bot config to telegram user {user_uuid}: bot={data.get('bot_name')}, archetype={data.get('archetype')}")
                return str(user_uuid)
            
            except Exception as db_error:
                logger.error(f"Database error applying config token: {db_error}", exc_info=True)
                try:
                    await self.db.rollback()
                except Exception as rollback_error:
                    logger.error(f"Rollback error: {rollback_error}")
                return None
            
            
        except Exception as e:
            logger.error(f"Unexpected error in _apply_config_token: {e}", exc_info=True)
            return None
    
    async def _handle_support(self, user_id: str, user: Dict, args: str) -> str:
        """Handle /support command - DROPS ALL PERSONA."""
        
        try:
            # Log support request (if support_requests table exists)
            await self.analytics.support_triggered(user_id, args or "")
            logger.info(f"[Support] Triggered by {user_id}: {args or 'No context'}")
        except Exception as e:
            logger.error(f"Error logging support request: {e}")
        
        return SUPPORT_RESPONSE
    
    async def _handle_settings(self, user_id: str, user: Dict, args: str, archetype: Optional[str] = None) -> str:
        """Handle /settings command."""
        try:
            # Ensure archetype-specific settings exist
            settings = await self._ensure_bot_settings(user_id, archetype)
            
            if not settings:
                return "you haven't completed the quiz yet! start with /start to create your bot."
            
            # Escape values that might contain special Markdown characters
            bot_name = escape_markdown(settings.bot_name or 'Dot')
            resolved_archetype = escape_markdown(settings.archetype or 'golden_retriever')
            attachment = escape_markdown(settings.attachment_style or 'secure')
            flirtiness = escape_markdown(settings.flirtiness or 'subtle')
            toxicity = escape_markdown(settings.toxicity or 'healthy')
            
            return (
                f"*{bot_name}*\n\n"
                f"archetype: {resolved_archetype}\n"
                f"attachment: {attachment}\n"
                f"flirtiness: {flirtiness}\n"
                f"spice: {toxicity}\n\n"
                f"to reconfigure, visit the quiz again!"
            )
        except Exception as e:
            logger.error(f"Error in _handle_settings: {e}")
            return "couldn't load your settings. try again?"
    
    async def _handle_personality(self, user_id: str, user: Dict, args: str, archetype: Optional[str] = None) -> str:
        """Handle /personality command."""
        try:
            # Ensure archetype-specific settings exist
            settings = await self._ensure_bot_settings(user_id, archetype)
            
            if settings and settings.tone_summary:
                # Escape tone_summary which might contain special characters
                tone = escape_markdown(settings.tone_summary)
                return f"I'm {tone}"
            
            return "I'm still figuring myself out. talk to me more?"
        except Exception as e:
            logger.error(f"Error in _handle_personality: {e}")
            return "I'm still figuring myself out. talk to me more?"
    
    async def _handle_summary(self, user_id: str, user: Dict, args: str, archetype: Optional[str] = None) -> str:
        """Handle /summary command - Show onboarding values from quiz."""
        from sqlalchemy import select
        from models.sql_models import BotSettings, User
        import uuid
        
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            
            # Ensure archetype-specific settings exist
            settings = await self._ensure_bot_settings(user_id, archetype)
            
            # Get user
            user_stmt = select(User).where(User.id == user_uuid)
            user_result = await self.db.execute(user_stmt)
            user_obj = user_result.scalar_one_or_none()
            
            if not user_obj or not settings:
                return "couldn't load your profile. try /start again?"
            
            # Build summary with onboarding values (escape all dynamic values)
            summary_lines = ["*📋 your profile:*\n"]
            
            # User information
            user_name = escape_markdown(user_obj.name or "not set")
            summary_lines.append(f"*your name:* {user_name}")
            
            # Bot configuration from quiz
            bot_name = escape_markdown(settings.bot_name or 'Dot')
            resolved_archetype = escape_markdown(settings.archetype or 'golden_retriever')
            gender = escape_markdown(settings.bot_gender or 'female')
            summary_lines.append(f"\n*bot name:* {bot_name}")
            summary_lines.append(f"*personality:* {resolved_archetype}")
            summary_lines.append(f"*gender:* {gender}")
            
            # Personality traits
            attachment = escape_markdown(settings.attachment_style or 'secure')
            flirtiness = escape_markdown(settings.flirtiness or 'subtle')
            toxicity = escape_markdown(settings.toxicity or 'healthy')
            summary_lines.append(f"\n*attachment style:* {attachment}")
            summary_lines.append(f"*flirtiness:* {flirtiness}")
            summary_lines.append(f"*spice level:* {toxicity}")
            
            # Tone summary if available
            if settings.tone_summary:
                tone = escape_markdown(settings.tone_summary)
                summary_lines.append(f"\n*my personality:* {tone}")
            
            # Spice consent status
            spice_status = "✓ consented" if user_obj.spice_consent else "✗ not consented"
            summary_lines.append(f"\n*spice consent:* {spice_status}")
            
            tier = escape_markdown(user_obj.tier or 'free')
            summary_lines.append(f"\n*tier:* {tier}")
            summary_lines.append(f"*joined:* {user_obj.created_at.strftime('%b %d, %Y') if user_obj.created_at else 'recently'}")
            
            summary_lines.append(f"\n✏️ to change these, retake the quiz!")
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            logger.error(f"Error in _handle_summary: {e}")
            return "couldn't load your summary. try again?"
    
    async def _handle_forget(self, user_id: str, user: Dict, topic: str) -> str:
        """Handle /forget command - Forget topics or clear all history."""
        from sqlalchemy import select, delete
        from models.sql_models import Message, MoodHistory, UserBoundary
        import uuid
        
        topic = topic.strip().lower()
        
        # If no argument, ask for clarification
        if not topic:
            return (
                "forget what?\n\n"
                "**/forget [topic]** — stop talking about a specific topic\n"
                "**/forget all** — clear ALL conversation history\n\n"
                "examples:\n"
                "/forget job search\n"
                "/forget my ex\n"
                "/forget all"
            )
        
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            
            # Option 1: Forget all conversation history
            if topic == "all":
                try:
                    # Delete all messages
                    delete_msg_stmt = delete(Message).where(Message.user_id == user_uuid)
                    await self.db.execute(delete_msg_stmt)
                    
                    # Delete all mood history
                    delete_mood_stmt = delete(MoodHistory).where(MoodHistory.user_id == user_uuid)
                    await self.db.execute(delete_mood_stmt)
                    
                    await self.db.commit()
                except Exception as db_error:
                    await self.db.rollback()
                    logger.error(f"Database error in _handle_forget: {db_error}", exc_info=True)
                    return "couldn't clear history. try again?"
                
                try:
                    await self.analytics.boundary_set(user_id, "history", "cleared_all")
                except Exception as analytics_error:
                    logger.warning(f"Analytics error (non-fatal): {analytics_error}")
                
                logger.info(f"[Forget] User {user_id} cleared all history")
                return "✓ all our conversation history has been deleted! starting fresh 🌱"
            
            # Option 2: Forget specific topic
            else:
                try:
                    # Add topic boundary
                    boundary = UserBoundary(
                        user_id=user_uuid,
                        boundary_type='topic',
                        boundary_value=topic,
                        active=True
                    )
                    self.db.add(boundary)
                    await self.db.commit()
                except Exception as db_error:
                    await self.db.rollback()
                    logger.error(f"Database error in _handle_forget: {db_error}", exc_info=True)
                    return "couldn't set boundary. try again?"
                
                try:
                    await self.analytics.boundary_set(user_id, "topic", topic)
                except Exception as analytics_error:
                    logger.warning(f"Analytics error (non-fatal): {analytics_error}")
                
                logger.info(f"[Forget] User {user_id} set boundary on topic: {topic}")
                return f"✓ got it! I'll avoid talking about '{topic}' from now on."
        
        except Exception as e:
            logger.error(f"Unexpected error in _handle_forget: {e}", exc_info=True)
            try:
                await self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"Rollback error: {rollback_error}")
            return "couldn't process that. try again?"
    
    async def _handle_boundaries(self, user_id: str, user: Dict, args: str) -> str:
        """Handle /boundaries command."""
        from sqlalchemy import select
        from models.sql_models import UserBoundary
        import uuid
        
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            
            stmt = select(UserBoundary).where(
                UserBoundary.user_id == user_uuid,
                UserBoundary.active == True
            )
            result = await self.db.execute(stmt)
            boundaries = result.scalars().all()
            
            if not boundaries:
                return "you haven't set any boundaries yet."
            
            lines = ["**your boundaries:**\n"]
            for b in boundaries:
                lines.append(f"• {b.boundary_type}: {b.boundary_value}")
            
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error in _handle_boundaries: {e}")
            return "couldn't load your boundaries. try again?"
    
    async def _handle_reset(self, user_id: str, user: Dict, args: str) -> str:
        """Handle /reset command."""
        from sqlalchemy import delete, update
        from models.sql_models import Message, MoodHistory, BotSettings, UserBoundary, UserMemory
        from datetime import datetime
        import uuid
        
        args = args.lower().strip()
        
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            
            if args == "conversation":
                # Clear message history, keep settings
                try:
                    delete_msg_stmt = delete(Message).where(Message.user_id == user_uuid)
                    await self.db.execute(delete_msg_stmt)
                    
                    delete_mood_stmt = delete(MoodHistory).where(MoodHistory.user_id == user_uuid)
                    await self.db.execute(delete_mood_stmt)
                    
                    await self.db.commit()
                except Exception as db_error:
                    await self.db.rollback()
                    logger.error(f"Database error in reset conversation: {db_error}", exc_info=True)
                    return "couldn't reset conversation. try again?"
                
                return "✓ conversation history cleared! let's start fresh 🌱"
            
            elif args == "personality":
                # Reset to default settings
                try:
                    update_stmt = update(BotSettings).where(
                        BotSettings.user_id == user_uuid
                    ).values(
                        bot_name='Dot',
                        bot_gender='female',
                        archetype='golden_retriever',
                        attachment_style='secure',
                        flirtiness='subtle',
                        toxicity='healthy',
                        tone_summary=None,
                        advanced_settings={},
                        updated_at=get_utc_now()
                    )
                    await self.db.execute(update_stmt)
                    await self.db.commit()
                except Exception as db_error:
                    await self.db.rollback()
                    logger.error(f"Database error in reset personality: {db_error}", exc_info=True)
                    return "couldn't reset personality. try again?"
                
                return "✓ personality reset! take the quiz again to reconfigure."
            
            elif args == "all":
                # Full reset - conversation + personality + boundaries + memories
                try:
                    delete_msg_stmt = delete(Message).where(Message.user_id == user_uuid)
                    await self.db.execute(delete_msg_stmt)
                    
                    delete_mood_stmt = delete(MoodHistory).where(MoodHistory.user_id == user_uuid)
                    await self.db.execute(delete_mood_stmt)
                    
                    update_boundary_stmt = update(UserBoundary).where(
                        UserBoundary.user_id == user_uuid
                    ).values(active=False)
                    await self.db.execute(update_boundary_stmt)
                    
                    delete_memory_stmt = delete(UserMemory).where(UserMemory.user_id == user_uuid)
                    await self.db.execute(delete_memory_stmt)
                    
                    update_settings_stmt = update(BotSettings).where(
                        BotSettings.user_id == user_uuid
                    ).values(
                        bot_name='Dot',
                        bot_gender='female',
                        archetype='golden_retriever',
                        attachment_style='secure',
                        flirtiness='subtle',
                        toxicity='healthy',
                        tone_summary=None,
                        advanced_settings={},
                        updated_at=get_utc_now()
                    )
                    await self.db.execute(update_settings_stmt)
                    await self.db.commit()
                except Exception as db_error:
                    await self.db.rollback()
                    logger.error(f"Database error in reset all: {db_error}", exc_info=True)
                    return "couldn't reset everything. try again?"
                
                return "✓ everything reset! it's like we just met 😊"
            
            else:
                return (
                    "reset options:\n"
                    "**/reset conversation** — clear chat history\n"
                    "**/reset personality** — reset to default persona\n"
                    "**/reset all** — start completely fresh"
                )
        except Exception as e:
            logger.error(f"Unexpected error in _handle_reset: {e}", exc_info=True)
            try:
                await self.db.rollback()
            except Exception as rollback_error:
                logger.error(f"Rollback error: {rollback_error}")
            return "couldn't process that. try again?"
    
    async def _handle_help(self, user_id: str, user: Dict, args: str) -> str:
        """Handle /help command."""
        
        return (
            "**/start** — start or restart\n"
            "**/support** — get real help (drops character)\n"
            "**/summary** — your profile & onboarding data\n"
            "**/settings** — view personality settings\n"
            "**/personality** — who am I?\n"
            "**/forget [topic|all]** — forget topics or clear history\n"
            "**/boundaries** — view your boundaries\n"
            "**/reset [conversation|personality|all]** — reset options\n"
            "**/schedule** — view your upcoming schedule\n"
            "**/help** — this message"
        )
    
    async def _handle_schedule(self, user_id: str, user: Dict, args: str, archetype: Optional[str] = None) -> str:
        """Handle /schedule command - show upcoming meetings and events."""
        from sqlalchemy import select
        from models.sql_models import UserSchedule
        import uuid
        
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            
            # Get upcoming schedules for the next 7 days
            # DB stores times in UTC, so use UTC for comparisons
            # Include events from the past 15 minutes to catch recent/current meetings
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            start_window = now - timedelta(minutes=15)
            week_from_now = now + timedelta(days=7)
            
            stmt = select(UserSchedule).where(
                UserSchedule.user_id == user_uuid,
                UserSchedule.start_time >= start_window,
                UserSchedule.start_time <= week_from_now,
                UserSchedule.is_completed == False
            ).order_by(UserSchedule.start_time)
            
            result = await self.db.execute(stmt)
            schedules = result.scalars().all()
            
            if not schedules:
                return "you don't have any upcoming events scheduled right now 📭"
            
            # Format schedule list
            user_tz = user.get('timezone', 'UTC')
            message = "📅 *your upcoming schedule:*\n\n"
            
            for schedule in schedules:
                # Convert to user's timezone for display
                # Handle naive datetimes properly
                try:
                    import pytz
                    tz = pytz.timezone(user_tz)
                    # Since start_time is naive, we treat it as UTC for conversion
                    local_time = schedule.start_time.replace(tzinfo=pytz.UTC).astimezone(tz)
                    time_str = local_time.strftime("%a, %b %d at %I:%M %p")
                except Exception as tz_err:
                    logger.debug(f"Timezone conversion failed: {tz_err}, using raw time")
                    time_str = schedule.start_time.strftime("%a, %b %d at %I:%M %p") if schedule.start_time else "N/A"
                
                status = "✅ done" if schedule.is_completed else "⏳ upcoming"
                message += f"• *{schedule.event_name}*\n  {time_str} {status}\n"
            
            message += f"\n_use /support if you need to change something_"
            return message
            
        except Exception as e:
            logger.error(f"Error in _handle_schedule: {e}", exc_info=True)
            return "oops, couldn't load your schedule. try again?"
    