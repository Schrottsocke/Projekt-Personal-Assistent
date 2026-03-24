"""
SQLAlchemy Datenbankmodelle und Session-Management.
Speichert: Notizen, Erinnerungen, User-Profile, Konversations-History.
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
