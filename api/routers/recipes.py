"""Rezepte: Chefkoch-Suche + gespeicherte Rezepte."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import (
    get_current_user,
    get_chefkoch_service,
    get_shopping_service,
)
from api.schemas.recipe import SavedRecipeCreate, SavedRecipeOut, ToShoppingRequest
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

CHEFKOCH_BASE = "https://www.chefkoch.de/rezepte"


def _parse_recipe(raw: dict) -> dict:
    """Normalisiert ein Chefkoch-API-Ergebnis."""
    item = raw.get("item", raw)
    rid = item.get("id", "")
    return {
        "chefkoch_id": str(rid),
        "title": item.get("title", ""),
        "image_url": (item.get("previewImageUrlTemplate") or "").replace("<format>", "400x300"),
        "prep_time": item.get("preparationTime") or 0,
        "cook_time": item.get("cookingTime") or 0,
        "difficulty": {1: "Einfach", 2: "Normal", 3: "Anspruchsvoll", 4: "Profi"}.get(item.get("difficulty", 0), ""),
        "rating": round(item.get("rating", {}).get("rating", 0.0), 1),
        "url": f"{CHEFKOCH_BASE}/{rid}/",
        "servings": item.get("servings") or 4,
        "ingredients": _extract_ingredients(item),
    }


def _extract_ingredients(recipe: dict) -> list[dict]:
    result = []
    for group in recipe.get("ingredientGroups", []):
        for ing in group.get("ingredients", []):
            result.append(
                {
                    "name": ing.get("name", ""),
                    "amount": ing.get("amount") or "",
                    "unit": ing.get("unit") or "",
                }
            )
    return result


@router.get("/search")
async def search_recipes(
    user_key: Annotated[str, Depends(get_current_user)],
    q: str = "",
    limit: int = 10,
    chefkoch_svc=Depends(get_chefkoch_service),
):
    if not q:
        return []
    results = await chefkoch_svc.search_recipes(q, limit=limit)
    return [_parse_recipe(r) for r in results]


@router.get("/saved", response_model=list[SavedRecipeOut])
async def list_saved(
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import SavedRecipe, get_db

    with get_db()() as session:
        rows = session.query(SavedRecipe).filter_by(user_key=user_key).all()
        result = [
            {c.name: getattr(r, c.name) for c in r.__table__.columns}
            for r in rows
        ]
    return result


@router.post("/saved", response_model=SavedRecipeOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def save_recipe(
    request: Request,
    body: SavedRecipeCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import SavedRecipe, get_db

    with get_db()() as session:
        rec = SavedRecipe(user_key=user_key, **body.model_dump())
        session.add(rec)
        session.flush()
        session.refresh(rec)
        result = {c.name: getattr(rec, c.name) for c in rec.__table__.columns}
    return result


@router.patch("/saved/{recipe_id}/favorite")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def toggle_favorite(
    request: Request,
    recipe_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import SavedRecipe, get_db

    with get_db()() as session:
        rec = session.query(SavedRecipe).filter_by(id=recipe_id, user_key=user_key).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Rezept nicht gefunden.")
        rec.is_favorite = not rec.is_favorite
        return {"id": rec.id, "is_favorite": rec.is_favorite}


@router.delete("/saved/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_saved(
    request: Request,
    recipe_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import SavedRecipe, get_db

    with get_db()() as session:
        rec = session.query(SavedRecipe).filter_by(id=recipe_id, user_key=user_key).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Rezept nicht gefunden.")
        session.delete(rec)


@router.get("/{chefkoch_id}")
async def get_recipe(
    chefkoch_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    chefkoch_svc=Depends(get_chefkoch_service),
):
    recipe = await chefkoch_svc.get_recipe(chefkoch_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden.")
    return _parse_recipe(recipe)


@router.post("/{chefkoch_id}/to-shopping")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def recipe_to_shopping(
    request: Request,
    chefkoch_id: str,
    body: ToShoppingRequest,
    user_key: Annotated[str, Depends(get_current_user)],
    chefkoch_svc=Depends(get_chefkoch_service),
    shopping_svc=Depends(get_shopping_service),
):
    recipe = await chefkoch_svc.get_recipe(chefkoch_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden.")
    count = await shopping_svc.add_items_from_recipe(user_key, recipe)
    return {"added": count, "recipe_title": recipe.get("title", "")}
