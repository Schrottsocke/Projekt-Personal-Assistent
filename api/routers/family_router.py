"""Family-Router: Workspaces, Members, Routines."""

from fastapi import APIRouter

from src.services.database import (  # noqa: F401
    HouseholdWorkspace,
    WorkspaceMember,
    Routine,
    RoutineCompletion,
)

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "module": "family"}
