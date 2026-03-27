"""
Dependency Injection für die FastAPI-App.

Services werden einmalig beim Start initialisiert (lifespan) und
dann via FastAPI Depends in die Routen injiziert.
"""

import logging
from typing import Annotated

from fastapi import Depends
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
    from src.services.memory_service import MemoryService
    from src.services.calendar_service import CalendarService
    from src.services.notes_service import NotesService
    from src.services.reminder_service import ReminderService
    from src.services.task_service import TaskService
    from src.services.shopping_service import ShoppingService
    from src.services.chefkoch_service import ChefkochService
    from src.services.email_service import EmailService
    from src.services.drive_service import DriveService
    from src.services.database import init_db

    init_db()

    _svc["ai"] = AIService()
    _svc["memory"] = MemoryService()
    _svc["calendar"] = CalendarService()
    _svc["notes"] = NotesService()
    _svc["reminder"] = ReminderService()
    _svc["task"] = TaskService()
    _svc["shopping"] = ShoppingService()
    _svc["chefkoch"] = ChefkochService()
    _svc["email"] = EmailService()
    _svc["drive"] = DriveService()

    # Async-Initialisierung
    for name in ("memory", "calendar", "notes", "reminder", "task", "email", "drive"):
        try:
            await _svc[name].initialize()
            logger.info("API Service '%s' initialisiert.", name)
        except Exception as e:
            logger.warning("API Service '%s' Init-Fehler (wird übersprungen): %s", name, e)

    # Bot-Shim für AIService-Aufrufe
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
    )
    logger.info("API vollständig initialisiert.")


# ------------------------------------------------------------------
# Dependency-Getter
# ------------------------------------------------------------------


def get_ai_service():
    return _svc.get("ai")


def get_memory_service():
    return _svc.get("memory")


def get_calendar_service():
    return _svc.get("calendar")


def get_task_service():
    return _svc.get("task")


def get_reminder_service():
    return _svc.get("reminder")


def get_shopping_service():
    return _svc.get("shopping")


def get_chefkoch_service():
    return _svc.get("chefkoch")


def get_email_service():
    return _svc.get("email")


def get_drive_service():
    return _svc.get("drive")


def get_bot_shim():
    return _svc.get("bot_shim")


# ------------------------------------------------------------------
# Auth-Dependency
# ------------------------------------------------------------------


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """Validiert JWT und gibt user_key ('taake' | 'nina') zurück."""
    return verify_token(token, token_type="access")
