"""Feedback-Router: Bug-Reports, UX-Bewertungen und Triage fuer Beta-Tester."""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from config.settings import settings
from src.services.feedback_service import FeedbackService, VALID_TRIAGE_STATES

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

_service = FeedbackService()


# --- Schemas ---


class BugReportCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    area: Optional[str] = Field(None, description="Bereich: dashboard, shopping, calendar, etc.")
    expected: Optional[str] = Field(None, description="Erwartetes Verhalten")
    actual: Optional[str] = Field(None, description="Tatsaechliches Verhalten")
    steps: Optional[str] = Field(None, description="Schritte zum Reproduzieren")
    device: Optional[str] = Field(None, description="Geraet/Browser")
    severity: Optional[str] = Field(None, description="low / medium / high / critical")


class UxRatingCreate(BaseModel):
    area: Optional[str] = Field(None, description="Bewerteter Bereich")
    rating_clarity: Optional[int] = Field(None, ge=1, le=5, description="Verstaendlichkeit (1-5)")
    rating_speed: Optional[int] = Field(None, ge=1, le=5, description="Geschwindigkeit (1-5)")
    rating_trust: Optional[int] = Field(None, ge=1, le=5, description="Vertrauen (1-5)")
    rating_mobile_comfort: Optional[int] = Field(None, ge=1, le=5, description="Mobiler Komfort (1-5)")
    comment: Optional[str] = None


class TriageUpdate(BaseModel):
    status: str = Field(..., description=f"Neuer Status. Erlaubt: {', '.join(sorted(VALID_TRIAGE_STATES))}")


# --- Endpoints ---


@router.get("/health")
async def health():
    return {"status": "ok", "module": "feedback"}


@router.post("/bugs")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_bug_report(
    request: Request,
    body: BugReportCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Bug-Report einreichen."""
    result = _service.create_bug_report(
        user_key=user_key,
        title=body.title,
        area=body.area,
        expected=body.expected,
        actual=body.actual,
        steps=body.steps,
        device=body.device,
        severity=body.severity,
    )
    return result


@router.post("/ux")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_ux_rating(
    request: Request,
    body: UxRatingCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """UX-Bewertung abgeben."""
    result = _service.create_ux_rating(
        user_key=user_key,
        area=body.area,
        rating_clarity=body.rating_clarity,
        rating_speed=body.rating_speed,
        rating_trust=body.rating_trust,
        rating_mobile_comfort=body.rating_mobile_comfort,
        comment=body.comment,
    )
    return result


@router.get("")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_all_feedback(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    feedback_type: Optional[str] = None,
    triage_status: Optional[str] = None,
    limit: int = 100,
    own_only: bool = False,
):
    """Feedback-Eintraege abrufen. Ohne own_only=true werden alle angezeigt (Admin)."""
    items = _service.get_all(
        feedback_type=feedback_type,
        triage_status=triage_status,
        limit=limit,
    )
    if own_only:
        items = [i for i in items if i.get("user_key") == user_key]
    return items


@router.patch("/{feedback_id}/triage")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_triage(
    request: Request,
    feedback_id: int,
    body: TriageUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Triage-Status aendern."""
    try:
        result = _service.update_triage(feedback_id, body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="Feedback nicht gefunden.")
    return result
