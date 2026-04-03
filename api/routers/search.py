"""GET /search – Globale Suche ueber Tasks, Kalender, Einkauf, Chat, Rezepte, Dokumente, Notizen, Drive."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_

from api.dependencies import (
    get_current_user,
    get_calendar_service_optional,
    get_drive_service_optional,
)
from api.schemas.search import SearchResult
from src.services.database import (
    Task,
    ConversationHistory,
    ShoppingItem,
    SavedRecipe,
    MealPlanEntry,
    Note,
    ScannedDocument,
    MemoryFact,
    get_db,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=list[SearchResult])
async def global_search(
    user_key: Annotated[str, Depends(get_current_user)],
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    cal_svc=Depends(get_calendar_service_optional),
    drive_svc=Depends(get_drive_service_optional),
):
    """Sucht uebergreifend in Tasks, Einkauf, Chat, Rezepte, Wochenplan, Notizen, Dokumente, Kalender, Drive."""
    results: list[SearchResult] = []
    term = f"%{q}%"
    per_source = min(limit, 5)

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
            .limit(per_source)
            .all()
        )
        for t in tasks:
            results.append(
                SearchResult(
                    type="task",
                    id=t.id,
                    title=t.title,
                    subtitle=f"Status: {t.status or 'offen'} · Priorität: {t.priority or 'normal'}",
                    route="#/tasks",
                )
            )

        # Shopping items
        shopping = (
            session.query(ShoppingItem)
            .filter(
                ShoppingItem.user_key == user_key,
                ShoppingItem.name.ilike(term),
            )
            .limit(per_source)
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

        # Saved recipes
        recipes = (
            session.query(SavedRecipe)
            .filter(
                SavedRecipe.user_key == user_key,
                SavedRecipe.title.ilike(term),
            )
            .limit(per_source)
            .all()
        )
        for r in recipes:
            parts = []
            if r.difficulty:
                parts.append(r.difficulty)
            parts.append(f"{r.servings} Portionen")
            if r.is_favorite:
                parts.append("Favorit")
            results.append(
                SearchResult(
                    type="recipe",
                    id=r.id,
                    title=r.title,
                    subtitle=" · ".join(parts),
                    route="#/recipes",
                )
            )

        # Meal plan entries
        mealplan = (
            session.query(MealPlanEntry)
            .filter(
                MealPlanEntry.user_key == user_key,
                MealPlanEntry.recipe_title.ilike(term),
            )
            .limit(per_source)
            .all()
        )
        for m in mealplan:
            meal_labels = {"breakfast": "Frühstück", "lunch": "Mittagessen", "dinner": "Abendessen"}
            meal_label = meal_labels.get(m.meal_type, m.meal_type or "")
            results.append(
                SearchResult(
                    type="mealplan",
                    id=m.id,
                    title=m.recipe_title,
                    subtitle=f"{m.planned_date} · {meal_label}" if meal_label else m.planned_date,
                    route="#/mealplan",
                )
            )

        # Scanned documents
        documents = (
            session.query(ScannedDocument)
            .filter(
                ScannedDocument.user_key == user_key,
                or_(
                    ScannedDocument.filename.ilike(term),
                    ScannedDocument.summary.ilike(term),
                    ScannedDocument.sender.ilike(term),
                    ScannedDocument.doc_type.ilike(term),
                ),
            )
            .limit(per_source)
            .all()
        )
        for d in documents:
            parts = [d.doc_type]
            if d.sender:
                parts.append(d.sender)
            if d.amount:
                parts.append(d.amount)
            results.append(
                SearchResult(
                    type="document",
                    id=d.id,
                    title=d.filename,
                    subtitle=" · ".join(parts),
                    route="#/documents",
                )
            )

        # Notes
        notes = (
            session.query(Note)
            .filter(
                Note.user_key == user_key,
                Note.content.ilike(term),
            )
            .limit(per_source)
            .all()
        )
        for n in notes:
            preview = n.content[:80] + ("…" if len(n.content) > 80 else "")
            results.append(
                SearchResult(
                    type="note",
                    id=n.id,
                    title=preview,
                    subtitle=n.created_at.strftime("%d.%m.%Y") if n.created_at else "",
                    route="#/memory",
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
            .limit(per_source)
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

        # Memory facts
        memories = (
            session.query(MemoryFact)
            .filter(
                MemoryFact.user_key == user_key,
                MemoryFact.content.ilike(term),
            )
            .limit(per_source)
            .all()
        )
        for mem in memories:
            preview = mem.content[:100] + ("…" if len(mem.content) > 100 else "")
            results.append(
                SearchResult(
                    type="memory",
                    id=mem.id,
                    title=preview,
                    subtitle=f"Konfidenz: {mem.confirmation_count}",
                    route="#/memory",
                )
            )

    # Calendar events (external Google Calendar API – best-effort)
    if cal_svc and cal_svc.is_connected(user_key):
        try:
            q_lower = q.lower()
            cal_events = await cal_svc.get_upcoming_events(user_key, days=30, max_results=20)
            count = 0
            for ev in cal_events:
                summary = ev.get("summary", "")
                location = ev.get("location", "")
                description = ev.get("description", "")
                if q_lower not in f"{summary} {location} {description}".lower():
                    continue
                start_raw = ev.get("start", {})
                start_str = (
                    start_raw.get("dateTime", start_raw.get("date", ""))
                    if isinstance(start_raw, dict)
                    else str(start_raw)
                )
                # Format for display
                subtitle_parts = []
                if start_str:
                    subtitle_parts.append(start_str[:16].replace("T", " "))
                if location:
                    subtitle_parts.append(location)
                results.append(
                    SearchResult(
                        type="calendar",
                        title=summary,
                        subtitle=" · ".join(subtitle_parts),
                        route="#/calendar",
                    )
                )
                count += 1
                if count >= per_source:
                    break
        except Exception as e:
            logger.debug("Calendar-Suche uebersprungen: %s", e)

    # Drive files (external Google Drive API – best-effort)
    if drive_svc and drive_svc.is_connected(user_key):
        try:
            drive_files = await drive_svc.search_files(user_key, q, limit=per_source)
            for f in drive_files or []:
                name = f.get("name", "")
                mime = f.get("mimeType", "")
                size = f.get("size")
                subtitle_parts = []
                if mime:
                    # Simplify MIME for display
                    short_mime = mime.split("/")[-1].replace("vnd.google-apps.", "")
                    subtitle_parts.append(short_mime)
                if size:
                    try:
                        size_mb = int(size) / (1024 * 1024)
                        subtitle_parts.append(f"{size_mb:.1f} MB" if size_mb >= 1 else f"{int(size) // 1024} KB")
                    except (ValueError, TypeError):
                        pass
                results.append(
                    SearchResult(
                        type="drive",
                        title=name,
                        subtitle=" · ".join(subtitle_parts),
                        route="#/drive",
                    )
                )
        except Exception as e:
            logger.debug("Drive-Suche uebersprungen: %s", e)

    # Trim to overall limit
    return results[:limit]
