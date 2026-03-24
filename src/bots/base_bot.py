"""
Basis-Bot-Klasse: Gemeinsame Logik für beide Bots (Taake & Nina).
Jeder Bot ist eine eigene Instanz mit eigenem Token, aber geteilter Engine.
"""

import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from config.settings import BotConfig, settings

logger = logging.getLogger(__name__)


class BaseAssistantBot:
    """
    Basis-Klasse für beide Personal-Assistenten-Bots.
    Wird von TaakeBot und NinaBot geerbt.
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self.name = config.name
        self.token = config.token
        self.owner_id = config.user_id
        self.app: Application | None = None

        # Services werden von außen injiziert (Dependency Injection)
        self.ai_service = None
        self.memory_service = None
        self.calendar_service = None
        self.notes_service = None
        self.reminder_service = None
        self.proposal_service = None

    def inject_services(
        self,
        ai_service,
        memory_service,
        calendar_service,
        notes_service,
        reminder_service,
        proposal_service,
    ):
        self.ai_service = ai_service
        self.memory_service = memory_service
        self.calendar_service = calendar_service
        self.notes_service = notes_service
        self.reminder_service = reminder_service
        self.proposal_service = proposal_service

    def _is_authorized(self, user_id: int) -> bool:
        """Nur der Owner darf mit diesem Bot interagieren."""
        return user_id == self.owner_id

    async def _unauthorized(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "⛔ Keine Berechtigung. Dieser Bot ist privat."
        )

    async def _check_auth(self, update: Update) -> bool:
        if not self._is_authorized(update.effective_user.id):
            await self._unauthorized(update, None)
            return False
        return True

    def build_application(self) -> Application:
        """Erstellt und konfiguriert die Telegram-Application."""
        from src.handlers.command_handlers import register_command_handlers
        from src.handlers.message_handlers import register_message_handlers
        from src.handlers.onboarding import register_onboarding_handler
        from src.handlers.proposal_handlers import register_proposal_handlers

        self.app = Application.builder().token(self.token).build()
        self.app.bot_data["bot_instance"] = self

        # Reihenfolge wichtig: Proposal-Callbacks zuerst, dann ConversationHandler
        register_proposal_handlers(self.app)
        register_onboarding_handler(self.app)
        register_command_handlers(self.app)
        register_message_handlers(self.app)

        logger.info(f"Bot '{self.name}' konfiguriert.")
        return self.app

    async def set_commands(self):
        """Setzt die Bot-Befehle im Telegram-Menü."""
        commands = [
            BotCommand("start", "Bot starten / Onboarding"),
            BotCommand("hilfe", "Alle Befehle anzeigen"),
            BotCommand("kalender", "Kalender anzeigen"),
            BotCommand("neu_termin", "Neuen Termin erstellen"),
            BotCommand("notiz", "Neue Notiz erstellen"),
            BotCommand("erinnerung", "Neue Erinnerung setzen"),
            BotCommand("briefing", "Morgen-Briefing jetzt abrufen"),
            BotCommand("gedaechtnis", "Gespeicherte Infos anzeigen"),
            BotCommand("vorschlaege", "Offene Vorschläge anzeigen"),
        ]
        await self.app.bot.set_my_commands(commands)
        logger.info(f"Bot '{self.name}': Befehle gesetzt.")
