"""GET /sync/status, POST /sync/batch – Offline-Sync-Endpunkte."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.sync import (
    SyncBatchRequest,
    SyncBatchResponse,
    SyncOperationResult,
)
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/status")
async def sync_status(
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Gibt Sync-Status-Informationen zurueck."""
    return {
        "status": "ok",
        "server_time": __import__("datetime").datetime.utcnow().isoformat(),
        "user_key": user_key,
    }


@router.post("/batch", response_model=SyncBatchResponse, deprecated=True)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def sync_batch(
    request: Request,
    body: SyncBatchRequest,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Batch-Sync ist noch nicht implementiert (deprecated).

    Dieser Endpoint nimmt offline gepufferte Operationen entgegen, kann sie
    aber noch nicht verarbeiten. Bitte die jeweiligen Einzel-Endpunkte
    verwenden, bis der Batch-Dispatch vollstaendig implementiert ist.
    """
    raise HTTPException(
        status_code=501,
        detail="Batch-Sync ist noch nicht implementiert. Bitte Einzel-Endpunkte verwenden.",
    )
