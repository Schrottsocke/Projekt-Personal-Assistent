"""Family-Router: Workspaces, Members, Routines."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.family import (
    MemberRoleUpdate,
    RoutineCompletionCreate,
    RoutineCompletionOut,
    RoutineCreate,
    RoutineOut,
    RoutineUpdate,
    WorkspaceCreate,
    WorkspaceDetail,
    WorkspaceMemberAdd,
    WorkspaceMemberOut,
    WorkspaceOut,
)
from config.settings import settings
from src.services.database import (
    HouseholdWorkspace,
    Routine,
    RoutineCompletion,
    UserProfile,
    WorkspaceMember,
    get_db,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _resolve_user_id(db, user_key: str) -> int:
    profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User-Profil nicht gefunden.")
    return profile.id


# --- Widget Summary ---


@router.get("/widget-summary")
async def widget_summary(user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)

        # Find user's workspaces (owned or member)
        owned = db.query(HouseholdWorkspace).filter(HouseholdWorkspace.owner_id == uid).all()
        member_ws_ids = [m.workspace_id for m in db.query(WorkspaceMember).filter(WorkspaceMember.user_id == uid).all()]
        all_ws_ids = list({w.id for w in owned} | set(member_ws_ids))

        # Today's routines assigned to user
        todays_routines = []
        next_routine_due = None
        if all_ws_ids:
            routines = (
                db.query(Routine).filter(Routine.workspace_id.in_(all_ws_ids), Routine.current_assignee_id == uid).all()
            )
            for r in routines:
                todays_routines.append({"name": r.name, "interval": r.interval})
            # Next routine (any assignee) in user's workspaces
            any_routine = db.query(Routine).filter(Routine.workspace_id.in_(all_ws_ids)).first()
            if any_routine:
                next_routine_due = any_routine.name

        return {
            "todays_routines": todays_routines,
            "workspace_count": len(all_ws_ids),
            "next_routine_due": next_routine_due,
        }


def _check_workspace_access(db, workspace_id: int, user_id: int) -> HouseholdWorkspace:
    ws = db.query(HouseholdWorkspace).filter(HouseholdWorkspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(404, "Workspace nicht gefunden.")
    if ws.owner_id == user_id:
        return ws
    member = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(403, "Kein Zugriff auf diesen Workspace.")
    return ws


def _get_member_role(db, workspace_id: int, user_id: int, ws: HouseholdWorkspace) -> str:
    if ws.owner_id == user_id:
        return "owner"
    member = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        .first()
    )
    return member.role if member else "none"


@router.get("/health")
async def health():
    return {"status": "ok", "module": "family"}


# --- Workspaces (#651) ---


@router.post("/workspaces", response_model=WorkspaceOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_workspace(
    request: Request,
    body: WorkspaceCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        ws = HouseholdWorkspace(name=body.name, owner_id=uid)
        db.add(ws)
        db.flush()
        db.refresh(ws)
        return ws


@router.get("/workspaces", response_model=list[WorkspaceOut])
async def list_workspaces(user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        owned = db.query(HouseholdWorkspace).filter(HouseholdWorkspace.owner_id == uid).all()
        member_ws_ids = [m.workspace_id for m in db.query(WorkspaceMember).filter(WorkspaceMember.user_id == uid).all()]
        member_ws = (
            db.query(HouseholdWorkspace).filter(HouseholdWorkspace.id.in_(member_ws_ids)).all() if member_ws_ids else []
        )
        seen = set()
        result = []
        for w in owned + member_ws:
            if w.id not in seen:
                seen.add(w.id)
                result.append(w)
        return result


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceDetail)
async def get_workspace(workspace_id: int, user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        ws = _check_workspace_access(db, workspace_id, uid)
        members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()
        routine_count = db.query(Routine).filter(Routine.workspace_id == workspace_id).count()
        return WorkspaceDetail(workspace=ws, members=members, routine_count=routine_count)


# --- Members (#651) ---


@router.get("/workspaces/{workspace_id}/members", response_model=list[WorkspaceMemberOut])
async def list_members(
    workspace_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Alle Mitglieder eines Workspaces auflisten."""
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        _check_workspace_access(db, workspace_id, uid)
        return (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.workspace_id == workspace_id)
            .all()
        )


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=WorkspaceMemberOut,
    status_code=201,
)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def add_member(
    request: Request,
    workspace_id: int,
    body: WorkspaceMemberAdd,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        ws = _check_workspace_access(db, workspace_id, uid)
        role = _get_member_role(db, workspace_id, uid, ws)
        if role not in ("owner", "admin"):
            raise HTTPException(403, "Nur Owner oder Admin können Mitglieder hinzufügen.")
        target = db.query(UserProfile).filter(UserProfile.user_key == body.user_key).first()
        if not target:
            raise HTTPException(404, "Eingeladener User nicht gefunden.")
        existing = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == target.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(409, "User ist bereits Mitglied.")
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=target.id,
            role=body.role,
        )
        db.add(member)
        db.flush()
        db.refresh(member)
        return member


