"""Gemeinsame Fixtures für alle Tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Test-Secrets setzen BEVOR Settings importiert wird
TEST_SECRET_KEY = "test-secret-key-that-is-at-least-32-characters-long"
TEST_PASSWORD = "test-password-123"


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    """Setzt Test-Umgebungsvariablen für jeden Test."""
    monkeypatch.setenv("API_SECRET_KEY", TEST_SECRET_KEY)
    monkeypatch.setenv("API_PASSWORD_TAAKE", TEST_PASSWORD)
    monkeypatch.setenv("API_PASSWORD_NINA", TEST_PASSWORD)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("BOT_TOKEN_TAAKE", "fake-token-taake")
    monkeypatch.setenv("BOT_TOKEN_NINA", "fake-token-nina")
    monkeypatch.setenv("TELEGRAM_USER_ID_TAAKE", "12345")
    monkeypatch.setenv("TELEGRAM_USER_ID_NINA", "67890")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-openrouter-key")


@pytest.fixture
def db_session():
    """In-Memory SQLite Session für DB-Tests."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.services.database import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def settings_fresh(monkeypatch):
    """Frische Settings-Instanz mit Test-Werten.

    Achtung: Settings ist eine Klasse mit Klassenattributen,
    die beim Import gesetzt werden. Wir patchen die Attribute direkt.
    """
    from config.settings import Settings

    monkeypatch.setattr(Settings, "API_SECRET_KEY", TEST_SECRET_KEY)
    monkeypatch.setattr(Settings, "API_PASSWORD_TAAKE", TEST_PASSWORD)
    monkeypatch.setattr(Settings, "API_PASSWORD_NINA", TEST_PASSWORD)
    monkeypatch.setattr(Settings, "DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setattr(Settings, "BOT_TOKEN_TAAKE", "fake-token-taake")
    monkeypatch.setattr(Settings, "BOT_TOKEN_NINA", "fake-token-nina")
    monkeypatch.setattr(Settings, "TELEGRAM_USER_ID_TAAKE", 12345)
    monkeypatch.setattr(Settings, "TELEGRAM_USER_ID_NINA", 67890)
    monkeypatch.setattr(Settings, "OPENROUTER_API_KEY", "fake-openrouter-key")
    return Settings


# ---------------------------------------------------------------------------
# Shared External-API Mocks (prevent real network calls in all test scopes)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _block_httpx_requests(monkeypatch):
    """Blockiert echte httpx-Requests in allen Tests (Safety-Net)."""

    async def _blocked_send(*args, **kwargs):
        raise RuntimeError("Real network call blocked by test fixture")

    try:
        import httpx

        monkeypatch.setattr(httpx.AsyncClient, "send", _blocked_send)
    except ImportError:
        pass


@pytest.fixture
def mock_telegram_bot_api():
    """Mock für die Telegram Bot API – verhindert echte Netzwerkaufrufe."""
    bot = MagicMock()
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=1))
    bot.send_photo = AsyncMock(return_value=MagicMock(message_id=2))
    bot.send_document = AsyncMock(return_value=MagicMock(message_id=3))
    bot.delete_message = AsyncMock(return_value=True)
    bot.get_me = AsyncMock(
        return_value=MagicMock(id=123456, is_bot=True, first_name="TestBot", username="test_bot")
    )
    return bot


@pytest.fixture
def mock_google_calendar_api():
    """Mock für die Google Calendar API – kein echter Google-Zugriff."""
    cal = MagicMock()
    cal.is_connected = MagicMock(return_value=True)
    cal.get_todays_events = AsyncMock(return_value=[])
    cal.get_upcoming_events = AsyncMock(return_value=[])
    cal.create_event = AsyncMock(return_value={"id": "mock-event-id", "status": "confirmed"})
    cal.delete_event = AsyncMock(return_value=True)
    cal.update_event = AsyncMock(return_value={"id": "mock-event-id", "status": "confirmed"})
    return cal


@pytest.fixture
def mock_openrouter_api():
    """Mock für die OpenRouter (AI) API – verhindert echte LLM-Aufrufe."""
    ai = AsyncMock()
    ai.process_message = AsyncMock(return_value="Mocked AI response")
    ai._detect_intent = AsyncMock(return_value={"intent": "chat"})
    ai._complete = AsyncMock(return_value="Mocked completion")
    ai.transcribe_voice = AsyncMock(return_value="Mocked transcription")
    return ai
