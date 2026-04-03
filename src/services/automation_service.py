"""Automation Service: Regel- und Automationscenter fuer bereichsuebergreifende Workflows."""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────
# Trigger & Action Registry (Metadaten fuer UI + Evaluation)
# ──────────────────────────────────────────────────────────

TRIGGER_REGISTRY = {
    "task_due_today": {
        "label": "Aufgabe faellig",
        "icon": "assignment_late",
        "description": "Wenn eine Aufgabe heute faellig wird",
        "config_fields": [],
    },
    "event_tomorrow": {
        "label": "Termin morgen",
        "icon": "event",
        "description": "Wenn ein Kalendertermin morgen ansteht",
        "config_fields": [],
    },
    "task_completed": {
        "label": "Aufgabe erledigt",
        "icon": "task_alt",
        "description": "Wenn eine Aufgabe als erledigt markiert wurde",
        "config_fields": [],
    },
    "shopping_list_empty": {
        "label": "Einkaufsliste leer",
        "icon": "remove_shopping_cart",
        "description": "Wenn keine offenen Einkaufsartikel vorhanden sind",
        "config_fields": [],
    },
    "daily_time": {
        "label": "Taeglich um Uhrzeit",
        "icon": "schedule",
        "description": "Jeden Tag zu einer bestimmten Uhrzeit",
        "config_fields": [
            {
                "key": "time",
                "label": "Uhrzeit",
                "type": "time",
                "placeholder": "08:00",
                "required": True,
            }
        ],
    },
}

ACTION_REGISTRY = {
    "create_notification": {
        "label": "Benachrichtigung erstellen",
        "icon": "notifications",
        "description": "Erstellt eine Benachrichtigung in der App",
        "config_fields": [
            {
                "key": "title",
                "label": "Titel",
                "type": "text",
                "placeholder": "Benachrichtigungs-Titel",
                "required": True,
            },
            {
                "key": "message",
                "label": "Nachricht",
                "type": "textarea",
                "placeholder": "Nachricht (optional)",
                "required": False,
            },
        ],
    },
    "create_task": {
        "label": "Aufgabe erstellen",
        "icon": "add_task",
        "description": "Erstellt eine neue Aufgabe",
        "config_fields": [
            {
                "key": "title",
                "label": "Aufgabentitel",
                "type": "text",
                "placeholder": "Was soll erledigt werden?",
                "required": True,
            },
            {
                "key": "priority",
                "label": "Prioritaet",
                "type": "select",
                "required": False,
                "options": [
                    {"value": "low", "label": "Niedrig"},
                    {"value": "medium", "label": "Mittel"},
                    {"value": "high", "label": "Hoch"},
                ],
            },
        ],
    },
    "add_shopping_items": {
        "label": "Einkaufsliste befuellen",
        "icon": "add_shopping_cart",
        "description": "Fuegt Artikel zur Einkaufsliste hinzu",
        "config_fields": [
            {
                "key": "items",
                "label": "Artikel",
                "type": "text",
                "placeholder": "Milch, Brot, Eier (kommagetrennt)",
                "required": True,
            },
        ],
    },
    "create_reminder": {
        "label": "Erinnerung erstellen",
        "icon": "alarm",
        "description": "Erstellt eine Erinnerung",
        "config_fields": [
            {
                "key": "content",
                "label": "Erinnerungstext",
                "type": "text",
                "placeholder": "Woran soll erinnert werden?",
                "required": True,
            },
            {
                "key": "remind_in_minutes",
                "label": "In Minuten",
                "type": "number",
                "placeholder": "30",
                "required": False,
            },
        ],
    },
}

# ──────────────────────────────────────────────────────────
# Vorlagen (Templates) fuer haeufige Regeln
# ──────────────────────────────────────────────────────────

RULE_TEMPLATES = [
    {
        "name": "Faellige Aufgaben melden",
        "description": "Benachrichtigung wenn Aufgaben heute faellig werden",
        "trigger_type": "task_due_today",
        "trigger_config": {},
        "action_type": "create_notification",
        "action_config": {"title": "Aufgaben faellig!", "message": "Du hast heute faellige Aufgaben."},
    },
    {
        "name": "Terminerinnerung fuer morgen",
        "description": "Benachrichtigung wenn morgen ein Termin ansteht",
        "trigger_type": "event_tomorrow",
        "trigger_config": {},
        "action_type": "create_notification",
        "action_config": {"title": "Termin morgen", "message": "Du hast morgen einen Termin."},
    },
    {
        "name": "Morgenroutine",
        "description": "Taeglich um 8:00 eine Erinnerung erstellen",
        "trigger_type": "daily_time",
        "trigger_config": {"time": "08:00"},
        "action_type": "create_notification",
        "action_config": {"title": "Guten Morgen!", "message": "Zeit fuer die Morgenroutine."},
    },
]


