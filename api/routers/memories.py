"""GET /memories, GET /memories/search, DELETE /memories/{id} – Memory-Verwaltung"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_memory_service
from api.schemas.memories import MemoryListResponse, MemoryOut, MemorySearchResult
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=MemoryListResponse)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_memories(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    memory_svc=Depends(get_memory_service),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Gibt alle gespeicherten Memories zurueck (paginiert)."""
    all_memories = await memory_svc.get_all_memories(user_key=user_key)

    total = len(all_memories)
    page = all_memories[offset : offset + limit]

    items = [
        MemoryOut(
            id=str(m.get("id", "")),
            memory=m.get("memory", ""),
            created_at=m.get("created_at"),
        )
        for m in page
    ]
    return MemoryListResponse(items=items, total=total)


@router.get("/search", response_model=list[MemorySearchResult])
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def search_memories(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    memory_svc=Depends(get_memory_service),
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
):
    """Semantische Suche in den Memories via mem0."""
    results = await memory_svc.search_memories(user_key=user_key, query=q, limit=limit)

    return [
        MemorySearchResult(
            id=str(m.get("id", "")),
            memory=m.get("memory", ""),
            score=m.get("score"),
        )
        for m in results
    ]


@router.delete("/{memory_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_memory(
    request: Request,
    memory_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    memory_svc=Depends(get_memory_service),
):
    """Loescht eine einzelne Memory."""
    ok = await memory_svc.delete_memory(memory_id=memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory nicht gefunden.")
