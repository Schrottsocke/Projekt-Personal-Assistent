"""GET /email/inbox – E-Mail-Posteingang, GET /email/{id} – Einzelne Mail."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_email_service
from api.schemas.email import EmailDetail, EmailHealthResponse, EmailSummary
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.get("/health", response_model=EmailHealthResponse)
async def health():
    return {"status": "ok"}


@router.get("/inbox", response_model=list[EmailSummary])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_inbox(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    limit: int = 20,
    unread_only: bool = False,
    email_svc=Depends(get_email_service),
):
    """Liste der E-Mails im Posteingang."""
    if not email_svc.is_connected(user_key):
        raise HTTPException(status_code=503, detail="Gmail nicht verbunden")

    emails = await email_svc.get_inbox(user_key, limit=limit, unread_only=unread_only)
    return emails


@router.get("/{email_id}", response_model=EmailDetail)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_email(
    request: Request,
    email_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    email_svc=Depends(get_email_service),
):
    """Einzelne E-Mail mit vollem Body abrufen."""
    if not email_svc.is_connected(user_key):
        raise HTTPException(status_code=503, detail="Gmail nicht verbunden")

    email = await email_svc.get_email(user_key, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="E-Mail nicht gefunden")
    return email
