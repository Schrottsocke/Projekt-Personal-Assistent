"""GET/POST/PATCH/DELETE /templates – Wiederverwendbare Vorlagen & Routinen."""

import logging
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import (
    get_current_user,
    get_shopping_service,
    get_task_service,
    get_template_service,
)
from api.schemas.templates import (
    ApplyResult,
    FromShoppingCreate,
    TemplateCreate,
    TemplateOut,
    TemplateUpdate,
)
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=list[TemplateOut])
async def list_templates(
    user_key: Annotated[str, Depends(get_current_user)],
    tpl_svc=Depends(get_template_service),
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    return await tpl_svc.list_templates(user_key, category=category, limit=limit, offset=offset)


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(
    template_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    tpl_svc=Depends(get_template_service),
):
    tpl = await tpl_svc.get_template(user_key, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")
    return tpl


@router.post("", response_model=TemplateOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_template(
    request: Request,
    body: TemplateCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    tpl_svc=Depends(get_template_service),
):
    data = body.model_dump()
    return await tpl_svc.create_template(user_key, data)


@router.patch("/{template_id}", response_model=TemplateOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_template(
    request: Request,
    template_id: str,
    body: TemplateUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
    tpl_svc=Depends(get_template_service),
):
    updates = body.model_dump(exclude_unset=True)
    result = await tpl_svc.update_template(user_key, template_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")
    return result


@router.delete("/{template_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_template(
    request: Request,
    template_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    tpl_svc=Depends(get_template_service),
):
    deleted = await tpl_svc.delete_template(user_key, template_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")


# ── Apply ────────────────────────────────────────────────────────────


@router.post("/{template_id}/apply", response_model=ApplyResult)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def apply_template(
    request: Request,
    template_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    tpl_svc=Depends(get_template_service),
    shopping_svc=Depends(get_shopping_service),
    task_svc=Depends(get_task_service),
):
    """Wendet eine Vorlage an und erstellt die entsprechenden Eintraege."""
    tpl = await tpl_svc.apply_template(user_key, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")

    category = tpl.get("category", "")
    content = tpl.get("content", {})
    created_items: list[dict] = []
    message = ""

    if category == "shopping":
        created_items, message = await _apply_shopping(user_key, content, shopping_svc)
    elif category == "task":
        created_items, message = await _apply_task(user_key, content, task_svc)
    elif category == "checklist":
        created_items, message = await _apply_checklist(user_key, content, task_svc)
    elif category == "mealplan":
        created_items, message = await _apply_mealplan(user_key, content)
    elif category == "routine":
        steps = content.get("steps", [])
        message = f"Routine mit {len(steps)} Schritten geladen"
    elif category == "message":
        message = "Nachricht bereit zum Senden"

    return ApplyResult(template=tpl, created_items=created_items, message=message)


async def _apply_shopping(user_key: str, content: dict, shopping_svc) -> tuple[list[dict], str]:
    items = content.get("items", [])
    if not items:
        return [], "Keine Artikel in der Vorlage"
    created = []
    for item in items:
        name = item.get("name", "").strip()
        if not name:
            continue
        result = await shopping_svc.add_item(
            user_key=user_key,
            name=name,
            quantity=item.get("quantity"),
            unit=item.get("unit"),
            source="template",
        )
        created.append(result)
    return created, f"{len(created)} Artikel zur Einkaufsliste hinzugefuegt"


async def _apply_task(user_key: str, content: dict, task_svc) -> tuple[list[dict], str]:
    title = content.get("title", "").strip()
    if not title:
        return [], "Kein Titel in der Vorlage"
    result = await task_svc.create_task(
        user_key=user_key,
        title=title,
        priority=content.get("priority", "medium"),
        description=content.get("description", ""),
        recurrence=content.get("recurrence"),
    )
    return [result], f"Aufgabe erstellt: {title}"


async def _apply_checklist(user_key: str, content: dict, task_svc) -> tuple[list[dict], str]:
    items = content.get("items", [])
    if not items:
        return [], "Keine Eintraege in der Checkliste"
    created = []
    for item in items:
        title = item if isinstance(item, str) else item.get("title", "")
        if not title.strip():
            continue
        result = await task_svc.create_task(
            user_key=user_key,
            title=title.strip(),
            priority="low",
        )
        created.append(result)
    return created, f"{len(created)} Aufgaben aus Checkliste erstellt"


async def _apply_mealplan(user_key: str, content: dict) -> tuple[list[dict], str]:
    from src.services.database import MealPlanEntry, get_db

    recipe_title = content.get("recipe_title", "").strip()
    if not recipe_title:
        return [], "Kein Rezepttitel in der Vorlage"
    planned_date = content.get("planned_date") or date.today().isoformat()
    with get_db()() as session:
        entry = MealPlanEntry(
            user_key=user_key,
            planned_date=planned_date,
            recipe_title=recipe_title,
            recipe_chefkoch_id=content.get("recipe_chefkoch_id"),
            recipe_image_url=content.get("recipe_image_url"),
            meal_type=content.get("meal_type", "dinner"),
            servings=content.get("servings", 4),
            notes=content.get("notes"),
        )
        session.add(entry)
        session.flush()
        result = {c.name: getattr(entry, c.name) for c in entry.__table__.columns}
    return [result], f"Wochenplan-Eintrag erstellt: {recipe_title}"


# ── Save as Template ─────────────────────────────────────────────────


@router.post("/from-shopping", response_model=TemplateOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_from_shopping(
    request: Request,
    body: FromShoppingCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    tpl_svc=Depends(get_template_service),
    shopping_svc=Depends(get_shopping_service),
):
    """Erstellt eine Vorlage aus der aktuellen Einkaufsliste."""
    items_raw = await shopping_svc.get_items(user_key, include_checked=False)
    if not items_raw:
        raise HTTPException(status_code=400, detail="Einkaufsliste ist leer.")
    items = [{"name": it["name"], "quantity": it.get("quantity", ""), "unit": it.get("unit", "")} for it in items_raw]
    data = {
        "name": body.name,
        "category": "shopping",
        "description": body.description,
        "content": {"items": items},
    }
    return await tpl_svc.create_template(user_key, data)


@router.post("/from-task/{task_id}", response_model=TemplateOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_from_task(
    request: Request,
    task_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
    tpl_svc=Depends(get_template_service),
    task_svc=Depends(get_task_service),
):
    """Erstellt eine Vorlage aus einem bestehenden Task."""
    tasks = await task_svc.get_all_tasks(user_key)
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task nicht gefunden.")
    data = {
        "name": f"Vorlage: {task['title']}",
        "category": "task",
        "description": "",
        "content": {
            "title": task["title"],
            "description": task.get("description", ""),
            "priority": task.get("priority", "medium"),
            "recurrence": task.get("recurrence"),
        },
    }
    return await tpl_svc.create_template(user_key, data)
