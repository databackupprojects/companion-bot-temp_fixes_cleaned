# backend/utils/chat_logger.py - Chat Logging Utility
"""
Chat logging utility for storing user conversations
Logs are organized by user_id/bot_id/YYYY-MM-DD.log
"""
import os
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
import json
from config.settings import settings

logger = logging.getLogger(__name__)

class ChatLogger:
    """Utility class for logging user-bot conversations."""
    
    def __init__(self):
        """Initialize chat logger."""
        self.enabled = settings.enable_chat_logging
        self.logs_dir = settings.chat_logs_dir
        
        if self.enabled:
            # Create logs directory if it doesn't exist
            Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Chat logging enabled. Logs directory: {self.logs_dir}")
        else:
            logger.info("ℹ️  Chat logging is disabled")
    
    def log_conversation(
        self,
        user_id: str,
        username: str,
        bot_id: str,
        user_message: str,
        bot_response: str,
        message_type: str = "reactive",
        source: str = "web"
    ) -> bool:
        """
        Log a conversation exchange.
        
        Args:
            user_id: User ID
            username: Username
            bot_id: Bot ID (archetype)
            user_message: User's message
            bot_response: Bot's response
            message_type: Type of message (reactive/proactive)
            source: Source of message (web/telegram)
        
        Returns:
            bool: True if logged successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Create user/bot directory structure with username_userid format
            user_folder = f"{username}_{user_id}"
            user_bot_dir = Path(self.logs_dir) / user_folder / str(bot_id)
            user_bot_dir.mkdir(parents=True, exist_ok=True)
            
            # Create log file with current date
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = user_bot_dir / f"{date_str}.log"
            
            # Prepare log entry (simplified structure)
            timestamp = datetime.utcnow().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "user_message": user_message,
                "bot_response": bot_response,
                "message_type": message_type,
                "source": source
            }
            
            # Read existing logs or create new array
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        logs = []
            else:
                logs = []
            
            # Append new entry
            logs.append(log_entry)
            
            # Write back to daily file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            # Also append to combined log file
            combined_file = user_bot_dir / "combined.log"
            if combined_file.exists():
                with open(combined_file, 'r', encoding='utf-8') as f:
                    try:
                        combined_logs = json.load(f)
                    except json.JSONDecodeError:
                        combined_logs = []
            else:
                combined_logs = []
            
            combined_logs.append(log_entry)
            
            with open(combined_file, 'w', encoding='utf-8') as f:
                json.dump(combined_logs, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error logging conversation: {e}", exc_info=True)
            return False
    
    def log_proactive_message(
        self,
        user_id: str,
        username: str,
        bot_id: str,
        bot_message: str,
        source: str = "telegram"
    ) -> bool:
        """
        Log a proactive message from bot.
        
        Args:
            user_id: User ID
            username: Username
            bot_id: Bot ID (archetype)
            bot_message: Proactive message from bot
            source: Source of message (web/telegram)
        
        Returns:
            bool: True if logged successfully
        """
        if not self.enabled:
            return False
        
        try:
            # Create user/bot directory structure with username_userid format
            user_folder = f"{username}_{user_id}"
            user_bot_dir = Path(self.logs_dir) / user_folder / str(bot_id)
            user_bot_dir.mkdir(parents=True, exist_ok=True)
            
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = user_bot_dir / f"{date_str}.log"
            
            timestamp = datetime.utcnow().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "bot_message": bot_message,
                "message_type": "proactive",
                "source": source
            }
            
            # Read existing logs or create new array
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        logs = []
            else:
                logs = []
            
            # Append new entry
            logs.append(log_entry)
            
            # Write back to daily file
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            # Also append to combined log file
            combined_file = user_bot_dir / "combined.log"
            if combined_file.exists():
                with open(combined_file, 'r', encoding='utf-8') as f:
                    try:
                        combined_logs = json.load(f)
                    except json.JSONDecodeError:
                        combined_logs = []
            else:
                combined_logs = []
            
            combined_logs.append(log_entry)
            
            with open(combined_file, 'w', encoding='utf-8') as f:
                json.dump(combined_logs, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error logging proactive message: {e}", exc_info=True)
            return False
    
    def get_conversation_history(
        self,
        user_id: str,
        username: str,
        bot_id: str,
        date: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """
        Retrieve conversation history from logs.
        
        Args:
            user_id: User ID
            username: Username
            bot_id: Bot ID (archetype)
            date: Optional date string (YYYY-MM-DD), defaults to today
            limit: Maximum number of entries to return
        
        Returns:
            list: List of conversation entries
        """
        if not self.enabled:
            return []
        
        try:
            if not date:
                date = datetime.utcnow().strftime("%Y-%m-%d")
            
            user_folder = f"{username}_{user_id}"
            log_file = Path(self.logs_dir) / user_folder / str(bot_id) / f"{date}.log"
            
            if not log_file.exists():
                return []
            
            with open(log_file, 'r', encoding='utf-8') as f:
                try:
                    conversations = json.load(f)
                except json.JSONDecodeError:
                    conversations = []
            
            # Return most recent entries up to limit
            return conversations[-limit:] if conversations else []
            
        except Exception as e:
            logger.error(f"❌ Error retrieving conversation history: {e}", exc_info=True)
            return []
    
    def get_user_stats(self, user_id: str, bot_id: Optional[str] = None) -> dict:
        """
        Get statistics about user's conversations.
        
        Args:
            user_id: User ID
            bot_id: Optional bot ID to filter by specific bot
        
        Returns:
            dict: Statistics dictionary
        """
        if not self.enabled:
            return {"enabled": False}
        
        try:
            user_dir = Path(self.logs_dir) / str(user_id)
            
            if not user_dir.exists():
                return {
                    "enabled": True,
                    "total_conversations": 0,
                    "bots": []
                }
            
            stats = {
                "enabled": True,
                "total_conversations": 0,
                "bots": []
            }
            
            # If bot_id specified, only count that bot
            if bot_id:
                bot_dir = user_dir / str(bot_id)
                if bot_dir.exists():
                    count = self._count_conversations_in_dir(bot_dir)
                    stats["total_conversations"] = count
                    stats["bots"].append({
                        "bot_id": str(bot_id),
                        "conversations": count
                    })
            else:
                # Count all bots
                for bot_dir in user_dir.iterdir():
                    if bot_dir.is_dir():
                        count = self._count_conversations_in_dir(bot_dir)
                        stats["total_conversations"] += count
                        stats["bots"].append({
                            "bot_id": bot_dir.name,
                            "conversations": count
                        })
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting user stats: {e}", exc_info=True)
            return {"enabled": True, "error": str(e)}
    
    def _count_conversations_in_dir(self, directory: Path) -> int:
        """Count total conversation entries in a directory."""
        count = 0
        for log_file in directory.glob("*.log"):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                    count += len(logs) if isinstance(logs, list) else 0
            except Exception:
                continue
        return count


# Global chat logger instance
chat_logger = ChatLogger()
