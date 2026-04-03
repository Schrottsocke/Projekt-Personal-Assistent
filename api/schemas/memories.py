from pydantic import BaseModel
from typing import Optional


class MemoryOut(BaseModel):
    id: str
    memory: str
    created_at: Optional[str] = None


class MemorySearchResult(BaseModel):
    id: str
    memory: str
    score: Optional[float] = None


class MemoryListResponse(BaseModel):
    items: list[MemoryOut]
    total: int
