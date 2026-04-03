"""GET/POST/PATCH /notifications"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_notification_service
from api.schemas.notification import (
    NotificationBulkUpdate,
    NotificationCreate,
    NotificationOut,
    NotificationStatusUpdate,
)
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    user_key: Annotated[str, Depends(get_current_user)],
    notif_svc=Depends(get_notification_service),
    type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    return await notif_svc.list(user_key, type_filter=type, status_filter=status, limit=limit, offset=offset)


@router.get("/count")
async def notification_count(
    user_key: Annotated[str, Depends(get_current_user)],
    notif_svc=Depends(get_notification_service),
):
    unread = await notif_svc.count_unread(user_key)
    return {"unread": unread}


@router.post("", response_model=NotificationOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_notification(
    request: Request,
    body: NotificationCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    notif_svc=Depends(get_notification_service),
):
    return await notif_svc.create(
        user_key=user_key,
        type=body.type,
        title=body.title,
        message=body.message,
        link=body.link,
    )


@router.patch("/bulk", response_model=dict)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def bulk_update_notifications(
    request: Request,
    body: NotificationBulkUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
    notif_svc=Depends(get_notification_service),
):
    count = await notif_svc.bulk_update_status(body.ids, user_key, body.status)
    return {"updated": count}


@router.post("/mark-all-read", response_model=dict)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def mark_all_read(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    notif_svc=Depends(get_notification_service),
):
    count = await notif_svc.mark_all_read(user_key)
    return {"updated": count}


@router.patch("/{notif_id}", response_model=NotificationOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_notification(
    request: Request,
    notif_id: int,
    body: NotificationStatusUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
    notif_svc=Depends(get_notification_service),
):
    result = await notif_svc.update_status(notif_id, user_key, body.status)
    if not result:
        raise HTTPException(status_code=404, detail="Notification nicht gefunden.")
    return result
