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
    TELEGRAM_USER_ID_TAAKE: int = int(os.getenv("TELEGRAM_USER_ID_TAAKE") or "0")
    TELEGRAM_USER_ID_NINA: int = int(os.getenv("TELEGRAM_USER_ID_NINA") or "0")

    # AI
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    AI_MODEL: str = os.getenv("AI_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    AI_MODEL_FALLBACK: str = os.getenv("AI_MODEL_FALLBACK", "nvidia_fallback")
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "moonshotai/kimi-k2.5")

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

    # Mobility (OpenRouteService)
    OPENROUTE_API_KEY: str = os.getenv("OPENROUTE_API_KEY", "")
    HOME_ADDRESS: str = os.getenv("HOME_ADDRESS", "")

    # Email (Gmail) – Check-Intervall in Minuten
    EMAIL_CHECK_INTERVAL_MINUTES: int = int(os.getenv("EMAIL_CHECK_INTERVAL_MINUTES", "15"))

    # Conversation History Pruning (Einträge älter als N Tage löschen)
    CONVERSATION_HISTORY_DAYS: int = int(os.getenv("CONVERSATION_HISTORY_DAYS", "30"))

    # Dokument-Scan
    DRIVE_DOCUMENTS_FOLDER_ID: str = os.getenv("DRIVE_DOCUMENTS_FOLDER_ID", "")
    OCR_CONFIDENCE_THRESHOLD: int = int(os.getenv("OCR_CONFIDENCE_THRESHOLD", "70"))
    SCAN_SAVE_LOCAL: bool = os.getenv("SCAN_SAVE_LOCAL", "true").lower() == "true"
    SCANS_DIR: Path = BASE_DIR / "data" / "scans"

    # REST API (FastAPI)
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "change-me-in-production-please")
    API_PASSWORD_TAAKE: str = os.getenv("API_PASSWORD_TAAKE", "")
    API_PASSWORD_NINA: str = os.getenv("API_PASSWORD_NINA", "")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_CORS_ORIGINS: list = os.getenv("API_CORS_ORIGINS", "*").split(",")
    API_TOKEN_EXPIRE_DAYS: int = int(os.getenv("API_TOKEN_EXPIRE_DAYS", "30"))

    # Webhook Deployer
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "9000"))
    DEPLOY_BRANCH: str = os.getenv("DEPLOY_BRANCH", "claude/dual-personal-assistants-0Uqna")

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
        if cls.TELEGRAM_USER_ID_TAAKE <= 0:
            errors.append("TELEGRAM_USER_ID_TAAKE fehlt oder ungültig in .env (muss > 0 sein)")
        if cls.TELEGRAM_USER_ID_NINA <= 0:
            errors.append("TELEGRAM_USER_ID_NINA fehlt oder ungültig in .env (muss > 0 sein)")
        if not cls.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY fehlt in .env")
        return errors



    def get_system_prompt(self, user_key: str = None) -> str:
        """Gibt den personalisierten System-Prompt fuer einen User zurueck."""
        prompts = {
            'taake': 'Du bist ein persoenlicher KI-Assistent fuer Taake. Du bist hilfsbereit, praezise und effizient. Antworte auf Deutsch.',
            'nina': 'Du bist ein persoenlicher KI-Assistent fuer Nina. Du bist einfuehlsam, organisiert und unterstuetzend. Antworte auf Deutsch.',
        }
        default = 'Du bist ein hilfreicher persoenlicher KI-Assistent. Antworte auf Deutsch.'
        if not user_key:
            return default
        return prompts.get(user_key.lower(), default)

settings = Settings()
