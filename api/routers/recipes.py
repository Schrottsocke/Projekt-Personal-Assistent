"""Rezepte: Chefkoch-Suche + gespeicherte Rezepte + Bild-Proxy."""

import hashlib
import logging
import re
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import (
    get_current_user,
    get_chefkoch_service,
    get_shopping_service,
)
from api.schemas.recipe import SavedRecipeCreate, SavedRecipeOut, SelectedIngredientsRequest, ToShoppingRequest
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

CHEFKOCH_BASE = "https://www.chefkoch.de/rezepte"
_CHEFKOCH_CDN = "https://img.chefkoch-cdn.de"
_ALLOWED_CDN_RE = re.compile(r"^https://img\.chefkoch-cdn\.de/")

# NOTE: Update Chrome version periodically to avoid CDN rejection.
_CDN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.chefkoch.de/",
    "Sec-Fetch-Dest": "image",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Ch-Ua": '"Chromium";v="135", "Google Chrome";v="135", "Not-A.Brand";v="8"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


def _to_proxy_url(original_url: str) -> str:
    """Wandelt eine Chefkoch-CDN-URL in eine lokale Proxy-URL um."""
    if not original_url or not _ALLOWED_CDN_RE.match(original_url):
        return original_url
    path = original_url.replace(_CHEFKOCH_CDN, "", 1)
    return f"/recipes/img-proxy{path}"


def _parse_recipe(raw: dict) -> dict:
    """Normalisiert ein Chefkoch-API-Ergebnis."""
    item = raw.get("recipe", raw.get("item", raw))
    rid = item.get("id", "")
    direct_url = (item.get("previewImageUrlTemplate") or "").replace("<format>", "crop-400x300")
    return {
        "chefkoch_id": str(rid),
        "title": item.get("title", ""),
        "image_url": _to_proxy_url(direct_url),
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
    limit: int = Query(10, ge=1, le=50),
    chefkoch_svc=Depends(get_chefkoch_service),
):
    if not q:
        return []
    results = await chefkoch_svc.search_recipes(q, limit=limit)
    if results is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chefkoch-API nicht erreichbar.",
        )
    return [_parse_recipe(r) for r in results]


@router.get("/saved", response_model=list[SavedRecipeOut])
async def list_saved(
    user_key: Annotated[str, Depends(get_current_user)],
):
    from src.services.database import SavedRecipe, get_db

    with get_db()() as session:
        rows = session.query(SavedRecipe).filter_by(user_key=user_key).all()
        result = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows]
    for item in result:
        if item.get("image_url"):
            item["image_url"] = _to_proxy_url(item["image_url"])
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


@router.get("/img-proxy/{path:path}")
@limiter.limit("60/minute")
async def image_proxy(request: Request, path: str):
    """Proxied Chefkoch-CDN-Bilder um Hotlinking-Schutz zu umgehen."""
    if not re.match(r"^rezepte/\d+/bilder/\d+/crop-\d+x\d+$", path):
        raise HTTPException(status_code=400, detail="Ungültiger Bildpfad.")

    upstream = f"{_CHEFKOCH_CDN}/{path}"
    logger.debug("Image proxy fetch: %s", upstream)
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(upstream, headers=_CDN_HEADERS)
        if resp.status_code != 200:
            logger.warning(
                "CDN returned %s for %s – body: %s",
                resp.status_code,
                upstream,
                resp.content[:200],
            )
            raise HTTPException(status_code=resp.status_code, detail="Bild nicht verfügbar.")
        ct = resp.headers.get("content-type", "image/jpeg")
        etag = hashlib.md5(path.encode()).hexdigest()  # noqa: S324
        return Response(
            content=resp.content,
            media_type=ct,
            headers={
                "Cache-Control": "public, max-age=86400",
                "ETag": f'"{etag}"',
            },
        )
    except httpx.HTTPError as exc:
        logger.warning("CDN request failed for %s: %s", upstream, exc)
        raise HTTPException(status_code=502, detail="Chefkoch-CDN nicht erreichbar.")


@router.post("/ingredients-to-shopping")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def selected_ingredients_to_shopping(
    request: Request,
    body: SelectedIngredientsRequest,
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
):
    """Uebernimmt vorselektierte Zutaten direkt in die Einkaufsliste."""
    items = [
        {"name": ing.name, "quantity": ing.amount, "unit": ing.unit, "source": "recipe"} for ing in body.ingredients
    ]
    result = await shopping_svc.add_items_bulk(user_key, items)
    return {"added": result["added"], "merged": result["merged"]}


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
    result = await shopping_svc.add_items_from_recipe(user_key, recipe, servings=body.servings)
    return {"added": result["added"], "merged": result["merged"], "recipe_title": recipe.get("title", "")}
