# backend/config/settings.py
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    # Database & Infrastructure
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost/companion_bot"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "your-secret-key"
    
    # API & Server
    environment: str = "development"
    api_port: int = 8001
    log_level: str = "INFO"
    
    # Authentication & Keys
    llm_api_key: str
    telegram_bot_token: str
    
    # LLM Configuration
    openai_model: str = "gpt-4"
    llm_mode: str = "completion"  # completion or assistant
    openai_assistant_id: str = ""  # OpenAI Assistant ID (required if llm_mode=assistant)
    
    # Chat Logging
    enable_chat_logging: bool = True  # Enable chat logging
    chat_logs_dir: str = "logs/chats"  # Directory for chat logs
    
    # Telegram Bot Usernames for each archetype (for deep links)
    telegram_bot_golden_retriever: str = "golden_retriever_bot"
    telegram_bot_tsundere: str = "tsundere_dot_bot"
    telegram_bot_lawyer: str = "lawyer_dot_bot"
    telegram_bot_cool_girl: str = "cool_girl_dot_bot"
    telegram_bot_toxic_ex: str = "toxicEx_bot"
    
    # Telegram Bot Tokens for each archetype (for receiving messages)
    telegram_bot_token_golden_retriever: str = ""
    telegram_bot_token_tsundere: str = ""
    telegram_bot_token_lawyer: str = ""
    telegram_bot_token_cool_girl: str = ""
    telegram_bot_token_toxic_ex: str = ""
    
    # Proactive Features Configuration
    proactive_check_interval_minutes: int = 5  # How often to check for proactive messages
    
    # Time-based greeting hours (24-hour format, 0-23)
    greeting_morning_start_hour: int = 6
    greeting_morning_end_hour: int = 12
    greeting_afternoon_start_hour: int = 12
    greeting_afternoon_end_hour: int = 17
    greeting_evening_start_hour: int = 17
    greeting_evening_end_hour: int = 22
    greeting_night_start_hour: int = 22
    greeting_night_end_hour: int = 6
    
    model_config = ConfigDict(env_file=".env")

settings = Settings()