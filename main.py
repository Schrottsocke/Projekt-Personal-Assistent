"""
Main Entry Point: Startet beide Bots parallel.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Projektpfad zum Python-Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from src.services.database import init_db
from src.services.ai_service import AIService
from src.services.calendar_service import CalendarService
from src.services.notes_service import NotesService
from src.services.reminder_service import ReminderService
from src.memory.memory_service import MemoryService
from src.scheduler.scheduler import AssistantScheduler
from src.services.proposal_service import ProposalService
from src.services.task_service import TaskService
from src.services.document_service import DocumentService
from src.services.tts_service import TTSService
from src.services.spotify_service import SpotifyService
from src.services.smarthome_service import SmartHomeService
from src.services.chefkoch_service import ChefkochService
from src.services.drive_service import DriveService
from src.services.shopping_service import ShoppingService
from src.services.email_service import EmailService
from src.services.scanner_service import ScannerService
from src.services.mobility_service import MobilityService
from src.services.ocr_service import OcrService
from src.services.pdf_service import PdfService
from src.bots.taake_bot import TaakeBot
from src.bots.nina_bot import NinaBot

# Logging konfigurieren
def setup_logging():
    settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.LOG_FILE),
    ]

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=handlers,
    )

    # Externe Libraries ruhigstellen
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


async def _deliver_missed_reminders(reminder_service, taake_app, nina_app):
    """
    Adoption B: Memory-Persistence – Sofortiges Zustellen verpasster Erinnerungen beim Start.
    Der Scheduler läuft erst nach 1 Minute; diese Funktion liefert sofort alle überfälligen
    Erinnerungen, die während des Bot-Downtimes fällig wurden.
    """
    try:
        due = await reminder_service.get_due_reminders()
        if not due:
            return

        logger.info(f"Startup: {len(due)} verpasste Erinnerungen werden zugestellt...")
        apps = {"taake": taake_app, "nina": nina_app}

        for reminder in due:
            user_key = reminder.get("user_key", "")
            chat_id = reminder.get("chat_id")
            content = reminder.get("content", "")
            app = apps.get(user_key)
            if app and chat_id:
                try:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"⏰ *Verpasste Erinnerung:*\n{content}",
                        parse_mode="Markdown",
                    )
                    await reminder_service.mark_sent(reminder["id"])
                    logger.info(f"Verpasste Erinnerung zugestellt: {user_key} – {content[:40]}")
                except Exception as e:
                    logger.error(f"Konnte verpasste Erinnerung nicht senden: {e}")
    except Exception as e:
        logger.error(f"Startup-Reminder-Check fehlgeschlagen: {e}")


async def main():
    setup_logging()
    logger.info("=" * 60)
    logger.info("Personal Assistant startet...")
    logger.info("=" * 60)

    # Konfiguration validieren
    errors = settings.validate()
    if errors:
        for err in errors:
            logger.error(f"Konfigurationsfehler: {err}")
        logger.error("Bitte .env Datei ausfüllen (siehe .env.example)")
        sys.exit(1)

    # Verzeichnisse anlegen
    Path("data").mkdir(exist_ok=True)
    Path("data/documents").mkdir(exist_ok=True)
    Path("data/scans").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    init_db()

    # Services initialisieren (geteilt zwischen beiden Bots)
    logger.info("Initialisiere Services...")
    ai_service = AIService()
    memory_service = MemoryService()
    calendar_service = CalendarService()
    notes_service = NotesService()
    reminder_service = ReminderService()
    proposal_service = ProposalService()
    task_service = TaskService()
    document_service = DocumentService()
    tts_service = TTSService()
    spotify_service = SpotifyService()
    smarthome_service = SmartHomeService()
    chefkoch_service = ChefkochService()
    drive_service = DriveService()
    shopping_service = ShoppingService()
    email_service = EmailService()
    scanner_service = ScannerService()
    mobility_service = MobilityService()
    ocr_service = OcrService()
    pdf_service = PdfService()

    await memory_service.initialize()
    await calendar_service.initialize()
    await notes_service.initialize()
    await reminder_service.initialize()
    await proposal_service.initialize()
    await task_service.initialize()
    await document_service.initialize()
    await drive_service.initialize()
    await email_service.initialize()

    logger.info("Services bereit.")

    # Bots erstellen
    taake_bot = TaakeBot()
    nina_bot = NinaBot()

    # Services in Bots injizieren
    for bot in [taake_bot, nina_bot]:
        bot.inject_services(
            ai_service=ai_service,
            memory_service=memory_service,
            calendar_service=calendar_service,
            notes_service=notes_service,
            reminder_service=reminder_service,
            proposal_service=proposal_service,
            task_service=task_service,
            document_service=document_service,
            tts_service=tts_service,
            spotify_service=spotify_service,
            smarthome_service=smarthome_service,
            chefkoch_service=chefkoch_service,
            drive_service=drive_service,
            shopping_service=shopping_service,
            email_service=email_service,
            scanner_service=scanner_service,
            mobility_service=mobility_service,
            ocr_service=ocr_service,
            pdf_service=pdf_service,
        )

    # Telegram Applications bauen
    taake_app = taake_bot.build_application()
    nina_app = nina_bot.build_application()

    # ProposalService braucht die Apps für Bot-übergreifende Proposals
    proposal_service.register_app("taake", taake_app)
    proposal_service.register_app("nina", nina_app)

    # Scheduler einrichten
    scheduler = AssistantScheduler()
    scheduler.register_bot("taake", taake_bot, taake_app)
    scheduler.register_bot("nina", nina_bot, nina_app)

    # Beide Bots + Scheduler parallel starten
    logger.info(f"Starte Bot 'Taake' (User-ID: {settings.TELEGRAM_USER_ID_TAAKE})...")
    logger.info(f"Starte Bot 'Nina' (User-ID: {settings.TELEGRAM_USER_ID_NINA})...")

    async with taake_app, nina_app:
        # Bot-Befehle setzen
        await taake_bot.set_commands()
        await nina_bot.set_commands()

        # Polling starten
        await taake_app.updater.start_polling(drop_pending_updates=True)
        await nina_app.updater.start_polling(drop_pending_updates=True)

        await taake_app.start()
        await nina_app.start()

        # Scheduler starten
        scheduler.start()

        # Adoption B: Memory-Persistence – verpasste Erinnerungen sofort zustellen
        await _deliver_missed_reminders(reminder_service, taake_app, nina_app)

        logger.info("=" * 60)
        logger.info("Beide Bots laufen! Drücke Ctrl+C zum Beenden.")
        logger.info("=" * 60)

        # Warten bis Ctrl+C
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutdown eingeleitet...")
        finally:
            scheduler.stop()
            await taake_app.updater.stop()
            await nina_app.updater.stop()
            await taake_app.stop()
            await nina_app.stop()
            logger.info("Sauber beendet.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
