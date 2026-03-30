"""Shopping CRUD – eine Liste pro User (user_key)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import (
    get_current_user,
    get_shopping_service,
    get_chefkoch_service,
)
from api.schemas.shopping import ShoppingItemCreate, ShoppingItemOut, ShoppingItemUpdate
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/items", response_model=list[ShoppingItemOut])
async def get_items(
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
    include_checked: bool = False,
):
    return await shopping_svc.get_items(user_key, include_checked=include_checked)


@router.post("/items", response_model=ShoppingItemOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def add_item(
    request: Request,
    body: ShoppingItemCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
):
    return await shopping_svc.add_item(
        user_key=user_key,
        name=body.name,
        quantity=body.quantity,
        unit=body.unit,
        category=body.category,
        source="manual",
    )


@router.patch("/items/{item_id}", response_model=ShoppingItemOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_item(
    request: Request,
    item_id: int,
    body: ShoppingItemUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
):
    from src.services.database import ShoppingItem, get_db

    with get_db()() as session:
        db_item = session.query(ShoppingItem).filter_by(id=item_id, user_key=user_key).first()
        if not db_item:
            raise HTTPException(status_code=404, detail="Item nicht gefunden.")
        if body.quantity is not None:
            db_item.quantity = body.quantity
        if body.checked is not None:
            db_item.checked = not db_item.checked
        result = {c.name: getattr(db_item, c.name) for c in db_item.__table__.columns}
    return result


@router.delete("/items/checked", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def clear_checked(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
):
    await shopping_svc.clear_checked(user_key)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_item(
    request: Request,
    item_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
):
    ok = await shopping_svc.remove_item(user_key, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item nicht gefunden.")


@router.post("/from-recipe/{chefkoch_id}")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def add_from_recipe(
    request: Request,
    chefkoch_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
    chefkoch_svc=Depends(get_chefkoch_service),
    servings: int = Query(4, ge=1, le=100),
):
    """Lädt Rezept von Chefkoch und fügt Zutaten zur Einkaufsliste hinzu."""
    recipe = await chefkoch_svc.get_recipe(chefkoch_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden.")
    count = await shopping_svc.add_items_from_recipe(user_key, recipe, servings=servings)
    return {"added": count, "recipe_title": recipe.get("title", "")}
