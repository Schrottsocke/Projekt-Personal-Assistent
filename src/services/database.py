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


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True)
    user_key = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' oder 'assistant'
    content = Column(Text, nullable=False)
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
    logger.info(f"Datenbank initialisiert: {settings.DATABASE_URL}")


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
