"""
Basis-Bot-Klasse: Gemeinsame Logik für beide Bots (Taake & Nina).
Jeder Bot ist eine eigene Instanz mit eigenem Token, aber geteilter Engine.
"""

import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    ContextTypes,
)
from config.settings import BotConfig

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
        self.task_service = None
        self.document_service = None
        self.tts_service = None
        self.spotify_service = None
        self.smarthome_service = None
        self.chefkoch_service = None
        self.drive_service = None
        self.shopping_service = None
        self.email_service = None
        self.scanner_service = None
        self.mobility_service = None
        self.ocr_service = None
        self.pdf_service = None

    def inject_services(
        self,
        ai_service,
        memory_service,
        calendar_service=None,
        notes_service=None,
        reminder_service=None,
        proposal_service=None,
        task_service=None,
        document_service=None,
        tts_service=None,
        spotify_service=None,
        smarthome_service=None,
        chefkoch_service=None,
        drive_service=None,
        shopping_service=None,
        email_service=None,
        scanner_service=None,
        mobility_service=None,
        ocr_service=None,
        pdf_service=None,
    ):
        self.ai_service = ai_service
        self.memory_service = memory_service
        self.calendar_service = calendar_service
        self.notes_service = notes_service
        self.reminder_service = reminder_service
        self.proposal_service = proposal_service
        self.task_service = task_service
        self.document_service = document_service
        self.tts_service = tts_service
        self.spotify_service = spotify_service
        self.smarthome_service = smarthome_service
        self.chefkoch_service = chefkoch_service
        self.drive_service = drive_service
        self.shopping_service = shopping_service
        self.email_service = email_service
        self.scanner_service = scanner_service
        self.mobility_service = mobility_service
        self.ocr_service = ocr_service
        self.pdf_service = pdf_service

    def _is_authorized(self, user_id: int) -> bool:
        """Nur der Owner darf mit diesem Bot interagieren."""
        if self.owner_id <= 0:
            return False
        return user_id == self.owner_id

    async def _unauthorized(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("⛔ Keine Berechtigung. Dieser Bot ist privat.")

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
            BotCommand("tasks", "Offene Aufgaben anzeigen"),
            BotCommand("done", "Aufgabe abhaken"),
            BotCommand("kalender", "Kalender anzeigen"),
            BotCommand("neu_termin", "Neuen Termin erstellen"),
            BotCommand("notiz", "Neue Notiz erstellen"),
            BotCommand("erinnerung", "Neue Erinnerung setzen"),
            BotCommand("briefing", "Morgen-Briefing jetzt abrufen"),
            BotCommand("gedaechtnis", "Gespeicherte Infos anzeigen"),
            BotCommand("vorschlaege", "Offene Vorschläge anzeigen"),
            BotCommand("autonomie", "Direkt-Ausführung konfigurieren"),
            BotCommand("profil", "Persönlichkeitsprofil anzeigen"),
            BotCommand("tabelle", "Tabelle oder Excel-Datei erstellen"),
            BotCommand("praesentation", "PowerPoint-Präsentation erstellen"),
            BotCommand("fokus", "Fokus-Modus aktivieren"),
            BotCommand("gemeinsam", "Gemeinsamer Kalender mit Partner"),
            BotCommand("tts", "Sprachantworten an/aus"),
            BotCommand("spotify", "Spotify verbinden und steuern"),
            BotCommand("smarthome", "Smart Home Status und Steuerung"),
            BotCommand("rezept", "Rezept auf Chefkoch.de suchen"),
            BotCommand("drive", "Google Drive Dateien anzeigen & verwalten"),
        ]
        await self.app.bot.set_my_commands(commands)
        logger.info(f"Bot '{self.name}': Befehle gesetzt.")
