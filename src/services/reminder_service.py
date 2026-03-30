"""
Erinnerungen-Service: CRUD + Scheduler-Integration.
Erinnerungen werden in der DB gespeichert und vom Scheduler zugestellt.
"""

import logging
from datetime import datetime, timezone
import pytz

from config.settings import settings

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self):
        self._db = None
        self.tz = pytz.timezone(settings.TIMEZONE)

    def _ensure_initialized(self):
        if self._db is None:
            raise RuntimeError("ReminderService not initialized – call initialize() first")

    async def initialize(self):
        from src.services.database import get_db, init_db

        init_db()
        self._db = get_db()
        logger.info("Reminder Service initialisiert.")

    async def create_reminder(
        self,
        user_key: str,
        user_chat_id: str,
        content: str,
        remind_at: datetime,
        is_shared: bool = False,
    ) -> dict:
        from src.services.database import Reminder

        self._ensure_initialized()
        with self._db() as session:
            reminder = Reminder(
                user_key=user_key,
                chat_id=str(user_chat_id),
                content=content,
                remind_at=remind_at,
                is_shared=is_shared,
            )
            session.add(reminder)
            session.flush()
            result = {
                "id": reminder.id,
                "content": content,
                "remind_at": remind_at,
                "chat_id": str(user_chat_id),
            }

        logger.info(f"Erinnerung erstellt für '{user_key}': {content[:50]} @ {remind_at}")
        return result

    async def get_active_reminders(self, user_key: str) -> list[dict]:
        from src.services.database import Reminder

        now = datetime.now(timezone.utc)
        self._ensure_initialized()
        with self._db() as session:
            reminders = (
                session.query(Reminder)
                .filter(
                    Reminder.user_key == user_key,
                    Reminder.is_sent == False,
                    Reminder.remind_at >= now,
                )
                .order_by(Reminder.remind_at.asc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "content": r.content,
                    "remind_at": pytz.utc.localize(r.remind_at).astimezone(self.tz) if r.remind_at.tzinfo is None else r.remind_at.astimezone(self.tz),
                    "chat_id": r.chat_id,
                }
                for r in reminders
            ]

    async def get_due_reminders(self) -> list[dict]:
        """Gibt alle fälligen Erinnerungen zurück (für den Scheduler)."""
        from src.services.database import Reminder

        now = datetime.now(timezone.utc)
        self._ensure_initialized()
        with self._db() as session:
            reminders = (
                session.query(Reminder)
                .filter(
                    Reminder.is_sent == False,
                    Reminder.remind_at <= now,
                )
                .all()
            )
            return [
                {
                    "id": r.id,
                    "content": r.content,
                    "remind_at": r.remind_at,
                    "chat_id": r.chat_id,
                    "user_key": r.user_key,
                }
                for r in reminders
            ]

    async def get_todays_reminders(self, user_key: str) -> list[dict]:
        """Gibt heutige Erinnerungen zurück (für Briefing)."""
        from src.services.database import Reminder

        now = datetime.now(self.tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)

        start_utc = start.astimezone(pytz.utc).replace(tzinfo=None)
        end_utc = end.astimezone(pytz.utc).replace(tzinfo=None)

        self._ensure_initialized()
        with self._db() as session:
            reminders = (
                session.query(Reminder)
                .filter(
                    Reminder.user_key == user_key,
                    Reminder.is_sent == False,
                    Reminder.remind_at >= start_utc,
                    Reminder.remind_at <= end_utc,
                )
                .order_by(Reminder.remind_at.asc())
                .all()
            )
            return [{"id": r.id, "content": r.content, "remind_at": r.remind_at} for r in reminders]

    async def mark_sent(self, reminder_id: int):
        """Markiert eine Erinnerung als zugestellt."""
        from src.services.database import Reminder

        self._ensure_initialized()
        with self._db() as session:
            reminder = session.query(Reminder).filter_by(id=reminder_id).first()
            if reminder:
                reminder.is_sent = True

    async def delete_reminder(self, reminder_id: int, user_key: str) -> bool:
        from src.services.database import Reminder

        self._ensure_initialized()
        with self._db() as session:
            reminder = session.query(Reminder).filter_by(id=reminder_id, user_key=user_key).first()
            if reminder:
                session.delete(reminder)
                return True
        return False
