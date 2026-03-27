"""Gemeinsame Fixtures für alle Tests."""

import pytest

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
