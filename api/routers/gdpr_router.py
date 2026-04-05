"""GDPR/DSGVO-Router: Daten-Export, Account-Löschung, Einwilligungen."""

import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.gdpr import (
    ConsentUpdateResponse,
    ConsentsResponse,
    DataExportResponse,
    DeleteAccountResponse,
    DeleteCategoryResponse,
    GdprHealthResponse,
)
from config.settings import settings
from src.services.database import (
    Budget,
    Contract,
    FinanceInvoice,
    HouseholdWorkspace,
    InventoryItem,
    NotificationEvent,
    NotificationPreference,
    Routine,
    RoutineCompletion,
    ScannedDocument,
    Transaction,
    UserProfile,
    Warranty,
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


def _serialize(obj) -> dict:
    result = {}
    for c in obj.__table__.columns:
        val = getattr(obj, c.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[c.name] = val
    return result


@router.get("/health", response_model=GdprHealthResponse)
async def health():
    return {"status": "ok", "module": "gdpr"}


@router.get("/data-export", response_model=DataExportResponse)
async def data_export(user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        data = {
            "transactions": [_serialize(r) for r in db.query(Transaction).filter(Transaction.user_id == uid).all()],
            "budgets": [_serialize(r) for r in db.query(Budget).filter(Budget.user_id == uid).all()],
            "contracts": [_serialize(r) for r in db.query(Contract).filter(Contract.user_id == uid).all()],
            "finance_invoices": [
                _serialize(r) for r in db.query(FinanceInvoice).filter(FinanceInvoice.user_id == uid).all()
            ],
            "inventory_items": [
                _serialize(r) for r in db.query(InventoryItem).filter(InventoryItem.user_id == uid).all()
            ],
            "warranties": [_serialize(r) for r in db.query(Warranty).filter(Warranty.user_id == uid).all()],
            "documents": [
                _serialize(r) for r in db.query(ScannedDocument).filter(ScannedDocument.user_key == user_key).all()
            ],
            "notification_events": [
                _serialize(r) for r in db.query(NotificationEvent).filter(NotificationEvent.user_id == uid).all()
            ],
            "notification_preferences": [
                _serialize(r)
                for r in db.query(NotificationPreference).filter(NotificationPreference.user_id == uid).all()
            ],
            "workspaces_owned": [
                _serialize(r) for r in db.query(HouseholdWorkspace).filter(HouseholdWorkspace.owner_id == uid).all()
            ],
            "workspace_memberships": [
                _serialize(r) for r in db.query(WorkspaceMember).filter(WorkspaceMember.user_id == uid).all()
            ],
        }
        return {"user_key": user_key, "user_id": uid, "data": data}


@router.delete("/account", response_model=DeleteAccountResponse)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_account(request: Request, user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        counts = {}
        # Delete in FK-safe order (dependents first)
        counts["routine_completions"] = (
            db.query(RoutineCompletion).filter(RoutineCompletion.completed_by == uid).delete()
        )
        # Routines in owned workspaces
        owned_ws_ids = [w.id for w in db.query(HouseholdWorkspace).filter(HouseholdWorkspace.owner_id == uid).all()]
        if owned_ws_ids:
            routine_ids = [r.id for r in db.query(Routine).filter(Routine.workspace_id.in_(owned_ws_ids)).all()]
            if routine_ids:
                counts["routine_completions_owned"] = (
                    db.query(RoutineCompletion)
                    .filter(RoutineCompletion.routine_id.in_(routine_ids))
                    .delete(synchronize_session="fetch")
                )
            counts["routines"] = (
                db.query(Routine).filter(Routine.workspace_id.in_(owned_ws_ids)).delete(synchronize_session="fetch")
            )
            counts["workspace_members"] = (
                db.query(WorkspaceMember)
                .filter(WorkspaceMember.workspace_id.in_(owned_ws_ids))
                .delete(synchronize_session="fetch")
            )
        counts["workspace_memberships"] = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == uid).delete()
        counts["workspaces"] = db.query(HouseholdWorkspace).filter(HouseholdWorkspace.owner_id == uid).delete()
        counts["warranties"] = db.query(Warranty).filter(Warranty.user_id == uid).delete()
        counts["inventory_items"] = db.query(InventoryItem).filter(InventoryItem.user_id == uid).delete()
        counts["notification_preferences"] = (
            db.query(NotificationPreference).filter(NotificationPreference.user_id == uid).delete()
        )
        counts["notification_events"] = db.query(NotificationEvent).filter(NotificationEvent.user_id == uid).delete()
        counts["finance_invoices"] = db.query(FinanceInvoice).filter(FinanceInvoice.user_id == uid).delete()
        counts["contracts"] = db.query(Contract).filter(Contract.user_id == uid).delete()
        counts["budgets"] = db.query(Budget).filter(Budget.user_id == uid).delete()
        counts["transactions"] = db.query(Transaction).filter(Transaction.user_id == uid).delete()
        counts["documents"] = db.query(ScannedDocument).filter(ScannedDocument.user_key == user_key).delete()
        return {"deleted": True, "user_key": user_key, "counts": counts}


@router.delete("/data/{category}", response_model=DeleteCategoryResponse)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_category(
    request: Request,
    category: Literal["finance", "inventory", "documents", "family", "notifications"],
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        uid = _resolve_user_id(db, user_key)
        counts = {}
        if category == "finance":
            counts["finance_invoices"] = db.query(FinanceInvoice).filter(FinanceInvoice.user_id == uid).delete()
            counts["contracts"] = db.query(Contract).filter(Contract.user_id == uid).delete()
            counts["budgets"] = db.query(Budget).filter(Budget.user_id == uid).delete()
            counts["transactions"] = db.query(Transaction).filter(Transaction.user_id == uid).delete()
        elif category == "inventory":
            counts["warranties"] = db.query(Warranty).filter(Warranty.user_id == uid).delete()
            counts["inventory_items"] = db.query(InventoryItem).filter(InventoryItem.user_id == uid).delete()
        elif category == "documents":
            counts["documents"] = db.query(ScannedDocument).filter(ScannedDocument.user_key == user_key).delete()
        elif category == "family":
            owned_ws_ids = [w.id for w in db.query(HouseholdWorkspace).filter(HouseholdWorkspace.owner_id == uid).all()]
            if owned_ws_ids:
                routine_ids = [r.id for r in db.query(Routine).filter(Routine.workspace_id.in_(owned_ws_ids)).all()]
                if routine_ids:
                    db.query(RoutineCompletion).filter(RoutineCompletion.routine_id.in_(routine_ids)).delete(
                        synchronize_session="fetch"
                    )
                db.query(Routine).filter(Routine.workspace_id.in_(owned_ws_ids)).delete(synchronize_session="fetch")
                db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id.in_(owned_ws_ids)).delete(
                    synchronize_session="fetch"
                )
            counts["workspace_memberships"] = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == uid).delete()
            counts["workspaces"] = db.query(HouseholdWorkspace).filter(HouseholdWorkspace.owner_id == uid).delete()
        elif category == "notifications":
            counts["notification_preferences"] = (
                db.query(NotificationPreference).filter(NotificationPreference.user_id == uid).delete()
            )
            counts["notification_events"] = (
                db.query(NotificationEvent).filter(NotificationEvent.user_id == uid).delete()
            )
        return {"category": category, "deleted": True, "counts": counts}


@router.get("/consents", response_model=ConsentsResponse)
async def list_consents(user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
        if not profile:
            raise HTTPException(404, "User-Profil nicht gefunden.")
        features = {}
        if profile.enabled_features:
            try:
                features = json.loads(profile.enabled_features)
            except (json.JSONDecodeError, TypeError):
                features = {}
        return {"user_key": user_key, "consents": features}


@router.post("/consents/{feature}", response_model=ConsentUpdateResponse)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def grant_consent(
    request: Request,
    feature: str,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
        if not profile:
            raise HTTPException(404, "User-Profil nicht gefunden.")
        features = {}
        if profile.enabled_features:
            try:
                features = json.loads(profile.enabled_features)
            except (json.JSONDecodeError, TypeError):
                features = {}
        features[feature] = True
        profile.enabled_features = json.dumps(features)
        db.flush()
        return {"feature": feature, "consented": True}


@router.delete("/consents/{feature}", response_model=ConsentUpdateResponse)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def revoke_consent(
    request: Request,
    feature: str,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
        if not profile:
            raise HTTPException(404, "User-Profil nicht gefunden.")
        features = {}
        if profile.enabled_features:
            try:
                features = json.loads(profile.enabled_features)
            except (json.JSONDecodeError, TypeError):
                features = {}
        features.pop(feature, None)
        profile.enabled_features = json.dumps(features)
        db.flush()
        return {"feature": feature, "consented": False}
