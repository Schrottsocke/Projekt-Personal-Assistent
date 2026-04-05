"""Fixtures für Integration-Tests: TestClient mit echten DB-Services + Mock-External.

Shared external-API mocks (mock_telegram_bot_api, mock_google_calendar_api,
mock_openrouter_api) are inherited from the root tests/conftest.py.
The autouse _block_httpx_requests fixture from tests/conftest.py prevents any
real network calls across all tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from config.settings import Settings

TEST_PASSWORD = "test-password-123"


def _setup_test_db():
    """Erstellt eine frische in-memory SQLite DB und setzt die globalen Variablen."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    import src.services.database as db_mod

    # Alte DB aufräumen
    if db_mod._engine is not None:
        db_mod._engine.dispose()

    # StaticPool: alle Connections teilen sich dieselbe in-memory DB
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db_mod._engine = engine
    db_mod._SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    db_mod.Base.metadata.create_all(bind=engine)

    return engine


def _reset_db():
    """Setzt die globalen DB-Variablen zurück."""
    import src.services.database as db_mod

    if db_mod._engine is not None:
        db_mod._engine.dispose()
    db_mod._engine = None
    db_mod._SessionLocal = None


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    """Settings für Integration-Tests patchen."""
    monkeypatch.setattr(Settings, "API_SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")
    monkeypatch.setattr(Settings, "API_TOKEN_EXPIRE_DAYS", 30)
    monkeypatch.setattr(Settings, "API_PASSWORD_TAAKE", TEST_PASSWORD)
    monkeypatch.setattr(Settings, "API_PASSWORD_NINA", TEST_PASSWORD)
    monkeypatch.setattr(Settings, "API_CORS_ORIGINS", ["http://localhost"])
    monkeypatch.setattr(Settings, "DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setattr(Settings, "RATE_LIMIT_DEFAULT", "200/minute")
    monkeypatch.setattr(Settings, "RATE_LIMIT_LOGIN", "200/minute")
    monkeypatch.setattr(Settings, "RATE_LIMIT_CHAT", "200/minute")
    monkeypatch.setattr(Settings, "RATE_LIMIT_WRITE", "200/minute")
    monkeypatch.setattr(Settings, "RATE_LIMIT_UPLOAD", "200/minute")
    monkeypatch.setattr(Settings, "TIMEZONE", "Europe/Berlin")


@pytest.fixture
def client():
    """TestClient mit echten DB-Services und gemockten External-Services."""
    import api.dependencies as deps

    # Frische in-memory DB erstellen
    _setup_test_db()

    # Echte DB-backed Services
    from src.services.task_service import TaskService
    from src.services.shopping_service import ShoppingService
    from src.services.notification_service import NotificationService
    from src.services.database import get_db

    task_svc = TaskService()
    task_svc._db = get_db()

    shopping_svc = ShoppingService()

    notif_svc = NotificationService()
    notif_svc._db = get_db()

    # Mock-Services für externe APIs
    ai_svc = AsyncMock()
    ai_svc.process_message = AsyncMock(return_value="Mocked AI response")

    memory_svc = AsyncMock()
    calendar_svc = MagicMock()
    calendar_svc.is_connected = MagicMock(return_value=False)
    calendar_svc.get_todays_events = AsyncMock(return_value=[])
    calendar_svc.get_upcoming_events = AsyncMock(return_value=[])
    calendar_svc.create_event = AsyncMock(return_value={"id": "mock-event-1"})

    reminder_svc = AsyncMock()
    reminder_svc.get_todays_reminders = AsyncMock(return_value=[])
    reminder_svc.get_active_reminders = AsyncMock(return_value=[])

    chefkoch_svc = AsyncMock()
    chefkoch_svc.search_recipes = AsyncMock(return_value=[])
    chefkoch_svc.get_recipe = AsyncMock(return_value=None)

    email_svc = MagicMock()
    email_svc.is_connected = MagicMock(return_value=False)
    email_svc.get_unread_count = AsyncMock(return_value=0)

    drive_svc = AsyncMock()
    notes_svc = AsyncMock()

    ocr_svc = MagicMock()
    ocr_svc.extract_text = AsyncMock(
        return_value={"text": "Mocked OCR", "confidence": 95.0, "method": "mock", "words_data": None}
    )

    pdf_svc = MagicMock()

    from src.services.storage_service import StorageService

    storage_svc = StorageService(drive_service=drive_svc)

    bot_shim = MagicMock()
    bot_shim.ai_service = ai_svc

    # Services in den Container injizieren
    deps._svc = {
        "ai": ai_svc,
        "memory": memory_svc,
        "calendar": calendar_svc,
        "notes": notes_svc,
        "reminder": reminder_svc,
        "task": task_svc,
        "shopping": shopping_svc,
        "chefkoch": chefkoch_svc,
        "email": email_svc,
        "drive": drive_svc,
        "notification": notif_svc,
        "ocr": ocr_svc,
        "pdf": pdf_svc,
        "storage": storage_svc,
        "bot_shim": bot_shim,
    }

    with patch("api.dependencies.startup", new_callable=AsyncMock):
        from api.main import app
        from fastapi.testclient import TestClient

        yield TestClient(app)

    # Cleanup
    deps._svc = {}
    _reset_db()


def _ensure_user_profile(user_key: str) -> None:
    """Stellt sicher, dass ein UserProfile in der Test-DB existiert."""
    from src.services.database import UserProfile, get_db

    with get_db()() as db:
        existing = db.query(UserProfile).filter_by(user_key=user_key).first()
        if not existing:
            db.add(UserProfile(user_key=user_key))
            db.flush()


@pytest.fixture
def auth_headers(client):
    """Login als 'taake' und Bearer-Token-Header zurückgeben."""
    _ensure_user_profile("taake")
    resp = client.post("/auth/login", json={"username": "taake", "password": TEST_PASSWORD})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_nina(client):
    """Login als 'nina' und Bearer-Token-Header zurückgeben."""
    _ensure_user_profile("nina")
    resp = client.post("/auth/login", json={"username": "nina", "password": TEST_PASSWORD})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
