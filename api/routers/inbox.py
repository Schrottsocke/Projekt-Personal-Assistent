"""GET/POST /inbox – Zentrale Aktions-Inbox + Unified Inbox Aggregation"""

import asyncio
import logging
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import (
    get_current_user,
    get_inbox_service,
    get_notification_service,
    get_followup_service,
)
from api.schemas.inbox import InboxAction, InboxItemCreate, InboxItemOut
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


@router.get("", response_model=list[InboxItemOut])
async def list_inbox(
    user_key: Annotated[str, Depends(get_current_user)],
    inbox_svc=Depends(get_inbox_service),
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    return await inbox_svc.list_items(user_key, status=status, category=category, limit=limit, offset=offset)


@router.get("/count")
async def inbox_count(
    user_key: Annotated[str, Depends(get_current_user)],
    inbox_svc=Depends(get_inbox_service),
):
    pending = await inbox_svc.count_pending(user_key)
    return {"pending": pending}


@router.post("", response_model=InboxItemOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def add_inbox_item(
    request: Request,
    body: InboxItemCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    inbox_svc=Depends(get_inbox_service),
):
    return await inbox_svc.add_item(user_key, body.model_dump())


@router.post("/{item_id}/action", response_model=InboxItemOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def action_inbox_item(
    request: Request,
    item_id: str,
    body: InboxAction,
    user_key: Annotated[str, Depends(get_current_user)],
    inbox_svc=Depends(get_inbox_service),
):
    result = await inbox_svc.action_item(user_key, item_id, body.action)
    if not result:
        raise HTTPException(status_code=404, detail="Inbox-Item nicht gefunden.")
    return result


# ---------------------------------------------------------------------------
# Unified Inbox – aggregiert Notifications, Inbox-Items und Follow-ups
# ---------------------------------------------------------------------------

# Priority mapping for notification types
_NOTIF_TYPE_PRIORITY = {
    "reminder": 3,
    "follow_up": 3,
    "document": 5,
    "inbox": 4,
    "weather": 6,
    "system": 7,
}

# Status mapping: source status → unified status
_NOTIF_STATUS_MAP = {"new": "actionable", "read": "read", "completed": "done", "hidden": "archived"}
_INBOX_STATUS_MAP = {"pending": "actionable", "approved": "done", "dismissed": "done", "snoozed": "archived"}
_FOLLOWUP_STATUS_MAP = {"open": "actionable", "done": "done", "cancelled": "archived"}

# Actions available per source type and status
_ACTIONS = {
    ("notification", "actionable"): ["read", "complete", "hide"],
    ("notification", "read"): ["complete", "hide"],
    ("inbox", "actionable"): ["approve", "dismiss", "snooze"],
    ("followup", "actionable"): ["complete", "snooze"],
}

# Human-readable source labels
_SOURCE_LABELS = {
    "reminder": "Erinnerung",
    "follow_up": "Follow-up",
    "document": "Dokument",
    "inbox": "Posteingang",
    "weather": "Wetter",
    "system": "System",
    "proposal": "Vorschlag",
    "approval": "Freigabe",
    "followup": "Folgeaktion",
    "email": "E-Mail-Nachverfolgung",
    "commitment": "Offene Zusage",
    "task": "Aufgabe",
}


def _normalize_notification(n: dict) -> dict:
    status = _NOTIF_STATUS_MAP.get(n["status"], "read")
    prio = _NOTIF_TYPE_PRIORITY.get(n["type"], 5)
    if status != "actionable":
        prio = max(prio, 9)
    return {
        "id": f"notif:{n['id']}",
        "source": "notification",
        "source_id": str(n["id"]),
        "category": n["type"],
        "title": n["title"],
        "message": n.get("message", ""),
        "status": status,
        "priority": prio,
        "actions": _ACTIONS.get(("notification", status), []),
        "link": n.get("link"),
        "due_date": None,
        "is_overdue": False,
        "created_at": n["created_at"].isoformat() if hasattr(n["created_at"], "isoformat") else str(n["created_at"]),
        "source_label": _SOURCE_LABELS.get(n["type"], n["type"]),
    }


def _normalize_inbox_item(item: dict) -> dict:
    status = _INBOX_STATUS_MAP.get(item.get("status"), "actionable")
    prio = item.get("priority", 5)
    if status != "actionable":
        prio = max(prio, 9)
    return {
        "id": f"inbox:{item['id']}",
        "source": "inbox",
        "source_id": item["id"],
        "category": item.get("category", "system"),
        "title": item.get("title", ""),
        "message": item.get("message", ""),
        "status": status,
        "priority": prio,
        "actions": _ACTIONS.get(("inbox", status), []),
        "link": item.get("link"),
        "due_date": None,
        "is_overdue": False,
        "created_at": item.get("created_at", ""),
        "source_label": _SOURCE_LABELS.get(item.get("category", ""), item.get("category", "")),
    }


def _normalize_followup(f: dict) -> dict:
    status = _FOLLOWUP_STATUS_MAP.get(f.get("status"), "actionable")
    today = datetime.now().strftime("%Y-%m-%d")
    due = f.get("due_date")
    is_overdue = bool(due and due <= today and status == "actionable")
    prio = 1 if is_overdue else (3 if status == "actionable" else 9)
    return {
        "id": f"followup:{f['id']}",
        "source": "followup",
        "source_id": f["id"],
        "category": f.get("type", "task"),
        "title": f.get("title", ""),
        "message": f.get("notes", ""),
        "status": status,
        "priority": prio,
        "actions": _ACTIONS.get(("followup", status), []),
        "link": None,
        "due_date": due,
        "is_overdue": is_overdue,
        "created_at": f.get("created_at", ""),
        "source_label": _SOURCE_LABELS.get(f.get("type", ""), f.get("type", "")),
    }


class UnifiedAction(BaseModel):
    action: str


@router.get("/unified")
async def unified_inbox(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    notif_svc=Depends(get_notification_service),
    inbox_svc=Depends(get_inbox_service),
    followup_svc=Depends(get_followup_service),
    filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Aggregierte Inbox: Notifications + Inbox-Items + Follow-ups in einem Stream."""

    async def safe(coro, default):
        try:
            return await coro
        except Exception as e:
            logger.warning("Unified inbox Teilfehler: %s", e)
            return default

    notifications, inbox_items, followups = await asyncio.gather(
        safe(notif_svc.list(user_key, limit=200), []),
        safe(inbox_svc.list_items(user_key, status=None, limit=200), []),
        safe(followup_svc.list_followups(user_key, status=None, limit=200), []),
    )

    items = []
    items.extend(_normalize_notification(n) for n in notifications)
    items.extend(_normalize_inbox_item(i) for i in inbox_items)
    items.extend(_normalize_followup(f) for f in followups)

    if filter and filter != "all":
        items = [i for i in items if i["status"] == filter]

    # Sort: actionable first, then by priority (low=urgent), then newest first
    status_order = {"actionable": 0, "read": 1, "done": 2, "archived": 3}
    items.sort(key=lambda x: (status_order.get(x["status"], 9), x["priority"], x["created_at"]))
    # Reverse created_at within same status+priority (newest first)
    # The above sort puts oldest first for created_at, so we do a stable re-sort
    items.sort(key=lambda x: (status_order.get(x["status"], 9), x["priority"]))

    total = len(items)
    actionable = sum(1 for i in items if i["status"] == "actionable")
    items = items[offset : offset + limit]

    return {
        "items": items,
        "counts": {"actionable": actionable, "total": total},
    }


@router.get("/unified/count")
async def unified_inbox_count(
    user_key: Annotated[str, Depends(get_current_user)],
    notif_svc=Depends(get_notification_service),
    inbox_svc=Depends(get_inbox_service),
    followup_svc=Depends(get_followup_service),
):
    """Kombinierter Zaehler: ungelesene Notifications + offene Inbox + faellige Follow-ups."""

    async def safe(coro, default):
        try:
            return await coro
        except Exception as e:
            logger.warning("Unified count Teilfehler: %s", e)
            return default

    notif_count, inbox_count_val, due_followups = await asyncio.gather(
        safe(notif_svc.count_unread(user_key), 0),
        safe(inbox_svc.count_pending(user_key), 0),
        safe(followup_svc.get_due_followups(user_key), []),
    )

    return {
        "total": notif_count + inbox_count_val + len(due_followups),
        "notifications": notif_count,
        "inbox": inbox_count_val,
        "followups": len(due_followups),
    }


@router.post("/unified/{unified_id}/action")
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def unified_inbox_action(
    request: Request,
    unified_id: str,
    body: UnifiedAction,
    user_key: Annotated[str, Depends(get_current_user)],
    notif_svc=Depends(get_notification_service),
    inbox_svc=Depends(get_inbox_service),
    followup_svc=Depends(get_followup_service),
):
    """Fuehrt eine Aktion auf einem Unified-Item aus, delegiert an den richtigen Service."""
    if ":" not in unified_id:
        raise HTTPException(status_code=400, detail="Ungueltige Item-ID.")

    source, source_id = unified_id.split(":", 1)
    action = body.action

    if source == "notif":
        status_map = {"read": "read", "complete": "completed", "hide": "hidden"}
        new_status = status_map.get(action)
        if not new_status:
            raise HTTPException(status_code=400, detail=f"Ungueltige Aktion '{action}' fuer Notification.")
        result = await notif_svc.update_status(int(source_id), user_key, new_status)
        if not result:
            raise HTTPException(status_code=404, detail="Notification nicht gefunden.")
        return {"ok": True, "source": "notification", "new_status": new_status}

    elif source == "inbox":
        if action not in ("approve", "dismiss", "snooze"):
            raise HTTPException(status_code=400, detail=f"Ungueltige Aktion '{action}' fuer Inbox-Item.")
        result = await inbox_svc.action_item(user_key, source_id, action)
        if not result:
            raise HTTPException(status_code=404, detail="Inbox-Item nicht gefunden.")
        return {"ok": True, "source": "inbox", "new_status": result.get("status")}

    elif source == "followup":
        if action == "complete":
            result = await followup_svc.update_followup(user_key, source_id, {"status": "done"})
        elif action == "snooze":
            # Snooze: due_date um 3 Tage verschieben
            from datetime import timedelta

            new_due = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
            result = await followup_svc.update_followup(user_key, source_id, {"due_date": new_due})
        else:
            raise HTTPException(status_code=400, detail=f"Ungueltige Aktion '{action}' fuer Follow-up.")
        if not result:
            raise HTTPException(status_code=404, detail="Follow-up nicht gefunden.")
        return {"ok": True, "source": "followup", "new_status": result.get("status")}

    raise HTTPException(status_code=400, detail=f"Unbekannte Quelle '{source}'.")
