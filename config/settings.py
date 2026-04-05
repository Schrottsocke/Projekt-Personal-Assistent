"""Zentrale Konfiguration - lädt alle Einstellungen aus .env"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Lade .env Datei
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")


def _safe_int(value: str | None, default: int, name: str) -> int:
    """Konvertiert einen String sicher zu int mit Fehlerbehandlung."""
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        logging.getLogger(__name__).warning(
            "Umgebungsvariable '%s' hat ungültigen Wert '%s' – verwende Default %d.",
            name,
            value,
            default,
        )
        return default


def _safe_float(value: str | None, default: float, name: str) -> float:
    """Konvertiert einen String sicher zu float mit Fehlerbehandlung."""
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        logging.getLogger(__name__).warning(
            "Umgebungsvariable '%s' hat ungültigen Wert '%s' – verwende Default %.2f.",
            name,
            value,
            default,
        )
        return default


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
    TELEGRAM_USER_ID_TAAKE: int = _safe_int(os.getenv("TELEGRAM_USER_ID_TAAKE"), -1, "TELEGRAM_USER_ID_TAAKE")
    TELEGRAM_USER_ID_NINA: int = _safe_int(os.getenv("TELEGRAM_USER_ID_NINA"), -1, "TELEGRAM_USER_ID_NINA")

    # AI
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    AI_MODEL_INTENT: str = os.getenv("AI_MODEL_INTENT", "meta-llama/llama-3.1-8b-instruct")
    AI_MODEL_CHAT: str = os.getenv("AI_MODEL_CHAT", "google/gemma-3-27b-it")
    AI_MODEL_FALLBACK_NVIDIA: str = os.getenv("AI_MODEL_FALLBACK_NVIDIA", "nvidia_fallback")
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
    HA_URL: str = os.getenv("HA_URL", "")  # z.B. http://homeassistant.local:8123
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

    # Data directory (JSON-basierte Services: Invoices, Contacts, Inbox, etc.)
    DATA_DIR: Path = BASE_DIR / "data"

    # Document Generation
    DOCUMENTS_DIR: Path = BASE_DIR / "data" / "documents"

    # Storage Backend (local | gdrive)
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")

    # Calendar Cache (TTL in Minuten)
    CALENDAR_CACHE_TTL_MINUTES: int = _safe_int(
        os.getenv("CALENDAR_CACHE_TTL_MINUTES"), 5, "CALENDAR_CACHE_TTL_MINUTES"
    )

    # Memory Search Cache (TTL in Minuten)
    MEMORY_CACHE_TTL_MINUTES: int = _safe_int(os.getenv("MEMORY_CACHE_TTL_MINUTES"), 5, "MEMORY_CACHE_TTL_MINUTES")

    # Mobility (OpenRouteService)
    OPENROUTE_API_KEY: str = os.getenv("OPENROUTE_API_KEY", "")
    HOME_ADDRESS: str = os.getenv("HOME_ADDRESS", "")

    # Email (Gmail) – Check-Intervall in Minuten
    EMAIL_CHECK_INTERVAL_MINUTES: int = _safe_int(
        os.getenv("EMAIL_CHECK_INTERVAL_MINUTES"), 15, "EMAIL_CHECK_INTERVAL_MINUTES"
    )

    # Conversation History Pruning (Einträge älter als N Tage löschen)
    CONVERSATION_HISTORY_DAYS: int = _safe_int(os.getenv("CONVERSATION_HISTORY_DAYS"), 30, "CONVERSATION_HISTORY_DAYS")

    # Dokument-Scan
    DRIVE_DOCUMENTS_FOLDER_ID: str = os.getenv("DRIVE_DOCUMENTS_FOLDER_ID", "")
    OCR_CONFIDENCE_THRESHOLD: int = _safe_int(os.getenv("OCR_CONFIDENCE_THRESHOLD"), 70, "OCR_CONFIDENCE_THRESHOLD")
    SCAN_SAVE_LOCAL: bool = os.getenv("SCAN_SAVE_LOCAL", "true").lower() == "true"
    SCANS_DIR: Path = BASE_DIR / "data" / "scans"

    # REST API (FastAPI)
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "")
    API_PASSWORD_TAAKE: str = os.getenv("API_PASSWORD_TAAKE", "")
    API_PASSWORD_NINA: str = os.getenv("API_PASSWORD_NINA", "")
    API_PORT: int = _safe_int(os.getenv("API_PORT"), 8000, "API_PORT")
    API_CORS_ORIGINS: list = [o.strip() for o in os.getenv("API_CORS_ORIGINS", "").split(",") if o.strip()]

    # Rate Limits (Requests pro Minute)
    RATE_LIMIT_LOGIN: str = os.getenv("RATE_LIMIT_LOGIN", "5/minute")
    RATE_LIMIT_CHAT: str = os.getenv("RATE_LIMIT_CHAT", "30/minute")
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
    RATE_LIMIT_UPLOAD: str = os.getenv("RATE_LIMIT_UPLOAD", "10/minute")
    RATE_LIMIT_WRITE: str = os.getenv("RATE_LIMIT_WRITE", "30/minute")
    API_TOKEN_EXPIRE_DAYS: int = _safe_int(os.getenv("API_TOKEN_EXPIRE_DAYS"), 30, "API_TOKEN_EXPIRE_DAYS")

    # Upload-Limits
    MAX_UPLOAD_SIZE: int = _safe_int(os.getenv("MAX_UPLOAD_SIZE"), 50 * 1024 * 1024, "MAX_UPLOAD_SIZE")
    MAX_UPLOAD_SIZE_MB: int = _safe_int(os.getenv("MAX_UPLOAD_SIZE_MB"), 20, "MAX_UPLOAD_SIZE_MB")

    # Performance Limits
    OCR_TIMEOUT_SECONDS: int = _safe_int(os.getenv("OCR_TIMEOUT_SECONDS"), 30, "OCR_TIMEOUT_SECONDS")
    OCR_MAX_PARALLEL_JOBS: int = _safe_int(os.getenv("OCR_MAX_PARALLEL_JOBS"), 3, "OCR_MAX_PARALLEL_JOBS")
    SCHEDULER_JOB_TIMEOUT_SECONDS: int = _safe_int(
        os.getenv("SCHEDULER_JOB_TIMEOUT_SECONDS"), 10, "SCHEDULER_JOB_TIMEOUT_SECONDS"
    )
    STORAGE_ALERT_THRESHOLD_PERCENT: int = _safe_int(
        os.getenv("STORAGE_ALERT_THRESHOLD_PERCENT"), 80, "STORAGE_ALERT_THRESHOLD_PERCENT"
    )

    # Webhook Deployer
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
    WEBHOOK_PORT: int = _safe_int(os.getenv("WEBHOOK_PORT"), 9000, "WEBHOOK_PORT")
    DEPLOY_BRANCH: str = os.getenv("DEPLOY_BRANCH", "main")

    # GitHub API (Issue-Erstellung aus der WebApp)
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPO: str = os.getenv("GITHUB_REPO", "schrottsocke/projekt-personal-assistent")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Path = BASE_DIR / os.getenv("LOG_FILE", "logs/assistant.log")

    # Observability (Sentry)
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", "development")
    SENTRY_TRACES_SAMPLE_RATE: float = _safe_float(
        os.getenv("SENTRY_TRACES_SAMPLE_RATE"), 0.2, "SENTRY_TRACES_SAMPLE_RATE"
    )

    # Bot Configs
    @classmethod
    def get_bot_configs(cls) -> dict[str, BotConfig]:
        return {
            "taake": BotConfig(
                name="Taake",
                token=cls.BOT_TOKEN_TAAKE,
                user_id=cls.TELEGRAM_USER_ID_TAAKE,
                google_token_path=str(cls.GOOGLE_TOKEN_PATH_TAAKE.relative_to(BASE_DIR)),
            ),
            "nina": BotConfig(
                name="Nina",
                token=cls.BOT_TOKEN_NINA,
                user_id=cls.TELEGRAM_USER_ID_NINA,
                google_token_path=str(cls.GOOGLE_TOKEN_PATH_NINA.relative_to(BASE_DIR)),
            ),
        }

    @classmethod
    def get_allowed_user_ids(cls) -> set[int]:
        return {uid for uid in (cls.TELEGRAM_USER_ID_TAAKE, cls.TELEGRAM_USER_ID_NINA) if uid > 0}

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

        # JWT-Secret: darf nicht leer, nicht der alte Default und mindestens 32 Zeichen
        _insecure_defaults = {
            "",
            "change-me-in-production-please",
            "change-me-generate-with-secrets-token-hex",
            "CHANGE_ME_USE_python_c_import_secrets_print_secrets_token_hex_32",
        }
        if cls.API_SECRET_KEY in _insecure_defaults:
            errors.append(
                "API_SECRET_KEY ist nicht gesetzt oder unsicher. "
                'Generiere ein Secret: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        elif len(cls.API_SECRET_KEY) < 32:
            errors.append("API_SECRET_KEY muss mindestens 32 Zeichen lang sein (aktuell: %d)" % len(cls.API_SECRET_KEY))

        return errors

    def get_system_prompt(self, user_key: str = None) -> str:
        """Gibt den personalisierten System-Prompt fuer einen User zurueck."""
        prompts = {
            "taake": "Du bist ein persoenlicher KI-Assistent fuer Taake. Du bist hilfsbereit, praezise und effizient. Antworte auf Deutsch.",
            "nina": "Du bist ein persoenlicher KI-Assistent fuer Nina. Du bist einfuehlsam, organisiert und unterstuetzend. Antworte auf Deutsch.",
        }
        default = "Du bist ein hilfreicher persoenlicher KI-Assistent. Antworte auf Deutsch."
        if not user_key:
            return default
        return prompts.get(user_key.lower(), default)


settings = Settings()
