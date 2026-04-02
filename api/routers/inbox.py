"""GET/POST /inbox – Zentrale Aktions-Inbox"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_inbox_service
from api.schemas.inbox import InboxAction, InboxItemCreate, InboxItemOut
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=list[InboxItemOut])
async def list_inbox(
    user_key: Annotated[str, Depends(get_current_user)],
    inbox_svc=Depends(get_inbox_service),
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    return await inbox_svc.list_items(user_key, status=status, category=category, limit=limit, offset=offset)


@router.get("/count")
async def inbox_count(
    user_key: Annotated[str, Depends(get_current_user)],
    inbox_svc=Depends(get_inbox_service),
):
    pending = await inbox_svc.count_pending(user_key)
    return {"pending": pending}


@router.post("", response_model=InboxItemOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def add_inbox_item(
    request: Request,
    body: InboxItemCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    inbox_svc=Depends(get_inbox_service),
):
    return await inbox_svc.add_item(user_key, body.model_dump())


@router.post("/{item_id}/action", response_model=InboxItemOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def action_inbox_item(
    request: Request,
    item_id: str,
    body: InboxAction,
    user_key: Annotated[str, Depends(get_current_user)],
    inbox_svc=Depends(get_inbox_service),
):
    result = await inbox_svc.action_item(user_key, item_id, body.action)
    if not result:
        raise HTTPException(status_code=404, detail="Inbox-Item nicht gefunden.")
    return result
