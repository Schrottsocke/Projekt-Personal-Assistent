"""Monitoring-Router: Beta-Start KPIs, Event-Tracking und Fehler-Uebersicht."""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from config.settings import settings
from src.services.monitoring_service import MonitoringService, VALID_EVENT_TYPES

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

_service = MonitoringService()


# --- Schemas ---


class EventCreate(BaseModel):
    event_type: str = Field(..., description=f"Event-Typ. Erlaubt: {', '.join(sorted(VALID_EVENT_TYPES))}")
    user_key: Optional[str] = None
    metadata: Optional[str] = None


class EventOut(BaseModel):
    id: int
    event_type: str
    user_key: Optional[str] = None
    metadata: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ErrorCreate(BaseModel):
    source: str = Field(..., description="Fehler-Quelle: 'frontend' oder 'backend'")
    message: str
    stack_trace: Optional[str] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None


class ErrorOut(BaseModel):
    id: int
    source: str
    message: str
    stack_trace: Optional[str] = None
    user_key: Optional[str] = None
    url: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class MonitoringHealthOut(BaseModel):
    status: str
    module: str


class MonitoringMetrics(BaseModel):
    activation_rate: float = 0.0
    login_rate: float = 0.0
    onboarding_rate: float = 0.0


class MonitoringErrors(BaseModel):
    total: int = 0
    last_24h: int = 0


class MonitoringDashboardOut(BaseModel):
    event_counts: dict[str, int] = {}
    total_events: int = 0
    metrics: MonitoringMetrics = MonitoringMetrics()
    errors: MonitoringErrors = MonitoringErrors()


# --- Endpoints ---


@router.get("/health", response_model=MonitoringHealthOut)
async def health():
    return {"status": "ok", "module": "monitoring"}


@router.get("/dashboard", response_model=MonitoringDashboardOut)
async def get_dashboard(user_key: Annotated[str, Depends(get_current_user)]):
    """KPIs und Aktivierungsmetriken abrufen."""
    return _service.get_dashboard()


@router.post("/events", status_code=201, response_model=EventOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def track_event(
    request: Request,
    body: EventCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Monitoring-Event erfassen."""
    try:
        result = _service.track_event(
            event_type=body.event_type,
            user_key=body.user_key or user_key,
            metadata=body.metadata,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/errors", status_code=201, response_model=ErrorOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def log_error(
    request: Request,
    body: ErrorCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Frontend- oder Backend-Fehler erfassen."""
    result = _service.log_error(
        source=body.source,
        message=body.message,
        stack_trace=body.stack_trace,
        user_key=user_key,
        url=body.url,
        user_agent=body.user_agent,
    )
    return result


@router.get("/errors", response_model=list[ErrorOut])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_errors(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    limit: int = 50,
    source: Optional[str] = None,
):
    """Fehler-Uebersicht abrufen."""
    return _service.get_errors(limit=limit, source=source)


@router.get("/events", response_model=list[EventOut])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_events(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    event_type: Optional[str] = None,
    limit: int = 100,
):
    """Events abrufen, optional nach Typ gefiltert."""
    return _service.get_events(event_type=event_type, limit=limit)
