"""
Task Service: Aufgabenverwaltung mit Status-Tracking und Cross-Bot-Zuweisung.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import pytz

from config.settings import settings

logger = logging.getLogger(__name__)

PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

STATUS_OPEN = "open"
STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "done"

PRIORITY_ICONS = {PRIORITY_HIGH: "🔴", PRIORITY_MEDIUM: "🟡", PRIORITY_LOW: "🟢"}
STATUS_ICONS = {STATUS_OPEN: "📋", STATUS_IN_PROGRESS: "⚙️", STATUS_DONE: "✅"}

RECURRENCE_INTERVALS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),
}


class TaskService:
    def __init__(self):
        self._db = None
        self.tz = pytz.timezone(settings.TIMEZONE)

    def _ensure_initialized(self):
        if self._db is None:
            raise RuntimeError("TaskService not initialized – call initialize() first")

    async def initialize(self):
        from src.services.database import get_db, init_db

        init_db()
        self._db = get_db()
        logger.info("Task Service initialisiert.")

    async def create_task(
        self,
        user_key: str,
        title: str,
        priority: str = PRIORITY_MEDIUM,
        description: str = "",
        due_date: Optional[datetime] = None,
        assigned_by: Optional[str] = None,
        recurrence: Optional[str] = None,
    ) -> dict:
        from src.services.database import Task

        self._ensure_initialized()
        with self._db() as session:
            task = Task(
                user_key=user_key,
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
                status=STATUS_OPEN,
                assigned_by=assigned_by,
                recurrence=recurrence if recurrence in RECURRENCE_INTERVALS else None,
            )
            session.add(task)
            session.flush()
            result = self._task_to_dict(task)
        logger.info(f"Task #{result['id']} erstellt für '{user_key}': {title[:60]}")
        return result

    async def get_open_tasks(self, user_key: str) -> list[dict]:
        from src.services.database import Task

        self._ensure_initialized()
        with self._db() as session:
            tasks = (
                session.query(Task)
                .filter(Task.user_key == user_key, Task.status != STATUS_DONE)
                .order_by(Task.priority.asc(), Task.created_at.asc())
                .all()
            )
            return [self._task_to_dict(t) for t in tasks]

    async def get_all_tasks(self, user_key: str, limit: int = 20) -> list[dict]:
        from src.services.database import Task

        self._ensure_initialized()
        with self._db() as session:
            tasks = (
                session.query(Task)
                .filter(Task.user_key == user_key)
                .order_by(Task.created_at.desc())
                .limit(limit)
                .all()
            )
            return [self._task_to_dict(t) for t in tasks]

    async def complete_task(self, task_id: int, user_key: str) -> Optional[dict]:
        from src.services.database import Task

        self._ensure_initialized()
        now = datetime.now(timezone.utc)
        with self._db() as session:
            task = session.query(Task).filter_by(id=task_id, user_key=user_key).first()
            if not task:
                return None
            if task.recurrence and task.recurrence in RECURRENCE_INTERVALS:
                # Recurring: record completion, keep open
                task.last_completed_at = now
                task.status = STATUS_OPEN
                task.updated_at = now
            else:
                task.status = STATUS_DONE
                task.updated_at = now
            return self._task_to_dict(task)

    async def get_completed_tasks_since(self, user_key: str, since: datetime) -> list[dict]:
        """Tasks completed (done or recurring-completed) since a given datetime."""
        from src.services.database import Task
        from sqlalchemy import or_

        self._ensure_initialized()
        with self._db() as session:
            tasks = (
                session.query(Task)
                .filter(
                    Task.user_key == user_key,
                    or_(
                        # Normal tasks marked done in the period
                        (Task.status == STATUS_DONE) & (Task.updated_at >= since),
                        # Recurring tasks completed in the period
                        (Task.recurrence.isnot(None)) & (Task.last_completed_at >= since),
                    ),
                )
                .order_by(Task.updated_at.desc())
                .all()
            )
            return [self._task_to_dict(t) for t in tasks]

    async def delete_task(self, task_id: int, user_key: str) -> bool:
        from src.services.database import Task

        self._ensure_initialized()
        with self._db() as session:
            task = session.query(Task).filter_by(id=task_id, user_key=user_key).first()
            if task:
                session.delete(task)
                return True
        return False

    def _task_to_dict(self, task) -> dict:
        due = None
        if task.due_date:
            due = task.due_date.replace(tzinfo=pytz.utc).astimezone(self.tz)
        last_completed = None
        if task.last_completed_at:
            last_completed = task.last_completed_at.replace(tzinfo=pytz.utc).astimezone(self.tz)
        return {
            "id": task.id,
            "user_key": task.user_key,
            "title": task.title,
            "description": task.description or "",
            "priority": task.priority,
            "status": task.status,
            "due_date": due,
            "assigned_by": task.assigned_by,
            "recurrence": task.recurrence,
            "last_completed_at": last_completed,
            "created_at": task.created_at,
        }

    def format_task_list(self, tasks: list[dict], header: str = "📋 *Deine Aufgaben:*") -> str:
        if not tasks:
            return "📋 Keine offenen Aufgaben. Alles erledigt! 🎉"

        lines = [header + "\n"]
        priority_order = [PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW]

        for priority in priority_order:
            group = [t for t in tasks if t["priority"] == priority and t["status"] != STATUS_DONE]
            if not group:
                continue
            icon = PRIORITY_ICONS[priority]
            for t in group:
                due_str = ""
                if t.get("due_date"):
                    due_str = f" _(bis {t['due_date'].strftime('%d.%m.')})_"
                assigned_str = ""
                if t.get("assigned_by"):
                    assigned_str = f" ← von {t['assigned_by'].capitalize()}"
                recur_str = ""
                if t.get("recurrence"):
                    recur_labels = {"daily": "täglich", "weekly": "wöchentlich", "monthly": "monatlich"}
                    recur_str = f" 🔄 {recur_labels.get(t['recurrence'], t['recurrence'])}"
                lines.append(f"{icon} `#{t['id']}` {t['title']}{due_str}{assigned_str}{recur_str}")

        return "\n".join(lines)
