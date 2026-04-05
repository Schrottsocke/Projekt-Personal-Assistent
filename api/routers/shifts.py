"""CRUD /shifts/types und /shifts/entries – Dienstplan-Verwaltung + Tracking."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_shift_tracking_service
from api.schemas.shift import (
    ShiftConfirmRequest,
    ShiftEntryCreate,
    ShiftEntryOut,
    ShiftEntryUpdate,
    ShiftReportOut,
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
            if not stype:
                continue
            st = entry.planned_start or stype.start_time or "00:00"
            et = entry.planned_end or stype.end_time or "23:59"
            summary = f"{stype.name} ({stype.short_name})"
            note = entry.note or stype.default_note or ""
            conf_status = entry.confirmation_status or "pending"
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
                    "confirmation_status": conf_status,
                    "actual_start": entry.actual_start,
                    "actual_end": entry.actual_end,
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
        # Atomar: Eintraege zaehlen und entscheiden in einer Transaktion.
        # SQLite serialisiert Writes; bei PostgreSQL-Migration .with_for_update() auf ShiftType ergaenzen.
        entry_count = session.query(ShiftEntry).filter_by(shift_type_id=type_id, user_key=user_key).count()
        if entry_count > 0:
            row.is_active = False
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
        stype = session.query(ShiftType).filter_by(id=body.shift_type_id, user_key=user_key, is_active=True).first()
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


# ─── Shift Tracking ─────────────────────────────────────────


@router.patch("/entries/{entry_id}", response_model=ShiftEntryOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_shift_entry(
    request: Request,
    entry_id: int,
    body: ShiftEntryUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
    svc=Depends(get_shift_tracking_service),
):
    """Manuelle Bearbeitung eines Diensteintrags (Ist-Zeiten, Status, Notizen)."""
    try:
        updates = body.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=400, detail="Keine Aenderungen angegeben.")
        return svc.update_entry(entry_id, user_key, updates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/entries/{entry_id}/confirm", status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def confirm_shift_entry(
    request: Request,
    entry_id: int,
    body: ShiftConfirmRequest,
    user_key: Annotated[str, Depends(get_current_user)],
    svc=Depends(get_shift_tracking_service),
):
    """Quick-Confirm: Dienst bestaetigen, Abweichung melden, snoozen oder absagen."""
    try:
        if body.action == "confirm":
            return svc.confirm_shift(entry_id, user_key, source="web")
        elif body.action == "deviation":
            if not body.actual_start or not body.actual_end:
                raise HTTPException(status_code=400, detail="actual_start und actual_end sind Pflicht bei Abweichung.")
            return svc.record_deviation(
                entry_id,
                user_key,
                actual_start=body.actual_start,
                actual_end=body.actual_end,
                actual_break=body.actual_break_minutes or 0,
                note=body.deviation_note,
                source="web",
            )
        elif body.action == "cancel":
            return svc.cancel_shift(entry_id, user_key, source="web")
        elif body.action == "snooze":
            return svc.snooze_reminder(entry_id, user_key, minutes=body.snooze_minutes)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/report", response_model=ShiftReportOut)
async def get_shift_report(
    user_key: Annotated[str, Depends(get_current_user)],
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="YYYY-MM"),
    svc=Depends(get_shift_tracking_service),
):
    """Soll/Ist-Monatsauswertung."""
    year, m = map(int, month.split("-"))
    return svc.get_monthly_report(user_key, year, m)


@router.get("/report/csv")
async def get_shift_report_csv(
    user_key: Annotated[str, Depends(get_current_user)],
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="YYYY-MM"),
    svc=Depends(get_shift_tracking_service),
):
    """CSV-Export der Monatsauswertung."""
    year, m = map(int, month.split("-"))
    csv_content = svc.generate_csv(user_key, year, m)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="dienstzeiten_{month}.csv"'},
    )


@router.get("/pending", response_model=list[ShiftEntryOut])
async def get_pending_shifts(
    user_key: Annotated[str, Depends(get_current_user)],
    svc=Depends(get_shift_tracking_service),
):
    """Alle offenen (noch nicht bestaetigten) Dienste."""
    return svc.get_pending_shifts(user_key)
