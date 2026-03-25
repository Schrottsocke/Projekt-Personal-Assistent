"""
SQLAlchemy Datenbankmodelle und Session-Management.
Speichert: Notizen, Erinnerungen, User-Profile, Konversations-History, Proposals.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Float,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config.settings import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), unique=True, nullable=False)
    is_onboarded = Column(Boolean, default=False)
    nickname = Column(String(100), nullable=True)
    communication_style = Column(String(50), default="casual")
    interests = Column(Text, nullable=True)
    chat_id = Column(String(50), nullable=True)  # Telegram Chat-ID für Proaktive Nachrichten
    # Trust-System: Komma-getrennte Proposal-Typen die auto-approved werden
    auto_approve_types = Column(Text, default="timer_create")
    # Persönlichkeitsprofil (Onboarding 2.0)
    work_start = Column(String(10), nullable=True)   # z.B. "09:00"
    work_end = Column(String(10), nullable=True)     # z.B. "18:00"
    quiet_start = Column(String(10), nullable=True)  # z.B. "22:00"
    quiet_end = Column(String(10), nullable=True)    # z.B. "07:00"
    focus_time = Column(String(20), nullable=True)   # "morgen" / "mittag" / "abend"
    week_structure = Column(Text, nullable=True)     # Freitext
    # Fokus-Modus: bis wann aktiv (None = kein Fokus-Modus)
    focus_mode_until = Column(DateTime, nullable=True)
    # TTS: Sprachantworten aktiviert (opt-in)
    tts_enabled = Column(Boolean, default=False)
    # Spotify: OAuth2-Token als JSON
    spotify_token_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    is_shared = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    chat_id = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    remind_at = Column(DateTime, nullable=False)
    is_sent = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Proposal(Base):
    """
    Vorschlag zur manuellen Genehmigung (Human-in-the-Loop).
    Status: pending → approved/rejected
    """
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True)
    proposal_type = Column(String(50), nullable=False)  # calendar_create, reminder_create, etc.
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=False)  # JSON-kodierte Aktionsparameter
    user_key = Column(String(50), nullable=False)  # Für wen ist der Vorschlag
    created_by = Column(String(50), nullable=False)  # 'user', 'bot_taake', 'bot_nina', 'ai'
    status = Column(String(20), default="pending")  # pending, approved, rejected
    telegram_message_id = Column(String(50), nullable=True)  # Für späteres Editieren
    telegram_chat_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)


class Task(Base):
    """Aufgaben/To-Do mit Status-Tracking und Cross-Bot-Zuweisung."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)       # Besitzer der Aufgabe
    assigned_by = Column(String(50), nullable=True)     # user_key des Zuweisers (cross-bot)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(10), default="medium")     # high / medium / low
    due_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="open")         # open / in_progress / done
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MemoryFact(Base):
    """
    Gespeicherte Fakten aus Gesprächen mit Bestätigungs-Tracking.
    Inspiriert vom JARVIS Continuous-Learning / Instinct-System.
    Fakten die öfter extrahiert oder bestätigt werden, bekommen höhere Konfidenz.
    """
    __tablename__ = "memory_facts"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    confirmation_count = Column(Integer, default=1)   # Wie oft wurde dieser Fakt extrahiert
    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' oder 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ShoppingItem(Base):
    """Einkaufsliste-Eintrag. Eine Liste pro User (kein separates Listen-Model)."""
    __tablename__ = "shopping_items"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    quantity = Column(String(50), nullable=True)   # z.B. "500", "2", "1 Bund"
    unit = Column(String(30), nullable=True)       # z.B. "g", "Stück", "ml"
    category = Column(String(50), nullable=True)   # z.B. "Gemüse", "Milchprodukte"
    checked = Column(Boolean, default=False)
    source = Column(String(100), nullable=True)    # z.B. "chefkoch:12345" oder "manual"
    created_at = Column(DateTime, default=datetime.utcnow)


class ScannedDocument(Base):
    """Gespeichertes Scan-Ergebnis für die /dokumente-Historie."""
    __tablename__ = "scanned_documents"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    doc_type = Column(String(100), nullable=False)       # Rechnung, Brief, etc.
    filename = Column(String(200), nullable=False)       # YYYY-MM-DD_Typ.pdf
    drive_link = Column(String(500), nullable=True)      # Drive webViewLink
    drive_file_id = Column(String(100), nullable=True)   # Drive File-ID
    summary = Column(Text, nullable=True)
    sender = Column(String(200), nullable=True)
    amount = Column(String(50), nullable=True)           # Betrag falls Rechnung
    scanned_at = Column(DateTime, default=datetime.utcnow)


class SavedRecipe(Base):
    """Gespeichertes / favorisiertes Rezept (aus Chefkoch-Suche)."""
    __tablename__ = "saved_recipes"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    chefkoch_id = Column(String(50), nullable=False)
    title = Column(String(300), nullable=False)
    image_url = Column(String(500), nullable=True)
    servings = Column(Integer, default=4)
    prep_time = Column(Integer, default=0)        # Minuten
    cook_time = Column(Integer, default=0)        # Minuten
    difficulty = Column(String(50), nullable=True)
    ingredients_json = Column(Text, nullable=True)  # JSON-Array
    is_favorite = Column(Boolean, default=False)
    source_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MealPlanEntry(Base):
    """Wochenplan-Eintrag: Rezept zu Tag + Mahlzeit."""
    __tablename__ = "meal_plan_entries"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    planned_date = Column(String(10), nullable=False)      # YYYY-MM-DD
    recipe_chefkoch_id = Column(String(50), nullable=True)
    recipe_title = Column(String(300), nullable=False)
    recipe_image_url = Column(String(500), nullable=True)
    meal_type = Column(String(20), default="dinner")       # breakfast|lunch|dinner
    servings = Column(Integer, default=4)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Engine & Session Setup
_engine = None
_SessionLocal = None


def init_db():
    global _engine, _SessionLocal

    _engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    )
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)

    # Tabellen erstellen
    Base.metadata.create_all(bind=_engine)

    # Migrations: neue Spalten zu bestehenden Tabellen hinzufügen (SQLite)
    if "sqlite" in settings.DATABASE_URL:
        with _engine.connect() as conn:
            for col_sql in [
                "ALTER TABLE user_profiles ADD COLUMN focus_mode_until DATETIME",
                "ALTER TABLE user_profiles ADD COLUMN tts_enabled BOOLEAN DEFAULT 0",
                "ALTER TABLE user_profiles ADD COLUMN spotify_token_json TEXT",
            ]:
                try:
                    conn.execute(__import__("sqlalchemy").text(col_sql))
                    conn.commit()
                except Exception:
                    pass  # Spalte existiert bereits

    logger.info(f"Datenbank initialisiert: {settings.DATABASE_URL}")


def prune_conversation_history(days: int = 30) -> int:
    """Löscht Conversation-History-Einträge älter als 'days' Tage.
    Returns: Anzahl gelöschter Zeilen."""
    from datetime import timedelta
    import sqlalchemy

    if _engine is None:
        return 0

    cutoff = datetime.utcnow() - timedelta(days=days)
    with _engine.connect() as conn:
        result = conn.execute(
            sqlalchemy.text(
                "DELETE FROM conversation_history WHERE created_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
        conn.commit()
        return result.rowcount


def get_db():
    """Gibt einen Session-Factory-Context-Manager zurück."""
    if _SessionLocal is None:
        init_db()
    return _session_context


@contextmanager
def _session_context():
    session: Session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
