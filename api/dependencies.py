"""
Dependency Injection für die FastAPI-App.

Services werden einmalig beim Start initialisiert (lifespan) und
dann via FastAPI Depends in die Routen injiziert.
"""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from api.auth.jwt_handler import verify_token
from api.bot_shim import ApiBotShim

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Globaler Service-Container
_svc: dict = {}


async def startup():
    """Alle Services initialisieren – wird in lifespan() aufgerufen."""
    from src.services.ai_service import AIService
    from src.services.memory_service import ApiMemoryService
    from src.services.calendar_service import CalendarService
    from src.services.notes_service import NotesService
    from src.services.reminder_service import ReminderService
    from src.services.task_service import TaskService
    from src.services.shopping_service import ShoppingService
    from src.services.chefkoch_service import ChefkochService
    from src.services.email_service import EmailService
    from src.services.drive_service import DriveService
    from src.services.notification_service import NotificationService
    from src.services.contacts_service import ContactsService
    from src.services.followup_service import FollowUpService
    from src.services.weather_service import WeatherService
    from src.services.mobility_service import MobilityService
    from src.services.ocr_service import OcrService
    from src.services.pdf_service import PdfService
    from src.services.template_service import TemplateService
    from src.services.database import init_db

    init_db()

    # Services erst in lokaler Map aufbauen, dann nach erfolgreicher Init uebernehmen.
    # Jeden Konstruktor einzeln wrappen, damit ein fehlender Service nicht alle blockiert.
    pending: dict = {}
    _constructors = [
        ("ai", AIService),
        ("memory", ApiMemoryService),
        ("calendar", CalendarService),
        ("notes", NotesService),
        ("reminder", ReminderService),
        ("task", TaskService),
        ("shopping", ShoppingService),
        ("chefkoch", ChefkochService),
        ("email", EmailService),
        ("drive", DriveService),
        ("notification", NotificationService),
        ("contacts", ContactsService),
        ("followup", FollowUpService),
        ("weather", WeatherService),
        ("mobility", MobilityService),
        ("ocr", OcrService),
        ("pdf", PdfService),
        ("template", TemplateService),
    ]

    # AutomationService (JSON-basiert, kein DB-Init noetig)
    from src.services.automation_service import AutomationService

    try:
        auto_svc = AutomationService()
        await auto_svc.initialize()
        _svc["automation"] = auto_svc
        logger.info("API Service 'automation' initialisiert.")
    except Exception as e:
        logger.warning("API Service 'automation' Init-Fehler: %s", e)
    for name, cls in _constructors:
        try:
            pending[name] = cls()
        except Exception as e:
            logger.warning("API Service '%s' Konstruktor-Fehler (uebersprungen): %s", name, e)

    # Async-Initialisierung – nur erfolgreich initialisierte Services uebernehmen
    # Services ohne async init (ai, shopping, chefkoch) werden direkt uebernommen
    for name in ("ai", "shopping", "chefkoch", "weather", "mobility", "ocr", "pdf"):
        if name in pending:
            _svc[name] = pending[name]
            logger.info("API Service '%s' registriert (sync).", name)

    for name in (
        "memory",
        "calendar",
        "notes",
        "reminder",
        "task",
        "email",
        "drive",
        "notification",
        "contacts",
        "followup",
        "template",
    ):
        if name not in pending:
            continue
        try:
            await pending[name].initialize()
            _svc[name] = pending[name]
            logger.info("API Service '%s' initialisiert.", name)
        except Exception as e:
            logger.warning("API Service '%s' Init-Fehler (nicht registriert): %s", name, e)

    # Bot-Shim nur erstellen, wenn alle benoetigten Services verfuegbar sind
    required_for_shim = (
        "ai",
        "memory",
        "calendar",
        "notes",
        "reminder",
        "task",
        "shopping",
        "chefkoch",
        "email",
        "drive",
    )
    missing = [n for n in required_for_shim if n not in _svc]
    if missing:
        logger.warning("Bot-Shim nicht erstellt – fehlende Services: %s", missing)
    else:
        _svc["bot_shim"] = ApiBotShim(
            ai_service=_svc["ai"],
            memory_service=_svc["memory"],
            calendar_service=_svc["calendar"],
            notes_service=_svc["notes"],
            reminder_service=_svc["reminder"],
            task_service=_svc["task"],
            shopping_service=_svc["shopping"],
            chefkoch_service=_svc["chefkoch"],
            email_service=_svc["email"],
            drive_service=_svc["drive"],
            ocr_service=_svc.get("ocr"),
            pdf_service=_svc.get("pdf"),
        )
    logger.info("API Initialisierung abgeschlossen.")


# ------------------------------------------------------------------
# Dependency-Getter
# ------------------------------------------------------------------


def _require(name: str):
    svc = _svc.get(name)
    if svc is None:
        raise HTTPException(status_code=503, detail=f"Service '{name}' not available")
    return svc


def get_ai_service():
    return _require("ai")


def get_memory_service():
    return _require("memory")


def get_calendar_service():
    return _require("calendar")


def get_calendar_service_optional():
    """Calendar-Service oder None (kein 503 wenn nicht verfuegbar)."""
    return _svc.get("calendar")


def get_task_service():
    return _require("task")


def get_reminder_service():
    return _require("reminder")


def get_shopping_service():
    return _require("shopping")


def get_chefkoch_service():
    return _require("chefkoch")


def get_notes_service():
    return _require("notes")


def get_email_service():
    return _require("email")


def get_drive_service():
    return _require("drive")


def get_drive_service_optional():
    """Drive-Service oder None (kein 503 wenn nicht verfuegbar)."""
    return _svc.get("drive")


def get_notification_service():
    return _require("notification")


def get_contacts_service():
    return _require("contacts")


def get_followup_service():
    return _require("followup")


def get_weather_service():
    return _require("weather")


def get_weather_service_optional():
    """Weather-Service oder None (kein 503 wenn nicht verfuegbar)."""
    return _svc.get("weather")


def get_mobility_service():
    return _require("mobility")


def get_ocr_service():
    return _require("ocr")


def get_pdf_service():
    return _require("pdf")


def get_template_service():
    return _require("template")


def get_automation_service():
    return _require("automation")


def get_bot_shim():
    return _require("bot_shim")


# ------------------------------------------------------------------
# Auth-Dependency
# ------------------------------------------------------------------


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """Validiert JWT und gibt user_key ('taake' | 'nina') zurück."""
    return verify_token(token, token_type="access")
