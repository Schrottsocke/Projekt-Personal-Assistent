"""GET/POST/PATCH /followups"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_followup_service
from api.schemas.followups import FollowUpCreate, FollowUpOut, FollowUpUpdate
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=list[FollowUpOut])
async def list_followups(
    user_key: Annotated[str, Depends(get_current_user)],
    followup_svc=Depends(get_followup_service),
    status: Optional[str] = "open",
    limit: int = 50,
    offset: int = 0,
):
    return await followup_svc.list_followups(user_key, status=status or "", limit=limit, offset=offset)


@router.get("/due", response_model=list[FollowUpOut])
async def due_followups(
    user_key: Annotated[str, Depends(get_current_user)],
    followup_svc=Depends(get_followup_service),
):
    return await followup_svc.get_due_followups(user_key)


@router.post("", response_model=FollowUpOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_followup(
    request: Request,
    body: FollowUpCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    followup_svc=Depends(get_followup_service),
):
    return await followup_svc.create_followup(user_key, body.model_dump())


@router.patch("/{followup_id}", response_model=FollowUpOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_followup(
    request: Request,
    followup_id: str,
    body: FollowUpUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
    followup_svc=Depends(get_followup_service),
):
    result = await followup_svc.update_followup(
        user_key, followup_id, body.model_dump(exclude_unset=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Follow-up nicht gefunden.")
    return result
