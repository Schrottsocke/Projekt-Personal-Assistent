"""GET /sync/status, POST /sync/batch – Offline-Sync-Endpunkte."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
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


@router.post("/batch", response_model=SyncBatchResponse)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def sync_batch(
    request: Request,
    body: SyncBatchRequest,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Verarbeitet einen Batch von offline gepufferten Operationen.

    Jede Operation wird sequentiell ausgefuehrt. Bei Fehler wird die
    Operation als fehlgeschlagen markiert, die restlichen werden trotzdem
    versucht.
    """
    results: list[SyncOperationResult] = []
    processed = 0
    failed = 0

    for i, op in enumerate(body.operations):
        try:
            # Validierung: nur bekannte Methoden
            if op.method not in ("POST", "PATCH", "DELETE"):
                results.append(
                    SyncOperationResult(
                        index=i,
                        success=False,
                        error=f"Unbekannte Methode: {op.method}",
                    )
                )
                failed += 1
                continue

            # Phase 1: Batch-Dispatch nicht implementiert.
            # Explizit als nicht-implementiert markieren statt fake success.
            results.append(
                SyncOperationResult(
                    index=i,
                    success=False,
                    status_code=501,
                    error="Batch-Sync noch nicht implementiert. Bitte Einzel-Endpunkte verwenden.",
                )
            )
            failed += 1
        except Exception as e:
            results.append(
                SyncOperationResult(
                    index=i,
                    success=False,
                    error=str(e),
                )
            )
            failed += 1

    return SyncBatchResponse(
        processed=processed,
        failed=failed,
        results=results,
    )
