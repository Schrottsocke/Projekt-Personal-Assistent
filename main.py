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

    await memory_service.initialize()
    await calendar_service.initialize()
    await notes_service.initialize()
    await reminder_service.initialize()
    await proposal_service.initialize()
    await task_service.initialize()
    await document_service.initialize()

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
