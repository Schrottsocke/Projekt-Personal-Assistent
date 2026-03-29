"""
Main Entry Point: Startet beide Bots parallel.
"""

import asyncio
import logging
import logging.handlers
import signal
import sys
from pathlib import Path

import structlog

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

    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    # Console: human-readable; File: JSON mit Rotation (10 MB, 5 Backups)
    console_handler = logging.StreamHandler(sys.stdout)
    file_handler = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[console_handler, file_handler],
    )

    # Externe Libraries ruhigstellen
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)

    # structlog konfigurieren
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Console: lesbar; File: JSON
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(),
    )
    json_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
    )

    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(json_formatter)


logger = structlog.get_logger(__name__)


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

    CORE_SERVICES = {"ai_service", "memory_service"}

    SERVICE_DEFINITIONS = [
        ("ai_service", AIService, False),
        ("memory_service", MemoryService, True),
        ("calendar_service", CalendarService, True),
        ("notes_service", NotesService, True),
        ("reminder_service", ReminderService, True),
        ("proposal_service", ProposalService, True),
        ("task_service", TaskService, True),
        ("document_service", DocumentService, True),
        ("tts_service", TTSService, False),
        ("spotify_service", SpotifyService, False),
        ("smarthome_service", SmartHomeService, False),
        ("chefkoch_service", ChefkochService, False),
        ("drive_service", DriveService, True),
        ("shopping_service", ShoppingService, False),
        ("email_service", EmailService, True),
        ("scanner_service", ScannerService, False),
        ("mobility_service", MobilityService, False),
        ("ocr_service", OcrService, False),
        ("pdf_service", PdfService, False),
    ]

    services = {}
    status_table = []

    for name, cls, needs_init in SERVICE_DEFINITIONS:
        try:
            svc = cls()
            if needs_init:
                await svc.initialize()
            services[name] = svc
            status_table.append((name, "OK"))
        except FileNotFoundError:
            services[name] = None
            status_table.append((name, "NICHT KONFIGURIERT"))
            logger.warning(f"Service '{name}' nicht konfiguriert – übersprungen.")
        except Exception as e:
            services[name] = None
            status_table.append((name, f"FEHLER: {e}"))
            logger.error(f"Service '{name}' fehlgeschlagen: {e}")

    # Startup-Tabelle loggen
    logger.info("Service-Status:")
    logger.info("-" * 50)
    for name, status in status_table:
        logger.info(f"  {name:<25s} {status}")
    logger.info("-" * 50)

    # Core-Services prüfen
    for core in CORE_SERVICES:
        if services.get(core) is None:
            logger.critical(f"Core-Service '{core}' nicht verfügbar – Abbruch!")
            sys.exit(1)

    logger.info("Services bereit.")

    # Bots erstellen
    taake_bot = TaakeBot()
    nina_bot = NinaBot()

    # Services in Bots injizieren
    for bot in [taake_bot, nina_bot]:
        bot.inject_services(**services)

    # Telegram Applications bauen
    taake_app = taake_bot.build_application()
    nina_app = nina_bot.build_application()

    # ProposalService braucht die Apps für Bot-übergreifende Proposals
    if services["proposal_service"] is not None:
        services["proposal_service"].register_app("taake", taake_app)
        services["proposal_service"].register_app("nina", nina_app)

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
        if services["reminder_service"] is not None:
            await _deliver_missed_reminders(services["reminder_service"], taake_app, nina_app)

        logger.info("=" * 60)
        logger.info("Beide Bots laufen! Drücke Ctrl+C zum Beenden.")
        logger.info("=" * 60)

        # Graceful Shutdown via Signal-Handler
        shutdown_event = asyncio.Event()

        def _signal_handler(sig, _frame):
            sig_name = signal.Signals(sig).name
            logger.info(f"Signal {sig_name} empfangen – Shutdown eingeleitet...")
            shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, _signal_handler)

        await shutdown_event.wait()

        logger.info("Fahre Services herunter...")

        async def _shutdown_sequence():
            logger.info("Shutdown: Scheduler stoppen...")
            scheduler.stop()
            logger.info("Shutdown: Scheduler gestoppt.")

            logger.info("Shutdown: Updater stoppen...")
            await taake_app.updater.stop()
            await nina_app.updater.stop()
            logger.info("Shutdown: Updater gestoppt.")

            logger.info("Shutdown: Bots stoppen...")
            await taake_app.stop()
            await nina_app.stop()
            logger.info("Shutdown: Bots gestoppt.")

            # Datenbank-Sessions schliessen
            logger.info("Shutdown: Datenbank-Engine schliessen...")
            try:
                from src.services.database import _engine
                if _engine is not None:
                    _engine.dispose()
                    logger.info("Shutdown: Datenbank-Engine geschlossen.")
                else:
                    logger.info("Shutdown: Keine Datenbank-Engine aktiv.")
            except Exception as exc:
                logger.warning("Shutdown: Datenbank-Cleanup fehlgeschlagen: %s", exc)

        shutdown_timeout = 10  # Sekunden
        try:
            await asyncio.wait_for(_shutdown_sequence(), timeout=shutdown_timeout)
            logger.info("Sauber beendet.")
        except asyncio.TimeoutError:
            logger.error(
                "Shutdown dauerte laenger als %d Sekunden – erzwinge Beendigung.",
                shutdown_timeout,
            )
            sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
