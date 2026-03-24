"""Zentrale Konfiguration - lädt alle Einstellungen aus .env"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Lade .env Datei
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")


class BotConfig:
    """Konfiguration für einen einzelnen Bot/User"""
    def __init__(self, name: str, token: str, user_id: int, google_token_path: str):
        self.name = name
        self.token = token
        self.user_id = user_id
        self.google_token_path = Path(BASE_DIR / google_token_path)


class Settings:
    BASE_DIR: Path = BASE_DIR

    # Telegram Bots
    BOT_TOKEN_TAAKE: str = os.getenv("BOT_TOKEN_TAAKE", "")
    BOT_TOKEN_NINA: str = os.getenv("BOT_TOKEN_NINA", "")
    TELEGRAM_USER_ID_TAAKE: int = int(os.getenv("TELEGRAM_USER_ID_TAAKE", "0"))
    TELEGRAM_USER_ID_NINA: int = int(os.getenv("TELEGRAM_USER_ID_NINA", "0"))

    # AI
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    AI_MODEL: str = os.getenv("AI_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    AI_MODEL_FALLBACK: str = os.getenv("AI_MODEL_FALLBACK", "mistralai/mistral-7b-instruct:free")

    # Voice / Whisper (Groq – kostenlos, 7.200 Sek./Tag)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-large-v3")

    # Vision (Foto-Analyse via OpenRouter – kostenlos)
    VISION_MODEL: str = os.getenv("VISION_MODEL", "google/gemini-2.0-flash-lite-001:free")

    # Spotify (optional – nur mit Premium)
    SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    SPOTIFY_REDIRECT_URI: str = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

    # Smart Home – Home Assistant (optional)
    HA_URL: str = os.getenv("HA_URL", "")           # z.B. http://homeassistant.local:8123
    HA_TOKEN: str = os.getenv("HA_TOKEN", "")

    # Web Search
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # Memory
    MEMORY_MODE: str = os.getenv("MEMORY_MODE", "local")
    MEM0_API_KEY: str = os.getenv("MEM0_API_KEY", "")

    # Google Calendar
    GOOGLE_CREDENTIALS_PATH: Path = BASE_DIR / os.getenv("GOOGLE_CREDENTIALS_PATH", "config/google_credentials.json")
    GOOGLE_TOKEN_PATH_TAAKE: Path = BASE_DIR / os.getenv("GOOGLE_TOKEN_PATH_TAAKE", "data/google_token_taake.json")
    GOOGLE_TOKEN_PATH_NINA: Path = BASE_DIR / os.getenv("GOOGLE_TOKEN_PATH_NINA", "data/google_token_nina.json")

    # Scheduler
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Berlin")
    MORNING_BRIEFING_TIME: str = os.getenv("MORNING_BRIEFING_TIME", "08:00")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/assistant.db")

    # Document Generation
    DOCUMENTS_DIR: Path = BASE_DIR / "data" / "documents"

    # Calendar Cache (TTL in Minuten)
    CALENDAR_CACHE_TTL_MINUTES: int = int(os.getenv("CALENDAR_CACHE_TTL_MINUTES", "5"))

    # Conversation History Pruning (Einträge älter als N Tage löschen)
    CONVERSATION_HISTORY_DAYS: int = int(os.getenv("CONVERSATION_HISTORY_DAYS", "30"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Path = BASE_DIR / os.getenv("LOG_FILE", "logs/assistant.log")

    # Bot Configs
    @classmethod
    def get_bot_configs(cls) -> dict[str, BotConfig]:
        return {
            "taake": BotConfig(
                name="Taake",
                token=cls.BOT_TOKEN_TAAKE,
                user_id=cls.TELEGRAM_USER_ID_TAAKE,
                google_token_path=str(cls.GOOGLE_TOKEN_PATH_TAAKE.relative_to(BASE_DIR))
            ),
            "nina": BotConfig(
                name="Nina",
                token=cls.BOT_TOKEN_NINA,
                user_id=cls.TELEGRAM_USER_ID_NINA,
                google_token_path=str(cls.GOOGLE_TOKEN_PATH_NINA.relative_to(BASE_DIR))
            ),
        }

    @classmethod
    def get_allowed_user_ids(cls) -> set[int]:
        return {cls.TELEGRAM_USER_ID_TAAKE, cls.TELEGRAM_USER_ID_NINA}

    @classmethod
    def validate(cls) -> list[str]:
        """Gibt Liste von Fehlern zurück wenn Konfiguration unvollständig ist"""
        errors = []
        if not cls.BOT_TOKEN_TAAKE:
            errors.append("BOT_TOKEN_TAAKE fehlt in .env")
        if not cls.BOT_TOKEN_NINA:
            errors.append("BOT_TOKEN_NINA fehlt in .env")
        if not cls.TELEGRAM_USER_ID_TAAKE:
            errors.append("TELEGRAM_USER_ID_TAAKE fehlt in .env")
        if not cls.TELEGRAM_USER_ID_NINA:
            errors.append("TELEGRAM_USER_ID_NINA fehlt in .env")
        if not cls.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY fehlt in .env")
        return errors


settings = Settings()
