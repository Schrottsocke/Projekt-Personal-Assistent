"""Schemas fuer Offline-Sync."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class SyncOperation(BaseModel):
    """Eine einzelne gepufferte Schreiboperation."""

    method: str  # POST, PATCH, DELETE
    path: str
    body: Optional[dict[str, Any]] = None
    queued_at: datetime


class SyncBatchRequest(BaseModel):
    """Batch von Offline-gepufferten Operationen."""

    operations: list[SyncOperation]


class SyncOperationResult(BaseModel):
    """Ergebnis einer einzelnen Sync-Operation."""

    index: int
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None


class SyncBatchResponse(BaseModel):
    """Antwort auf einen Sync-Batch."""

    processed: int
    failed: int
    results: list[SyncOperationResult]
