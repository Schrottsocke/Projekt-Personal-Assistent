"""Notifications V2 Router: NotificationEvents, NotificationPreferences."""

from fastapi import APIRouter

from src.services.database import NotificationEvent, NotificationPreference  # noqa: F401

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "module": "notifications"}