class AutomationService:
    """Verwaltet benutzerdefinierte Automatisierungsregeln (wenn X dann Y)."""

    def __init__(self):
        self._data_dir = Path(settings.DATA_DIR) / "automations"

    async def initialize(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("AutomationService initialisiert.")

    # ── Meta ──

    def get_meta(self) -> dict:
        """Gibt verfuegbare Trigger und Aktionen mit Labels/Icons zurueck."""
        triggers = []
        for tid, t in TRIGGER_REGISTRY.items():
            triggers.append({"id": tid, **t})
        actions = []
        for aid, a in ACTION_REGISTRY.items():
            actions.append({"id": aid, **a})
        return {"triggers": triggers, "actions": actions, "templates": RULE_TEMPLATES}

    # ── CRUD ──

    async def list_rules(
        self, user_key: str, active_only: bool = False, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        rules = await self._load(user_key)
        if active_only:
            rules = [r for r in rules if r.get("active", True)]
        return rules[offset : offset + limit]

    async def create_rule(self, user_key: str, data: dict) -> dict:
        rules = await self._load(user_key)
        data["id"] = str(uuid.uuid4())
        data.setdefault("active", True)
        data["created_at"] = datetime.now().isoformat()
        data["trigger_count"] = 0
        data["last_triggered_at"] = None
        rules.append(data)
        await self._save(user_key, rules)
        return data

    async def update_rule(self, user_key: str, rule_id: str, updates: dict) -> Optional[dict]:
        rules = await self._load(user_key)
        rule = next((r for r in rules if r.get("id") == rule_id), None)
        if not rule:
            return None
        rule.update(updates)
        rule["updated_at"] = datetime.now().isoformat()
        await self._save(user_key, rules)
        return rule

    async def toggle_rule(self, user_key: str, rule_id: str) -> Optional[dict]:
        rules = await self._load(user_key)
        rule = next((r for r in rules if r.get("id") == rule_id), None)
        if not rule:
            return None
        rule["active"] = not rule.get("active", True)
        await self._save(user_key, rules)
        return rule

    async def delete_rule(self, user_key: str, rule_id: str) -> bool:
        rules = await self._load(user_key)
        before = len(rules)
        rules = [r for r in rules if r.get("id") != rule_id]
        if len(rules) < before:
            await self._save(user_key, rules)
            return True
        return False

    # ── Evaluation Engine ──

    async def evaluate_rules(self, user_key: str, services: dict) -> dict:
        """Wertet alle aktiven Regeln eines Users aus und fuehrt Aktionen aus."""
        rules = await self._load(user_key)
        active_rules = [r for r in rules if r.get("active", True)]

        results = {"evaluated": len(active_rules), "triggered": 0, "details": []}

        for rule in active_rules:
            try:
                fired = await self._check_trigger(user_key, rule, services)
                if fired:
                    await self._execute_action(user_key, rule, services)
                    rule["trigger_count"] = rule.get("trigger_count", 0) + 1
                    rule["last_triggered_at"] = datetime.now().isoformat()
                    results["triggered"] += 1
                    results["details"].append({
                        "rule_id": rule["id"],
                        "name": rule.get("name", ""),
                        "triggered": True,
                    })
                else:
                    results["details"].append({
                        "rule_id": rule["id"],
                        "name": rule.get("name", ""),
                        "triggered": False,
                    })
            except Exception as e:
                logger.warning("Regel '%s' Fehler: %s", rule.get("name", rule["id"]), e)
                results["details"].append({
                    "rule_id": rule["id"],
                    "name": rule.get("name", ""),
                    "triggered": False,
                    "error": str(e),
                })

        await self._save(user_key, rules)
        return results

    # ── Trigger Checks ──

    async def _check_trigger(self, user_key: str, rule: dict, services: dict) -> bool:
        trigger_type = rule.get("trigger_type")
        config = rule.get("trigger_config", {})

        if trigger_type == "task_due_today":
            return await self._check_task_due_today(user_key, services)
        elif trigger_type == "event_tomorrow":
            return await self._check_event_tomorrow(user_key, services)
        elif trigger_type == "task_completed":
            return await self._check_task_completed(user_key, rule, services)
        elif trigger_type == "shopping_list_empty":
            return await self._check_shopping_empty(user_key, services)
        elif trigger_type == "daily_time":
            return self._check_daily_time(config)
        else:
            logger.warning("Unbekannter Trigger-Typ: %s", trigger_type)
            return False

    async def _check_task_due_today(self, user_key: str, services: dict) -> bool:
        task_svc = services.get("task")
        if not task_svc:
            return False
        tasks = await task_svc.get_open_tasks(user_key)
        today = datetime.now(timezone.utc).date()
        return any(
            t.get("due_date") and _parse_date(t["due_date"]) == today
            for t in tasks
        )

    async def _check_event_tomorrow(self, user_key: str, services: dict) -> bool:
        cal_svc = services.get("calendar")
        if not cal_svc:
            return False
        try:
            events = await cal_svc.get_upcoming_events(user_key, days=2, max_results=50)
        except Exception:
            return False
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()
        return any(
            e.get("start") and _parse_date(e["start"]) == tomorrow
            for e in events
        )

    async def _check_task_completed(self, user_key: str, rule: dict, services: dict) -> bool:
        task_svc = services.get("task")
        if not task_svc:
            return False
        last_check = rule.get("last_triggered_at")
        since = datetime.fromisoformat(last_check) if last_check else datetime.now(timezone.utc) - timedelta(days=1)
        try:
            completed = await task_svc.get_completed_tasks_since(user_key, since)
            return len(completed) > 0
        except Exception:
            return False

    async def _check_shopping_empty(self, user_key: str, services: dict) -> bool:
        shop_svc = services.get("shopping")
        if not shop_svc:
            return False
        items = await shop_svc.get_items(user_key, include_checked=False)
        return len(items) == 0

    def _check_daily_time(self, config: dict) -> bool:
        time_str = config.get("time", "")
        if not time_str:
            return False
        try:
            parts = time_str.split(":")
            target_h, target_m = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return False
        now = datetime.now()
        # 15 Minuten Toleranz
        return now.hour == target_h and abs(now.minute - target_m) <= 15

    # ── Action Execution ──

    async def _execute_action(self, user_key: str, rule: dict, services: dict):
        action_type = rule.get("action_type")
        config = rule.get("action_config", {})

        if action_type == "create_notification":
            await self._exec_create_notification(user_key, config, services)
        elif action_type == "create_task":
            await self._exec_create_task(user_key, config, services)
        elif action_type == "add_shopping_items":
            await self._exec_add_shopping_items(user_key, config, services)
        elif action_type == "create_reminder":
            await self._exec_create_reminder(user_key, config, services)
        else:
            logger.warning("Unbekannter Action-Typ: %s", action_type)

    async def _exec_create_notification(self, user_key: str, config: dict, services: dict):
        notif_svc = services.get("notification")
        if not notif_svc:
            raise RuntimeError("NotificationService nicht verfuegbar")
        await notif_svc.create(
            user_key=user_key,
            type="system",
            title=config.get("title", "Automation"),
            message=config.get("message"),
            link="#/automation",
        )

    async def _exec_create_task(self, user_key: str, config: dict, services: dict):
        task_svc = services.get("task")
        if not task_svc:
            raise RuntimeError("TaskService nicht verfuegbar")
        await task_svc.create_task(
            user_key=user_key,
            title=config.get("title", "Automatische Aufgabe"),
            priority=config.get("priority", "medium"),
        )

    async def _exec_add_shopping_items(self, user_key: str, config: dict, services: dict):
        shop_svc = services.get("shopping")
        if not shop_svc:
            raise RuntimeError("ShoppingService nicht verfuegbar")
        items_str = config.get("items", "")
        item_names = [i.strip() for i in items_str.split(",") if i.strip()]
        for name in item_names:
            await shop_svc.add_item(user_key=user_key, name=name)

    async def _exec_create_reminder(self, user_key: str, config: dict, services: dict):
        reminder_svc = services.get("reminder")
        if not reminder_svc:
            raise RuntimeError("ReminderService nicht verfuegbar")
        minutes = int(config.get("remind_in_minutes", 30))
        remind_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await reminder_svc.create_reminder(
            user_key=user_key,
            user_chat_id="",
            content=config.get("content", "Automatische Erinnerung"),
            remind_at=remind_at,
        )

    # ── Persistenz ──

    async def _load(self, user_key: str) -> list[dict]:
        path = self._data_dir / f"{user_key}.json"
        if path.exists():
            return json.loads(path.read_text())
        return []

    async def _save(self, user_key: str, data: list[dict]):
        path = self._data_dir / f"{user_key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _parse_date(value) -> Optional:
    """Parst ein Datum aus verschiedenen Formaten (ISO-String, datetime)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            pass
        # Format "2026-04-03" direkt
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return None
