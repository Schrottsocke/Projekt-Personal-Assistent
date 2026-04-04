"""Workspace-Zugriffskontrolle (Multi-Tenancy Dependency)."""

from typing import Annotated

from fastapi import Depends, HTTPException

from api.dependencies import get_current_user
from src.services.database import (
    get_db,
    HouseholdWorkspace,
    WorkspaceMember,
    UserProfile,
)


def get_workspace_access(
    workspace_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
) -> dict:
    """Prueft ob der aktuelle User Zugriff auf den Workspace hat.

    Returns:
        {"workspace": HouseholdWorkspace, "role": str, "user_id": int}
    Raises:
        HTTPException 403 wenn kein Zugriff.
        HTTPException 404 wenn Workspace nicht existiert.
    """
    with get_db()() as db:
        # user_key → user_id aufloesen
        profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
        if not profile:
            raise HTTPException(status_code=403, detail="User-Profil nicht gefunden.")

        workspace = db.query(HouseholdWorkspace).filter(HouseholdWorkspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace nicht gefunden.")

        # Owner?
        if workspace.owner_id == profile.id:
            return {"workspace": workspace, "role": "owner", "user_id": profile.id}

        # Member?
        member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == profile.id,
            )
            .first()
        )
        if member:
            return {"workspace": workspace, "role": member.role, "user_id": profile.id}

        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Workspace.")
