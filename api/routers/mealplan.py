"""GET/POST/DELETE /meal-plan"""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_chefkoch_service, get_current_user, get_shopping_service
from api.schemas.mealplan import MealPlanCreate, MealPlanOut
from config.settings import settings

logger = logging.getLogger(__name__)

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
        result = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows]
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


@router.post("/week/to-shopping")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def week_to_shopping(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    start: str = "",
    chefkoch_svc=Depends(get_chefkoch_service),
    shopping_svc=Depends(get_shopping_service),
):
    """Alle Rezept-Zutaten einer Woche gesammelt zur Einkaufsliste hinzufuegen."""
    from datetime import datetime, timedelta
    from src.services.database import MealPlanEntry, get_db

    if not start:
        today = datetime.now()
        start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungueltiges Datum.")

    end_str = (start_dt + timedelta(days=6)).strftime("%Y-%m-%d")

    with get_db()() as session:
        rows = (
            session.query(MealPlanEntry)
            .filter(
                MealPlanEntry.user_key == user_key,
                MealPlanEntry.planned_date >= start,
                MealPlanEntry.planned_date <= end_str,
                MealPlanEntry.recipe_chefkoch_id.isnot(None),
                MealPlanEntry.recipe_chefkoch_id != "",
            )
            .all()
        )
        meal_entries = [
            {
                "chefkoch_id": r.recipe_chefkoch_id,
                "servings": r.servings or 4,
                "title": r.recipe_title,
            }
            for r in rows
        ]

    if not meal_entries:
        return {"added": 0, "merged": 0, "recipes_processed": 0, "skipped": 0}

    # Rezepte parallel laden (max 3 concurrent)
    sem = asyncio.Semaphore(3)
    all_items = []
    processed = 0
    skipped = 0

    async def fetch_and_extract(entry):
        nonlocal processed, skipped
        async with sem:
            try:
                recipe = await chefkoch_svc.get_recipe(entry["chefkoch_id"])
                if not recipe:
                    skipped += 1
                    return

                original_servings = recipe.get("servings") or 4
                scale = entry["servings"] / float(original_servings) if original_servings else 1.0

                for group in recipe.get("ingredientGroups", []):
                    for ing in group.get("ingredients", []):
                        name = ing.get("name", "").strip()
                        if not name:
                            continue
                        amount = ing.get("amount", "")
                        unit = ing.get("unit", "")
                        scaled_amount = amount
                        if amount and scale != 1.0:
                            try:
                                num = round(float(amount) * scale, 2)
                                scaled_amount = int(num) if num == int(num) else num
                            except (ValueError, TypeError):
                                scaled_amount = amount
                        all_items.append({
                            "name": name,
                            "quantity": str(scaled_amount) if scaled_amount else None,
                            "unit": unit or None,
                            "source": f"mealplan:chefkoch:{entry['chefkoch_id']}",
                        })
                processed += 1
            except Exception as exc:
                logger.warning("Rezept %s konnte nicht geladen werden: %s", entry["chefkoch_id"], exc)
                skipped += 1

    await asyncio.gather(*(fetch_and_extract(e) for e in meal_entries))

    result = {"added": 0, "merged": 0}
    if all_items:
        result = await shopping_svc.add_items_bulk(user_key, all_items)

    return {
        "added": result["added"],
        "merged": result["merged"],
        "recipes_processed": processed,
        "skipped": skipped,
    }
