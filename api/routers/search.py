"""GET /search – Globale Suche ueber Tasks, Kalender, Einkauf, Chat, Drive."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_

from api.dependencies import get_current_user
from api.schemas.search import SearchResult
from src.services.database import (
    Task,
    ConversationHistory,
    ShoppingItem,
    get_db,
)

router = APIRouter()


@router.get("", response_model=list[SearchResult])
async def global_search(
    user_key: Annotated[str, Depends(get_current_user)],
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Sucht uebergreifend in Tasks, Einkauf und Chat-History."""
    results: list[SearchResult] = []
    term = f"%{q}%"

    with get_db()() as session:
        # Tasks
        tasks = (
            session.query(Task)
            .filter(
                Task.user_key == user_key,
                or_(
                    Task.title.ilike(term),
                    Task.description.ilike(term),
                ),
            )
            .limit(limit)
            .all()
        )
        for t in tasks:
            results.append(
                SearchResult(
                    type="task",
                    id=t.id,
                    title=t.title,
                    subtitle=f"Status: {t.status or 'offen'} · Priorität: {t.priority or 'normal'}",
                    route=f"#/tasks",
                )
            )

        # Shopping items
        shopping = (
            session.query(ShoppingItem)
            .filter(
                ShoppingItem.user_key == user_key,
                ShoppingItem.name.ilike(term),
            )
            .limit(limit)
            .all()
        )
        for s in shopping:
            checked = "erledigt" if s.checked else "offen"
            results.append(
                SearchResult(
                    type="shopping",
                    id=s.id,
                    title=s.name,
                    subtitle=f"{checked}" + (f" · {s.category}" if s.category else ""),
                    route="#/shopping",
                )
            )

        # Chat history
        chats = (
            session.query(ConversationHistory)
            .filter(
                ConversationHistory.user_key == user_key,
                ConversationHistory.content.ilike(term),
            )
            .order_by(ConversationHistory.created_at.desc())
            .limit(limit)
            .all()
        )
        for c in chats:
            preview = c.content[:100] + ("…" if len(c.content) > 100 else "")
            results.append(
                SearchResult(
                    type="chat",
                    id=c.id,
                    title=preview,
                    subtitle=f"{c.role} · {c.created_at.strftime('%d.%m.%Y %H:%M') if c.created_at else ''}",
                    route="#/chat",
                )
            )

    # Trim to overall limit
    return results[:limit]
