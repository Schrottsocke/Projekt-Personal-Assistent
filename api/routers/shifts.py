"""CRUD /shifts/types und /shifts/entries – Dienstplan-Verwaltung."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.shift import (
    ShiftEntryCreate,
    ShiftEntryOut,
    ShiftTypeCreate,
    ShiftTypeOut,
    ShiftTypeUpdate,
)
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _row_to_dict(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def _entry_with_type(entry_row, type_row):
    """Kombiniert ShiftEntry mit denormalisierten ShiftType-Feldern."""
    d = _row_to_dict(entry_row)
    if type_row:
        d["shift_type_name"] = type_row.name
        d["shift_type_short_name"] = type_row.short_name
        d["shift_type_color"] = type_row.color
        d["shift_type_start_time"] = type_row.start_time
        d["shift_type_end_time"] = type_row.end_time
        d["shift_type_category"] = type_row.category
    return d


def get_shift_events_for_range(user_key: str, start: str, end: str) -> list[dict]:
    """Shift-Eintraege als Kalender-Event-Dicts fuer einen Zeitraum.

    Wird auch von calendar.py und dashboard.py verwendet.
    """
    from src.services.database import ShiftEntry, ShiftType, get_db

    with get_db()() as session:
        entries = (
            session.query(ShiftEntry, ShiftType)
            .outerjoin(ShiftType, ShiftEntry.shift_type_id == ShiftType.id)
            .filter(
                ShiftEntry.user_key == user_key,
                ShiftEntry.date >= start,
                ShiftEntry.date <= end,
            )
            .order_by(ShiftEntry.date)
            .all()
        )

        result = []
        for entry, stype in entries:
            st = stype.start_time or "00:00"
            et = stype.end_time or "23:59"
            summary = f"{stype.name} ({stype.short_name})" if stype else "Dienst"
            note = entry.note or (stype.default_note if stype else "")
            result.append(
                {
                    "id": f"shift_{entry.id}",
                    "summary": summary,
                    "start": f"{entry.date}T{st}:00",
                    "end": f"{entry.date}T{et}:00",
                    "description": note or "",
                    "location": "",
                    "source": "shift",
                    "shift_color": stype.color if stype else "#7c4dff",
                    "shift_short_name": stype.short_name if stype else "?",
                    "shift_category": stype.category if stype else "work",
                    "shift_entry_id": entry.id,
                }
            )
    return result


# ─── Shift Types ─────────────────────────────────────────────


@router.get("/types", response_model=list[ShiftTypeOut])
async def list_shift_types(
    user_key: Annotated[str, Depends(get_current_user)],
    all: bool = Query(False, description="Auch inaktive Diensttypen anzeigen"),
):
    from src.services.database import ShiftType, get_db

    with get_db()() as session:
        q = session.query(ShiftType).filter(ShiftType.user_key == user_key)
        if not all:
            q = q.filter(ShiftType.is_active == True)  # noqa: E712
        rows = q.order_by(ShiftType.name).all()
        return [_row_to_dict(r) for r in rows]


@router.post("/types", response_model=ShiftTypeOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_shift_type(
    request: Request,
    body: ShiftTypeCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import ShiftType, get_db

    with get_db()() as session:
        entry = ShiftType(user_key=user_key, **body.model_dump())
        session.add(entry)
        session.flush()
        session.refresh(entry)
        return _row_to_dict(entry)


@router.patch("/types/{type_id}", response_model=ShiftTypeOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_shift_type(
    request: Request,
    type_id: int,
    body: ShiftTypeUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import ShiftType, get_db

    with get_db()() as session:
        row = session.query(ShiftType).filter_by(id=type_id, user_key=user_key).first()
        if not row:
            raise HTTPException(status_code=404, detail="Diensttyp nicht gefunden.")
        updates = body.model_dump(exclude_unset=True)
        for key, val in updates.items():
            setattr(row, key, val)
        session.flush()
        session.refresh(row)
        return _row_to_dict(row)


@router.delete("/types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_shift_type(
    request: Request,
    type_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import ShiftEntry, ShiftType, get_db

    with get_db()() as session:
        row = session.query(ShiftType).filter_by(id=type_id, user_key=user_key).first()
        if not row:
            raise HTTPException(status_code=404, detail="Diensttyp nicht gefunden.")
        # Soft-Delete wenn Eintraege existieren
        has_entries = (
            session.query(ShiftEntry)
            .filter_by(shift_type_id=type_id, user_key=user_key)
            .first()
        )
        if has_entries:
            row.is_active = False
            session.flush()
        else:
            session.delete(row)


# ─── Shift Entries ───────────────────────────────────────────


@router.get("/entries", response_model=list[ShiftEntryOut])
async def list_shift_entries(
    user_key: Annotated[str, Depends(get_current_user)],
    start: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
):
    from src.services.database import ShiftEntry, ShiftType, get_db

    with get_db()() as session:
        rows = (
            session.query(ShiftEntry, ShiftType)
            .outerjoin(ShiftType, ShiftEntry.shift_type_id == ShiftType.id)
            .filter(
                ShiftEntry.user_key == user_key,
                ShiftEntry.date >= start,
                ShiftEntry.date <= end,
            )
            .order_by(ShiftEntry.date)
            .all()
        )
        return [_entry_with_type(entry, stype) for entry, stype in rows]


@router.post("/entries", response_model=ShiftEntryOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_shift_entry(
    request: Request,
    body: ShiftEntryCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import ShiftEntry, ShiftType, get_db

    with get_db()() as session:
        # Pruefen ob ShiftType existiert und dem User gehoert
        stype = (
            session.query(ShiftType)
            .filter_by(id=body.shift_type_id, user_key=user_key, is_active=True)
            .first()
        )
        if not stype:
            raise HTTPException(status_code=404, detail="Diensttyp nicht gefunden oder inaktiv.")

        entry = ShiftEntry(user_key=user_key, **body.model_dump())
        session.add(entry)
        session.flush()
        session.refresh(entry)
        return _entry_with_type(entry, stype)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_shift_entry(
    request: Request,
    entry_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import ShiftEntry, get_db

    with get_db()() as session:
        entry = session.query(ShiftEntry).filter_by(id=entry_id, user_key=user_key).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Diensteintrag nicht gefunden.")
        session.delete(entry)
