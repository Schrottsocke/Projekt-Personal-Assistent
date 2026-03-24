"""
APScheduler: Proaktive Nachrichten - Morgen-Briefing & Erinnerungen.
"""

import asyncio
import logging
from datetime import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config.settings import settings

logger = logging.getLogger(__name__)


class AssistantScheduler:
    """
    Verwaltet alle geplanten Aufgaben:
    - Morgen-Briefing (täglich zur konfigurierten Uhrzeit)
    - Erinnerungen (prüft jede Minute auf fällige Erinnerungen)
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            timezone=settings.TIMEZONE
        )
        self._bots: dict = {}  # user_key -> bot instance
        self._applications: dict = {}  # user_key -> telegram Application

    def register_bot(self, user_key: str, bot, application):
        """Registriert einen Bot für proaktive Nachrichten."""
        self._bots[user_key] = bot
        self._applications[user_key] = application
        logger.info(f"Bot '{user_key}' im Scheduler registriert.")

    def start(self):
        """Startet den Scheduler mit allen Jobs."""
        # Morgen-Briefing
        hour, minute = settings.MORNING_BRIEFING_TIME.split(":")
        self.scheduler.add_job(
            self._send_morning_briefings,
            CronTrigger(hour=int(hour), minute=int(minute), timezone=settings.TIMEZONE),
            id="morning_briefing",
            replace_existing=True,
            name="Morgen-Briefing",
        )

        # Erinnerungen prüfen (jede Minute)
        self.scheduler.add_job(
            self._check_reminders,
            IntervalTrigger(minutes=1),
            id="reminder_check",
            replace_existing=True,
            name="Erinnerungs-Check",
        )

        self.scheduler.start()
        logger.info(
            f"Scheduler gestartet. Briefing täglich um {settings.MORNING_BRIEFING_TIME} Uhr."
        )

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler gestoppt.")

    async def _send_morning_briefings(self):
        """Sendet Morgen-Briefings an alle registrierten Bots."""
        logger.info("Sende Morgen-Briefings...")
        for user_key, bot in self._bots.items():
            try:
                await self._send_briefing_to_user(user_key, bot)
            except Exception as e:
                logger.error(f"Briefing-Fehler für '{user_key}': {e}")

    async def _send_briefing_to_user(self, user_key: str, bot):
        """Sendet Briefing an einen spezifischen User."""
        # Chat-ID aus DB holen
        chat_id = await self._get_chat_id(user_key)
        if not chat_id:
            logger.warning(f"Keine Chat-ID für '{user_key}' - Briefing übersprungen.")
            return

        from src.scheduler.briefing import generate_briefing
        text = await generate_briefing(bot)

        app = self._applications.get(user_key)
        if app:
            await app.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown"
            )
            logger.info(f"Morgen-Briefing gesendet an '{user_key}'.")

    async def _check_reminders(self):
        """Prüft und sendet fällige Erinnerungen."""
        if not self._bots:
            return

        # Einen beliebigen Bot für den DB-Zugriff nehmen
        first_bot = next(iter(self._bots.values()))
        try:
            due = await first_bot.reminder_service.get_due_reminders()
        except Exception as e:
            logger.error(f"Reminder-Check-Fehler: {e}")
            return

        for reminder in due:
            user_key = reminder.get("user_key")
            chat_id = reminder.get("chat_id")
            content = reminder.get("content")
            reminder_id = reminder.get("id")

            if not chat_id:
                continue

            app = self._applications.get(user_key)
            if app:
                try:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"⏰ *Erinnerung!*\n\n{content}",
                        parse_mode="Markdown"
                    )
                    await first_bot.reminder_service.mark_sent(reminder_id)
                    logger.info(f"Erinnerung #{reminder_id} gesendet an '{user_key}'.")
                except Exception as e:
                    logger.error(f"Erinnerungs-Send-Fehler für '{user_key}': {e}")

    async def _get_chat_id(self, user_key: str) -> str | None:
        """Holt Chat-ID aus DB."""
        try:
            from src.services.database import UserProfile, get_db
            with get_db()() as session:
                profile = session.query(UserProfile).filter_by(user_key=user_key).first()
                return profile.chat_id if profile else None
        except Exception as e:
            logger.warning(f"Chat-ID-Abruf-Fehler: {e}")
            return None
