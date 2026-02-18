# backend/telegram_bot.py - MULTI-BOT VERSION FOR PERSONAS
"""
Telegram bot integration for AI Companion Bot v3.1 - Multi-Bot Support
Each persona has its own Telegram bot and token
"""
import os
import logging
import asyncio
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Try to import Telegram libraries
try:
    from telegram import Update, Bot
    from telegram.ext import (
        Application, 
        CommandHandler, 
        MessageHandler, 
        filters, 
        CallbackContext,
        ApplicationBuilder
    )
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("Telegram libraries not installed. Telegram bot will not work.")

load_dotenv()

logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram bot handler for AI Companion Bot - Multi-Bot Support."""
    
    def __init__(self, message_handler, command_handler, token: Optional[str] = None, archetype: Optional[str] = None):
        """Initialize Telegram bot.
        
        Args:
            message_handler: Message handler instance
            command_handler: Command handler instance
            token: Optional specific token (if None, will get from archetype)
            archetype: Persona archetype (golden_retriever, tsundere, lawyer, cool_girl, toxic_ex)
        """
        if not TELEGRAM_AVAILABLE:
            raise ImportError("Telegram libraries not installed. Install with: pip install python-telegram-bot")
        
        self.archetype = archetype or "golden_retriever"
        
        # Get token - prioritize passed token, then archetype-specific, then generic
        if token:
            self.token = token
        else:
            # Try to get archetype-specific token
            from constants import get_telegram_bot_token
            self.token = get_telegram_bot_token(self.archetype)
        
        if not self.token:
            raise ValueError(f"TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN_{self.archetype.upper()} environment variable is required")
        
        self.message_handler = message_handler
        self.command_handler = command_handler
        self.application = None
        self.bot = None
        
    async def initialize(self):
        """Initialize Telegram bot application."""
        try:
            # Create application with proper async settings
            self.application = (
                ApplicationBuilder()
                .token(self.token)
                .job_queue(None)
                .concurrent_updates(True)
                .pool_timeout(30)
                .connect_timeout(30)
                .read_timeout(30)
                .write_timeout(30)
                .build()
            )
            self.bot = self.application.bot
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.handle_command))
            self.application.add_handler(CommandHandler("support", self.handle_command))
            self.application.add_handler(CommandHandler("settings", self.handle_command))
            self.application.add_handler(CommandHandler("personality", self.handle_command))
            self.application.add_handler(CommandHandler("summary", self.handle_command))
            self.application.add_handler(CommandHandler("forget", self.handle_command))
            self.application.add_handler(CommandHandler("boundaries", self.handle_command))
            self.application.add_handler(CommandHandler("reset", self.handle_command))
            self.application.add_handler(CommandHandler("schedule", self.handle_command))
            self.application.add_handler(CommandHandler("help", self.handle_command))
            
            # Add message handler
            self.application.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, 
                    self.handle_message
                )
            )
            
            logger.info(f"Telegram bot [{self.archetype}] initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot [{self.archetype}]: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def handle_message(self, update: Update, context: CallbackContext):
        """Handle incoming message with archetype context."""
        try:
            telegram_id = update.effective_user.id
            message_text = update.message.text
            
            if not message_text:
                return
            
            logger.info(f"[{self.archetype}] Received message from {telegram_id}: {message_text[:50]}...")
            
            # Send typing action
            await update.message.chat.send_action(action="typing")
            
            # Pass archetype context to message handler
            response = await self.message_handler.handle(
                telegram_id=telegram_id,
                message_text=message_text,
                archetype=self.archetype
            )
            
            if response:
                await update.message.reply_text(response, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"[{self.archetype}] Error handling message: {e}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                await update.message.reply_text("Oops, something went wrong. Try again?")
            except:
                pass
    
    async def handle_command(self, update: Update, context: CallbackContext):
        """Handle command with archetype context."""
        try:
            telegram_id = update.effective_user.id
            command = update.message.text.split()[0][1:]  # Remove leading slash
            args = update.message.text[len(command)+2:] if len(update.message.text.split()) > 1 else ""
            
            logger.info(f"[{self.archetype}] Received command from {telegram_id}: /{command} {args}")
            
            # Send typing action
            await update.message.chat.send_action(action="typing")
            
            # Pass archetype context to command handler
            response = await self.command_handler.handle(
                telegram_id=telegram_id,
                command=command,
                args=args,
                archetype=self.archetype
            )
            
            if response:
                await update.message.reply_text(response, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"[{self.archetype}] Error handling command: {e}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                await update.message.reply_text("Oops, something went wrong. Try again?")
            except:
                pass
    
    async def start_polling(self):
        """Start polling for updates."""
        if not self.application:
            await self.initialize()
        
        logger.info(f"Starting Telegram bot [{self.archetype}] polling...")
        
        try:
            # Initialize the application
            await self.application.initialize()
            
            # Start polling with error handling
            await self.application.start()
            
            # Get the updater and start polling
            await self.application.updater.start_polling(
                poll_interval=0.5,  # Half second interval
                drop_pending_updates=True,
                timeout=30,
                allowed_updates=Update.ALL_TYPES
            )
            
            logger.info(f"Telegram bot [{self.archetype}] is now polling for updates")
            
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info(f"Telegram bot [{self.archetype}] polling cancelled")
        except Exception as e:
            error_msg = str(e).lower()
            # Check if it's a network/DNS error - don't re-raise these
            if 'network' in error_msg or 'dns' in error_msg or 'name or service not known' in error_msg or 'connecterror' in error_msg:
                logger.error(f"Error in Telegram bot [{self.archetype}] polling: {e}")
                logger.warning(f"Telegram bot [{self.archetype}] cannot connect due to network/DNS error")
                logger.info("This is usually caused by internet connectivity or DNS resolution issues")
                # Don't re-raise network errors - let the application continue
                return
            else:
                logger.error(f"Error in Telegram bot [{self.archetype}] polling: {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise
    
    async def stop(self):
        """Stop the bot gracefully."""
        if self.application:
            try:
                logger.info(f"Stopping Telegram bot [{self.archetype}]...")
                
                if self.application.updater.running:
                    await self.application.updater.stop()
                
                await self.application.stop()
                await self.application.shutdown()
                
                logger.info(f"Telegram bot [{self.archetype}] stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping Telegram bot [{self.archetype}]: {e}")
    
    async def send_message(self, telegram_id: int, message: str) -> bool:
        """Send message to user."""
        try:
            await self.bot.send_message(
                chat_id=telegram_id, 
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"[{self.archetype}] Sent message to {telegram_id}: {message[:50]}...")
            return True
        except TelegramError as e:
            logger.error(f"[{self.archetype}] Failed to send message to {telegram_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"[{self.archetype}] Unexpected error sending message: {e}")
            return False


class TelegramBotManager:
    """Manages multiple Telegram bot instances for different personas."""
    
    def __init__(self, message_handler, command_handler):
        """Initialize bot manager.
        
        Args:
            message_handler: Message handler instance
            command_handler: Command handler instance
        """
        self.message_handler = message_handler
        self.command_handler = command_handler
        self.bots: Dict[str, TelegramBot] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
    
    async def initialize_all(self):
        """Initialize all persona bots."""
        from constants import TELEGRAM_BOTS, TELEGRAM_BOT_TOKENS
        
        for archetype in TELEGRAM_BOTS.keys():
            try:
                bot = TelegramBot(
                    self.message_handler,
                    self.command_handler,
                    archetype=archetype
                )
                
                # Only initialize if token is available
                token = TELEGRAM_BOT_TOKENS.get(archetype, '') or os.getenv('TELEGRAM_BOT_TOKEN', '')
                if token:
                    success = await bot.initialize()
                    if success:
                        self.bots[archetype] = bot
                        logger.info(f"Bot manager: Initialized {archetype} bot")
                    else:
                        logger.warning(f"Bot manager: Failed to initialize {archetype} bot")
                else:
                    logger.warning(f"Bot manager: No token found for {archetype} bot")
                    
            except Exception as e:
                logger.error(f"Bot manager: Error initializing {archetype} bot: {e}")
    
    async def start_all(self):
        """Start polling for all bot instances."""
        logger.info(f"Bot manager: Starting {len(self.bots)} bot instances...")
        
        for archetype, bot in self.bots.items():
            try:
                task = asyncio.create_task(bot.start_polling())
                self.tasks[archetype] = task
                logger.info(f"Bot manager: Started {archetype} bot polling")
            except Exception as e:
                logger.error(f"Bot manager: Error starting {archetype} bot: {e}")
    
    async def stop_all(self):
        """Stop all bot instances."""
        logger.info(f"Bot manager: Stopping all {len(self.bots)} bot instances...")
        
        for archetype, bot in self.bots.items():
            try:
                await bot.stop()
                if archetype in self.tasks:
                    self.tasks[archetype].cancel()
                logger.info(f"Bot manager: Stopped {archetype} bot")
            except Exception as e:
                logger.error(f"Bot manager: Error stopping {archetype} bot: {e}")
        
        self.tasks.clear()
    
    async def send_message(self, telegram_id: int, message: str, archetype: str = "golden_retriever") -> bool:
        """Send message from specific persona bot."""
        bot = self.bots.get(archetype)
        if bot:
            return await bot.send_message(telegram_id, message)
        else:
            logger.warning(f"Bot manager: No bot found for archetype {archetype}")
            return False


async def run_telegram_bots(message_handler, command_handler):
    """Run all Telegram bots."""
    try:
        manager = TelegramBotManager(message_handler, command_handler)
        await manager.initialize_all()
        await manager.start_all()
    except Exception as e:
        logger.error(f"Failed to run Telegram bots: {e}")
        raise


if __name__ == "__main__":
    # This is for testing the Telegram bot separately
    logging.basicConfig(level=logging.INFO)
    
    # Mock handlers for testing
    class MockMessageHandler:
        async def handle(self, telegram_id, message_text, archetype="golden_retriever"):
            await asyncio.sleep(0.5)  # Simulate processing time
            return f"Echo [{archetype}]: {message_text}"
    
    class MockCommandHandler:
        async def handle(self, telegram_id, command, args="", archetype="golden_retriever"):
            await asyncio.sleep(0.3)
            return f"Command [{archetype}]: {command} {args}"
    
    async def main():
        manager = TelegramBotManager(MockMessageHandler(), MockCommandHandler())
        await manager.initialize_all()
        await manager.start_all()
    
    asyncio.run(main())
