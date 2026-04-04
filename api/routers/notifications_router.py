"""Notifications V2 Router: Events, Preferences, History."""

import json
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from config.settings import settings
from src.services.database import (
    NotificationEvent,
    NotificationPreference,
    UserProfile,
    get_db,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# --- Inline Schemas ---


class NotificationEventCreate(BaseModel):
    type: str = Field(..., max_length=30)
    title: Optional[str] = Field(None, max_length=300)
    message: Optional[str] = None
    channel: Literal["push", "email", "inapp"] = "inapp"
    reference_id: Optional[int] = None
    reference_type: Optional[str] = Field(None, max_length=50)
    link: Optional[str] = Field(None, max_length=500)


class NotificationEventOut(BaseModel):
    id: int
    user_id: Optional[int]
    user_key: Optional[str]
    type: str
    title: Optional[str]
    message: Optional[str]
    status: str
    link: Optional[str]
    channel: str
    reference_id: Optional[int]
    reference_type: Optional[str]
    sent_at: Optional[datetime]
    read_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationEventUpdate(BaseModel):
    status: Literal["new", "read", "completed", "hidden"]


class PreferenceUpsert(BaseModel):
    push_enabled: bool = True
    email_enabled: bool = True
    quiet_start: str = Field("22:00", pattern=r"^\d{2}:\d{2}$")
    quiet_end: str = Field("07:00", pattern=r"^\d{2}:\d{2}$")


class PreferenceOut(BaseModel):
    id: int
    user_id: int
    category: str
    push_enabled: bool
    email_enabled: bool
    quiet_start: str
    quiet_end: str

    class Config:
        from_attributes = True


# --- Helpers ---


def _resolve_user_id(db, user_key: str) -> int:
    profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User-Profil nicht gefunden.")
    return profile.id


# --- Health ---


@router.get("/health")
async def health():
    return {"status": "ok", "module": "notifications"}


# --- Events (#655) ---


@router.post("/events", response_model=NotificationEventOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_event(
    request: Request,
    body: NotificationEventCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        evt = NotificationEvent(
            user_id=uid,
            user_key=user_key,
            type=body.type,
            title=body.title,
            message=body.message,
            channel=body.channel,
            reference_id=body.reference_id,
            reference_type=body.reference_type,
            link=body.link,
        )
        db.add(evt)
        db.flush()
        db.refresh(evt)
        return evt


@router.get("/events/unread-count")
async def unread_count(user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        count = (
            db.query(NotificationEvent)
            .filter(NotificationEvent.user_id == uid, NotificationEvent.status == "new")
            .count()
        )
        return {"unread_count": count}


@router.get("/events", response_model=list[NotificationEventOut])
async def list_events(
    user_key: Annotated[str, Depends(get_current_user)],
    type: Optional[str] = None,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        q = db.query(NotificationEvent).filter(NotificationEvent.user_id == uid)
        if type:
            q = q.filter(NotificationEvent.type == type)
        if status:
            q = q.filter(NotificationEvent.status == status)
        if channel:
            q = q.filter(NotificationEvent.channel == channel)
        return q.order_by(NotificationEvent.created_at.desc()).offset(offset).limit(limit).all()


@router.patch("/events/{event_id}", response_model=NotificationEventOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_event(
    request: Request,
    event_id: int,
    body: NotificationEventUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        evt = (
            db.query(NotificationEvent)
            .filter(NotificationEvent.id == event_id, NotificationEvent.user_id == uid)
            .first()
        )
        if not evt:
            raise HTTPException(404, "Benachrichtigung nicht gefunden.")
        evt.status = body.status
        if body.status == "read":
            evt.read_at = datetime.now(timezone.utc)
        evt.updated_at = datetime.now(timezone.utc)
        db.flush()
        db.refresh(evt)
        return evt


@router.post("/events/mark-all-read")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def mark_all_read(request: Request, user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        now = datetime.now(timezone.utc)
        count = (
            db.query(NotificationEvent)
            .filter(NotificationEvent.user_id == uid, NotificationEvent.status == "new")
            .update(
                {
                    NotificationEvent.status: "read",
                    NotificationEvent.read_at: now,
                    NotificationEvent.updated_at: now,
                },
                synchronize_session="fetch",
            )
        )
        return {"marked_read": count}


@router.delete("/events/{event_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_event(
    request: Request,
    event_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        evt = (
            db.query(NotificationEvent)
            .filter(NotificationEvent.id == event_id, NotificationEvent.user_id == uid)
            .first()
        )
        if not evt:
            raise HTTPException(404, "Benachrichtigung nicht gefunden.")
        db.delete(evt)


@router.get("/history", response_model=list[NotificationEventOut])
async def notification_history(user_key: Annotated[str, Depends(get_current_user)], days: int = 30):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            db.query(NotificationEvent)
            .filter(NotificationEvent.user_id == uid, NotificationEvent.created_at >= cutoff)
            .order_by(NotificationEvent.created_at.desc())
            .all()
        )


# --- Preferences (#655) ---


@router.get("/preferences", response_model=list[PreferenceOut])
async def list_preferences(user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        return db.query(NotificationPreference).filter(NotificationPreference.user_id == uid).all()


@router.get("/preferences/{category}", response_model=PreferenceOut)
async def get_preference(category: str, user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        pref = (
            db.query(NotificationPreference)
            .filter(NotificationPreference.user_id == uid, NotificationPreference.category == category)
            .first()
        )
        if not pref:
            raise HTTPException(404, "Preference nicht gefunden.")
        return pref


@router.put("/preferences/{category}", response_model=PreferenceOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def upsert_preference(
    request: Request,
    category: str,
    body: PreferenceUpsert,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        pref = (
            db.query(NotificationPreference)
            .filter(NotificationPreference.user_id == uid, NotificationPreference.category == category)
            .first()
        )
        if pref:
            pref.push_enabled = body.push_enabled
            pref.email_enabled = body.email_enabled
            pref.quiet_start = body.quiet_start
            pref.quiet_end = body.quiet_end
        else:
            pref = NotificationPreference(
                user_id=uid,
                category=category,
                push_enabled=body.push_enabled,
                email_enabled=body.email_enabled,
                quiet_start=body.quiet_start,
                quiet_end=body.quiet_end,
            )
            db.add(pref)
        db.flush()
        db.refresh(pref)
        return pref


@router.delete("/preferences/{category}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_preference(
    request: Request,
    category: str,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        pref = (
            db.query(NotificationPreference)
            .filter(NotificationPreference.user_id == uid, NotificationPreference.category == category)
            .first()
        )
        if not pref:
            raise HTTPException(404, "Preference nicht gefunden.")
        db.delete(pref)
