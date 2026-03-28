"""GET/POST/DELETE /meal-plan"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.mealplan import MealPlanCreate, MealPlanOut
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/week", response_model=list[MealPlanOut])
async def get_week(
    user_key: Annotated[str, Depends(get_current_user)],
    start: str = "",  # YYYY-MM-DD, leer = aktuelle Woche
):
    from src.services.database import MealPlanEntry, get_db
    from datetime import datetime, timedelta

    if not start:
        today = datetime.now()
        # Montag der aktuellen Woche
        start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungültiges Datum (YYYY-MM-DD erwartet).")

    end_dt = start_dt + timedelta(days=6)
    end_str = end_dt.strftime("%Y-%m-%d")

    with get_db()() as session:
        rows = (
            session.query(MealPlanEntry)
            .filter(
                MealPlanEntry.user_key == user_key,
                MealPlanEntry.planned_date >= start,
                MealPlanEntry.planned_date <= end_str,
            )
            .order_by(MealPlanEntry.planned_date, MealPlanEntry.meal_type)
            .all()
        )
        result = [
            {c.name: getattr(r, c.name) for c in r.__table__.columns}
            for r in rows
        ]
    return result


@router.post("", response_model=MealPlanOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def add_meal(
    request: Request,
    body: MealPlanCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import MealPlanEntry, get_db

    with get_db()() as session:
        entry = MealPlanEntry(user_key=user_key, **body.model_dump())
        session.add(entry)
        session.flush()
        session.refresh(entry)
        result = {c.name: getattr(entry, c.name) for c in entry.__table__.columns}
    return result


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_meal(
    request: Request,
    entry_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import MealPlanEntry, get_db

    with get_db()() as session:
        entry = session.query(MealPlanEntry).filter_by(id=entry_id, user_key=user_key).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Eintrag nicht gefunden.")
        session.delete(entry)
