"""GET/POST/PATCH/DELETE /automation – Regel- und Automationscenter"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_automation_service
from api.schemas.automation import AutomationRuleCreate, AutomationRuleOut, AutomationRuleUpdate
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=list[AutomationRuleOut])
async def list_rules(
    user_key: Annotated[str, Depends(get_current_user)],
    auto_svc=Depends(get_automation_service),
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    return await auto_svc.list_rules(user_key, active_only=active_only, limit=limit, offset=offset)


@router.post("", response_model=AutomationRuleOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_rule(
    request: Request,
    body: AutomationRuleCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    auto_svc=Depends(get_automation_service),
):
    return await auto_svc.create_rule(user_key, body.model_dump())


@router.patch("/{rule_id}", response_model=AutomationRuleOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_rule(
    request: Request,
    rule_id: str,
    body: AutomationRuleUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
    auto_svc=Depends(get_automation_service),
):
    updates = body.model_dump(exclude_unset=True)
    result = await auto_svc.update_rule(user_key, rule_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Regel nicht gefunden.")
    return result


@router.post("/{rule_id}/toggle", response_model=AutomationRuleOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def toggle_rule(
    request: Request,
    rule_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    auto_svc=Depends(get_automation_service),
):
    result = await auto_svc.toggle_rule(user_key, rule_id)
    if not result:
        raise HTTPException(status_code=404, detail="Regel nicht gefunden.")
    return result


@router.delete("/{rule_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_rule(
    request: Request,
    rule_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    auto_svc=Depends(get_automation_service),
):
    deleted = await auto_svc.delete_rule(user_key, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Regel nicht gefunden.")
