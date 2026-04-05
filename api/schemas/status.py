"""Pydantic-Schemas fuer Status-Endpunkte."""

from typing import Optional

from pydantic import BaseModel


class StatusResponse(BaseModel):
    api: str = "ok"
    timestamp: str
    uptime: str


class ServiceHealth(BaseModel):
    status: str
    error: Optional[str] = None
    response_ms: Optional[float] = None


class HealthResponse(BaseModel):
    services: dict[str, ServiceHealth] = {}
    overall: str = "healthy"
    uptime: str = ""
    commit: str = ""
    deployed_at: str = ""


class GitInfo(BaseModel):
    commit: str = "unknown"
    commit_full: str = "unknown"
    branch: str = "unknown"
    last_commit_msg: str = "unknown"
    last_commit_author: str = "unknown"
    last_commit_date: str = "unknown"
    remote_url: str = "unknown"
    local_changes: str = "none"


class ServiceDetail(BaseModel):
    active: bool = False
    last_logs: list[str] = []


class StatusDetailResponse(BaseModel):
    api: str = "ok"
    timestamp: str
    uptime: str
    git: GitInfo = GitInfo()
    services: dict[str, ServiceDetail] = {}
