"""GET/POST/PATCH/DELETE /templates – Wiederverwendbare Vorlagen & Routinen."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_template_service
from api.schemas.templates import TemplateCreate, TemplateOut, TemplateUpdate
from config.settings import settings

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


@router.post("/{template_id}/apply", response_model=TemplateOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def apply_template(
    request: Request,
    template_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    tpl_svc=Depends(get_template_service),
):
    """Wendet eine Vorlage an (gibt Inhalt zurueck, erhoeht Zaehler)."""
    result = await tpl_svc.apply_template(user_key, template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")
    return result
