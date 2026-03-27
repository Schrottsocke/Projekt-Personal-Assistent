"""
APScheduler: Proaktive Nachrichten - Morgen-Briefing, Erinnerungen,
Mustererkennung (alle 2 Tage), Wochenrückblick (Sonntags).
"""

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
    - Proaktive Mustererkennung (alle 2 Tage um 20:00)
    - Wochenrückblick (jeden Sonntag um 18:00)
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)
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

        # Proaktive Mustererkennung (alle 2 Tage um 20:00)
        self.scheduler.add_job(
            self._run_pattern_analysis,
            IntervalTrigger(days=2, hours=20, timezone=settings.TIMEZONE),
            id="pattern_analysis",
            replace_existing=True,
            name="Proaktive Mustererkennung",
        )

        # Wochenrückblick (jeden Sonntag um 18:00)
        self.scheduler.add_job(
            self._send_weekly_reviews,
            CronTrigger(day_of_week="sun", hour=18, minute=0, timezone=settings.TIMEZONE),
            id="weekly_review",
            replace_existing=True,
            name="Wochenrückblick",
        )

        # Conversation-History-Pruning (täglich um 03:00)
        self.scheduler.add_job(
            self._prune_conversation_history,
            CronTrigger(hour=3, minute=0, timezone=settings.TIMEZONE),
            id="conversation_pruning",
            replace_existing=True,
            name="Conversation-History-Pruning",
        )

        # E-Mail-Check (konfigurierbares Intervall, Standard 15 Min)
        self.scheduler.add_job(
            self._check_new_emails,
            IntervalTrigger(minutes=settings.EMAIL_CHECK_INTERVAL_MINUTES),
            id="email_check",
            replace_existing=True,
            name="E-Mail-Check",
        )

        self.scheduler.start()
        logger.info(
            f"Scheduler gestartet: Briefing {settings.MORNING_BRIEFING_TIME}, "
            f"Mustererkennung alle 2 Tage 20:00, Wochenrückblick So 18:00."
        )

    def stop(self):
        if self.scheduler.running:
            logger.info("Scheduler wird heruntergefahren (warte auf laufende Jobs, max 10s)...")
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler gestoppt.")

    async def _send_morning_briefings(self):
        """Sendet Morgen-Briefings an alle registrierten Bots."""
        logger.info("Sende Morgen-Briefings...")
        for user_key, bot in self._bots.items():
            if self._is_focus_mode(user_key):
                logger.info(f"Briefing für '{user_key}' übersprungen (Fokus-Modus).")
                continue
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
            await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
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
            content = reminder.get("content", "")
            reminder_id = reminder.get("id")

            if not chat_id:
                continue

            # Fokus-Modus: nur dringende Erinnerungen sofort senden
            is_urgent = "dringend" in content.lower()
            if self._is_focus_mode(user_key) and not is_urgent:
                logger.info(f"Erinnerung #{reminder_id} für '{user_key}' zurückgehalten (Fokus-Modus).")
                continue

            app = self._applications.get(user_key)
            if app:
                try:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"⏰ *Erinnerung!*\n\n{content}",
                        parse_mode="Markdown",
                    )
                    await first_bot.reminder_service.mark_sent(reminder_id)
                    logger.info(f"Erinnerung #{reminder_id} gesendet an '{user_key}'.")
                except Exception as e:
                    logger.error(f"Erinnerungs-Send-Fehler für '{user_key}': {e}")

    async def _run_pattern_analysis(self):
        """Proaktive Mustererkennung: analysiert Daten und erstellt Proposals."""
        logger.info("Starte proaktive Mustererkennung...")

        for user_key, bot in self._bots.items():
            try:
                if self._is_quiet_hours(user_key):
                    logger.info(f"Mustererkennung für '{user_key}' übersprungen (Ruhezeit).")
                    continue

                chat_id = await self._get_chat_id(user_key)
                if not chat_id:
                    continue

                intelligence = bot.ai_service.intelligence
                suggestions = await intelligence.analyze_patterns(user_key=user_key, bot=bot)

                for suggestion in suggestions:
                    s_type = suggestion.get("type", "ai_suggestion")
                    title = suggestion.get("title", "Vorschlag")
                    desc = suggestion.get("description", "")
                    payload = suggestion.get("payload", {})

                    await bot.proposal_service.create_proposal(
                        user_key=user_key,
                        proposal_type=s_type,
                        title=title,
                        description=desc,
                        payload=payload,
                        created_by="ai_pattern",
                        chat_id=chat_id,
                    )

                if suggestions:
                    logger.info(f"Mustererkennung für '{user_key}': {len(suggestions)} Vorschläge erstellt.")
            except Exception as e:
                logger.error(f"Mustererkennung-Fehler für '{user_key}': {e}")

    async def _send_weekly_reviews(self):
        """Sendet Wochenrückblick an alle registrierten Bots."""
        logger.info("Sende Wochenrückblicke...")

        for user_key, bot in self._bots.items():
            try:
                if self._is_quiet_hours(user_key):
                    logger.info(f"Wochenrückblick für '{user_key}' übersprungen (Ruhezeit).")
                    continue

                chat_id = await self._get_chat_id(user_key)
                if not chat_id:
                    continue

                intelligence = bot.ai_service.intelligence
                review_text = await intelligence.generate_weekly_review(
                    user_key=user_key,
                    name=bot.name,
                    bot=bot,
                )

                app = self._applications.get(user_key)
                if app:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=review_text,
                        parse_mode="Markdown",
                    )
                    logger.info(f"Wochenrückblick gesendet an '{user_key}'.")
            except Exception as e:
                logger.error(f"Wochenrückblick-Fehler für '{user_key}': {e}")

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

    def _is_quiet_hours(self, user_key: str) -> bool:
        """
        Gibt True zurück wenn der User gerade Ruhezeit hat.
        Gilt nur für proaktive Nachrichten (Muster, Weekly Review) –
        nicht für explizit gesetzte Erinnerungen.
        """
        try:
            from src.services.database import UserProfile, get_db

            with get_db()() as session:
                profile = session.query(UserProfile).filter_by(user_key=user_key).first()
                if not profile or not profile.quiet_start:
                    return False

                tz = pytz.timezone(settings.TIMEZONE)
                now = datetime.now(tz)
                current_minutes = now.hour * 60 + now.minute

                quiet_h, quiet_m = (int(x) for x in profile.quiet_start.split(":"))
                quiet_start_min = quiet_h * 60 + quiet_m

                quiet_end_str = profile.quiet_end or "07:00"
                end_h, end_m = (int(x) for x in quiet_end_str.split(":"))
                quiet_end_min = end_h * 60 + end_m

                if quiet_start_min > quiet_end_min:
                    # Über Mitternacht (z.B. 22:00 – 07:00)
                    return current_minutes >= quiet_start_min or current_minutes < quiet_end_min
                else:
                    return quiet_start_min <= current_minutes < quiet_end_min
        except Exception as e:
            logger.warning(f"Quiet-Hours-Check-Fehler: {e}")
            return False

    async def _prune_conversation_history(self):
        """Löscht Conversation-History-Einträge die älter als CONVERSATION_HISTORY_DAYS sind."""
        try:
            from src.services.database import prune_conversation_history

            days = settings.CONVERSATION_HISTORY_DAYS
            deleted = prune_conversation_history(days=days)
            logger.info(f"Conversation-Pruning: {deleted} Einträge gelöscht (> {days} Tage).")
        except Exception as e:
            logger.error(f"Conversation-Pruning-Fehler: {e}")

    async def _check_new_emails(self):
        """Prüft auf neue ungelesene Mails und benachrichtigt die User."""
        for user_key, bot in self._bots.items():
            try:
                if not hasattr(bot, "email_service") or not bot.email_service:
                    continue
                if not bot.email_service.is_connected(user_key):
                    continue
                if self._is_quiet_hours(user_key) or self._is_focus_mode(user_key):
                    continue

                count = await bot.email_service.get_unread_count(user_key)
                if count <= 0:
                    continue

                chat_id = await self._get_chat_id(user_key)
                if not chat_id:
                    continue

                app = self._applications.get(user_key)
                if app and count > 0:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"📬 Du hast *{count}* ungelesene E-Mail{'s' if count != 1 else ''}.\n_/email_ zum Anzeigen.",
                        parse_mode="Markdown",
                    )
                    logger.info(f"E-Mail-Benachrichtigung gesendet an '{user_key}': {count} ungelesen.")
            except Exception as e:
                logger.error(f"E-Mail-Check-Fehler für '{user_key}': {e}")

    def _is_focus_mode(self, user_key: str) -> bool:
        """Gibt True zurück wenn der User gerade im Fokus-Modus ist."""
        try:
            from src.services.database import UserProfile, get_db

            with get_db()() as session:
                profile = session.query(UserProfile).filter_by(user_key=user_key).first()
                if not profile or not profile.focus_mode_until:
                    return False
                now_utc = datetime.utcnow()
                return now_utc < profile.focus_mode_until
        except Exception as e:
            logger.warning(f"Fokus-Modus-Check-Fehler: {e}")
            return False
