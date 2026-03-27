"""Shopping CRUD – eine Liste pro User (user_key)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import (
    get_current_user,
    get_shopping_service,
    get_chefkoch_service,
)
from api.schemas.shopping import ShoppingItemCreate, ShoppingItemOut, ShoppingItemUpdate

router = APIRouter()


@router.get("/items", response_model=list[ShoppingItemOut])
async def get_items(
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
    include_checked: bool = False,
):
    return await shopping_svc.get_items(user_key, include_checked=include_checked)


@router.post("/items", response_model=ShoppingItemOut, status_code=status.HTTP_201_CREATED)
async def add_item(
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
async def update_item(
    item_id: int,
    body: ShoppingItemUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
):
    if body.checked is not None:
        ok = await shopping_svc.check_item(user_key, item_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Item nicht gefunden.")
    items = await shopping_svc.get_items(user_key, include_checked=True)
    item = next((i for i in items if i["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item nicht gefunden.")
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
):
    ok = await shopping_svc.remove_item(user_key, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item nicht gefunden.")


@router.delete("/items/checked", status_code=status.HTTP_204_NO_CONTENT)
async def clear_checked(
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
):
    await shopping_svc.clear_checked(user_key)


@router.post("/from-recipe/{chefkoch_id}")
async def add_from_recipe(
    chefkoch_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    shopping_svc=Depends(get_shopping_service),
    chefkoch_svc=Depends(get_chefkoch_service),
    servings: int = 4,
):
    """Lädt Rezept von Chefkoch und fügt Zutaten zur Einkaufsliste hinzu."""
    recipe = await chefkoch_svc.get_recipe(chefkoch_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Rezept nicht gefunden.")
    count = await shopping_svc.add_items_from_recipe(user_key, recipe)
    return {"added": count, "recipe_title": recipe.get("title", "")}
