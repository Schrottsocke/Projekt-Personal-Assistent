"""
BotMemoryService: Bot-spezifisches Gedaechtnis (Telegram Bots).

Erweitert BaseMemoryService um:
- SQLite-basiertes Fact-Tracking mit Konfidenz-Zaehler
- Onboarding-Status (mark_onboarded / is_onboarded)
- Conversation-Turn-Speicherung
"""

import logging
from sqlalchemy.exc import SQLAlchemyError
from src.memory.base_memory_service import BaseMemoryService

logger = logging.getLogger(__name__)


class BotMemoryService(BaseMemoryService):
    """
    Memory Service fuer Telegram Bots (Taake & Nina).
    Erbt mem0-Logik von BaseMemoryService, fuegt SQLite-Features hinzu.
    """

    def __init__(self):
        super().__init__()
        self._db = None

    async def initialize(self):
        """Initialisiert mem0 (via Base) und die lokale SQLite-DB."""
        await super().initialize()
        await self._setup_db()

    async def _setup_db(self):
        try:
            from src.services.database import get_db

            self._db = get_db()
        except Exception as e:
            logger.error("DB-Setup-Fehler: %s", e)
            self._db = None

    # ------------------------------------------------------------------
    # Conversation Turns
    # ------------------------------------------------------------------

    async def add_conversation_turn(self, user_key: str, user_message: str, assistant_response: str):
        """Speichert einen Gespraechsaustausch im Gedaechtnis."""
        await self.add_messages(
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response},
            ],
            user_key=user_key,
        )

    # ------------------------------------------------------------------
    # Fact-Tracking (JARVIS Continuous Learning)
    # ------------------------------------------------------------------

    async def upsert_fact(self, user_key: str, content: str):
        """
        Speichert einen Fakt mit Bestaetigungs-Tracking.
        Wenn der Fakt bereits existiert, wird confirmation_count erhoeht.
        """
        if self._db is None:
            logger.warning("upsert_fact: DB nicht verfuegbar")
            return
        try:
            from src.services.database import MemoryFact
            from datetime import datetime, timezone

            with self._db() as session:
                existing = session.query(MemoryFact).filter_by(user_key=user_key, content=content).first()
                if existing:
                    existing.confirmation_count += 1
                    existing.last_used = datetime.now(timezone.utc)
                else:
                    session.add(MemoryFact(user_key=user_key, content=content))
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as e:
            logger.error("Upsert-Fact-Fehler: %s", e)

    async def get_top_facts(self, user_key: str, limit: int = 10) -> list[dict]:
        """Gibt die bestaetigtesten Fakten sortiert nach Konfidenz zurueck."""
        if self._db is None:
            logger.warning("get_top_facts: DB nicht verfuegbar")
            return []
        try:
            from src.services.database import MemoryFact

            with self._db() as session:
                facts = (
                    session.query(MemoryFact)
                    .filter_by(user_key=user_key)
                    .order_by(MemoryFact.confirmation_count.desc())
                    .limit(limit)
                    .all()
                )
                return [
                    {
                        "id": f.id,
                        "content": f.content,
                        "confirmation_count": f.confirmation_count,
                    }
                    for f in facts
                ]
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as e:
            logger.error("Get-Top-Facts-Fehler: %s", e)
            return []

    # ------------------------------------------------------------------
    # Onboarding
    # ------------------------------------------------------------------

    async def mark_onboarded(self, user_key: str):
        """Markiert User als onboardet in der lokalen DB."""
        if self._db is None:
            logger.warning("mark_onboarded: DB nicht verfuegbar")
            return
        try:
            from src.services.database import UserProfile

            with self._db() as session:
                profile = session.query(UserProfile).filter_by(user_key=user_key).first()
                if not profile:
                    profile = UserProfile(user_key=user_key)
                    session.add(profile)
                profile.is_onboarded = True
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as e:
            logger.error("Mark-Onboarded-Fehler: %s", e)

    async def is_onboarded(self, user_key: str) -> bool:
        """Prueft ob User bereits onboardet wurde."""
        if self._db is None:
            logger.warning("is_onboarded: DB nicht verfuegbar")
            return False
        try:
            from src.services.database import UserProfile

            with self._db() as session:
                profile = session.query(UserProfile).filter_by(user_key=user_key).first()
                return bool(profile and profile.is_onboarded)
        except (OSError, ValueError, RuntimeError, SQLAlchemyError) as e:
            logger.error("Is-Onboarded-Fehler: %s", e)
            return False