@router.delete("/workspaces/{workspace_id}/members/{member_user_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def remove_member(
    request: Request,
    workspace_id: int,
    member_user_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        ws = _check_workspace_access(db, workspace_id, uid)
        role = _get_member_role(db, workspace_id, uid, ws)
        if role not in ("owner", "admin"):
            raise HTTPException(403, "Nur Owner oder Admin können Mitglieder entfernen.")
        member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == member_user_id,
            )
            .first()
        )
        if not member:
            raise HTTPException(404, "Mitglied nicht gefunden.")
        db.delete(member)


@router.patch(
    "/workspaces/{workspace_id}/members/{member_user_id}",
    response_model=WorkspaceMemberOut,
)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_member_role(
    request: Request,
    workspace_id: int,
    member_user_id: int,
    body: MemberRoleUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        ws = _check_workspace_access(db, workspace_id, uid)
        if ws.owner_id != uid:
            raise HTTPException(403, "Nur der Owner kann Rollen ändern.")
        member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == member_user_id,
            )
            .first()
        )
        if not member:
            raise HTTPException(404, "Mitglied nicht gefunden.")
        member.role = body.role
        db.flush()
        db.refresh(member)
        return member


# --- Routines (#653) ---


@router.post(
    "/workspaces/{workspace_id}/routines",
    response_model=RoutineOut,
    status_code=201,
)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_routine(
    request: Request,
    workspace_id: int,
    body: RoutineCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        _check_workspace_access(db, workspace_id, uid)
        routine = Routine(workspace_id=workspace_id, **body.model_dump())
        db.add(routine)
        db.flush()
        db.refresh(routine)
        return routine


@router.get("/workspaces/{workspace_id}/routines/weekly", response_model=list[RoutineOut])
async def weekly_routines(workspace_id: int, user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        _check_workspace_access(db, workspace_id, uid)
        return db.query(Routine).filter(Routine.workspace_id == workspace_id).all()


@router.get("/workspaces/{workspace_id}/routines", response_model=list[RoutineOut])
async def list_routines(workspace_id: int, user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        _check_workspace_access(db, workspace_id, uid)
        return db.query(Routine).filter(Routine.workspace_id == workspace_id).order_by(Routine.created_at.desc()).all()


@router.patch("/workspaces/{workspace_id}/routines/{routine_id}", response_model=RoutineOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_routine(
    request: Request,
    workspace_id: int,
    routine_id: int,
    body: RoutineUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        _check_workspace_access(db, workspace_id, uid)
        routine = db.query(Routine).filter(Routine.id == routine_id, Routine.workspace_id == workspace_id).first()
        if not routine:
            raise HTTPException(404, "Routine nicht gefunden.")
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(routine, k, v)
        db.flush()
        db.refresh(routine)
        return routine


@router.delete("/workspaces/{workspace_id}/routines/{routine_id}", status_code=204)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_routine(
    request: Request,
    workspace_id: int,
    routine_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        _check_workspace_access(db, workspace_id, uid)
        routine = db.query(Routine).filter(Routine.id == routine_id, Routine.workspace_id == workspace_id).first()
        if not routine:
            raise HTTPException(404, "Routine nicht gefunden.")
        db.query(RoutineCompletion).filter(RoutineCompletion.routine_id == routine_id).delete()
        db.delete(routine)


@router.post(
    "/workspaces/{workspace_id}/routines/{routine_id}/complete",
    response_model=RoutineCompletionOut,
    status_code=201,
)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def complete_routine(
    request: Request,
    workspace_id: int,
    routine_id: int,
    body: RoutineCompletionCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        _check_workspace_access(db, workspace_id, uid)
        routine = db.query(Routine).filter(Routine.id == routine_id, Routine.workspace_id == workspace_id).first()
        if not routine:
            raise HTTPException(404, "Routine nicht gefunden.")
        completion = RoutineCompletion(
            routine_id=routine_id,
            completed_by=uid,
            completed_at=datetime.now(timezone.utc),
            photo_url=body.photo_url,
        )
        db.add(completion)
        # Rotation logic
        if routine.assignee_strategy == "rotation":
            members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()
            member_ids = [m.user_id for m in members]
            ws = db.query(HouseholdWorkspace).filter(HouseholdWorkspace.id == workspace_id).first()
            if ws and ws.owner_id not in member_ids:
                member_ids.insert(0, ws.owner_id)
            if member_ids:
                current = routine.current_assignee_id
                if current in member_ids:
                    idx = (member_ids.index(current) + 1) % len(member_ids)
                else:
                    idx = 0
                routine.current_assignee_id = member_ids[idx]
        db.flush()
        db.refresh(completion)
        return completion


# --- Workspace Info (#652) ---


@router.get("/workspaces/{workspace_id}/info")
async def workspace_info(workspace_id: int, user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        ws = _check_workspace_access(db, workspace_id, uid)
        member_count = (
            db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).count()
        ) + 1  # +1 for owner
        routine_count = db.query(Routine).filter(Routine.workspace_id == workspace_id).count()
        return {
            "workspace_id": ws.id,
            "name": ws.name,
            "member_count": member_count,
            "routine_count": routine_count,
        }
