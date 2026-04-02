"""
User Preferences Service – Nav-Config, Dashboard-Widgets, Appearance.

Speichert Preferences als JSON-Blob in UserProfile.preferences_json.
"""

import json
import logging

from src.services.database import get_db, UserProfile

logger = logging.getLogger(__name__)

# Alle verfuegbaren Nav-Items mit Defaults
NAV_ITEMS_REGISTRY = [
    {"id": "dashboard", "label": "Home", "icon": "home", "route": "#/dashboard", "default_pinned": True, "default_order": 0},
    {"id": "shopping", "label": "Einkauf", "icon": "shopping_cart", "route": "#/shopping", "default_pinned": True, "default_order": 1},
    {"id": "recipes", "label": "Rezepte", "icon": "restaurant", "route": "#/recipes", "default_pinned": True, "default_order": 2},
    {"id": "chat", "label": "Chat", "icon": "chat_bubble", "route": "#/chat", "default_pinned": True, "default_order": 3},
    {"id": "profile", "label": "Profil", "icon": "person", "route": "#/profile", "default_pinned": True, "default_order": 4},
    {"id": "calendar", "label": "Kalender", "icon": "calendar_month", "route": "#/calendar", "default_pinned": False, "default_order": 5},
    {"id": "tasks", "label": "Aufgaben", "icon": "check_circle", "route": "#/tasks", "default_pinned": False, "default_order": 6},
    {"id": "mealplan", "label": "Wochenplan", "icon": "restaurant_menu", "route": "#/mealplan", "default_pinned": False, "default_order": 7},
    {"id": "drive", "label": "Drive", "icon": "folder", "route": "#/drive", "default_pinned": False, "default_order": 8},
    {"id": "shifts", "label": "Dienste", "icon": "work", "route": "#/shifts", "default_pinned": False, "default_order": 9},
    {"id": "issues", "label": "Issues", "icon": "bug_report", "route": "#/issues", "default_pinned": False, "default_order": 10},
]

# Alle verfuegbaren Dashboard-Widgets mit Defaults
DASHBOARD_WIDGETS_REGISTRY = [
    {"id": "emails", "label": "E-Mails", "icon": "mail", "default_enabled": True, "default_order": 0},
    {"id": "shifts", "label": "Dienste heute", "icon": "work", "default_enabled": True, "default_order": 1},
    {"id": "events", "label": "Termine heute", "icon": "calendar_month", "default_enabled": True, "default_order": 2},
    {"id": "tasks", "label": "Offene Aufgaben", "icon": "check_circle", "default_enabled": True, "default_order": 3},
    {"id": "shopping", "label": "Einkaufsliste", "icon": "shopping_cart", "default_enabled": True, "default_order": 4},
    {"id": "mealplan", "label": "Wochenplan", "icon": "restaurant", "default_enabled": True, "default_order": 5},
    {"id": "drive", "label": "Drive", "icon": "folder", "default_enabled": True, "default_order": 6},
]

MAX_PINNED_NAV = 5


def _default_preferences() -> dict:
    """Erzeugt die Standard-Preferences fuer neue User."""
    return {
        "nav": {
            "items": [
                {
                    "id": item["id"],
                    "enabled": True,
                    "pinned": item["default_pinned"],
                    "order": item["default_order"],
                }
                for item in NAV_ITEMS_REGISTRY
            ],
            "maxPinned": MAX_PINNED_NAV,
        },
        "dashboard": {
            "widgets": [
                {
                    "id": w["id"],
                    "enabled": w["default_enabled"],
                    "order": w["default_order"],
                }
                for w in DASHBOARD_WIDGETS_REGISTRY
            ],
        },
        "appearance": {
            "theme": "dark",
        },
    }


def get_preferences(user_key: str) -> dict:
    """Laedt User-Preferences aus DB, merged mit Defaults fuer neue Items."""
    with get_db()() as session:
        profile = session.query(UserProfile).filter_by(user_key=user_key).first()
        if not profile or not profile.preferences_json:
            return _default_preferences()

        try:
            stored = json.loads(profile.preferences_json)
        except (json.JSONDecodeError, TypeError):
            return _default_preferences()

    defaults = _default_preferences()
    return _merge_preferences(stored, defaults)


def update_preferences(user_key: str, updates: dict) -> dict:
    """Aktualisiert User-Preferences (partial merge). Gibt neue Preferences zurueck."""
    with get_db()() as session:
        profile = session.query(UserProfile).filter_by(user_key=user_key).first()
        if not profile:
            profile = UserProfile(user_key=user_key)
            session.add(profile)

        current = _default_preferences()
        if profile.preferences_json:
            try:
                stored = json.loads(profile.preferences_json)
                current = _merge_preferences(stored, current)
            except (json.JSONDecodeError, TypeError):
                pass

        # Deep-merge der Updates
        if "nav" in updates:
            if "items" in updates["nav"]:
                _validate_nav_items(updates["nav"]["items"])
                current["nav"]["items"] = updates["nav"]["items"]
        if "dashboard" in updates:
            if "widgets" in updates["dashboard"]:
                current["dashboard"]["widgets"] = updates["dashboard"]["widgets"]
        if "appearance" in updates:
            current["appearance"].update(updates["appearance"])

        profile.preferences_json = json.dumps(current)
        session.flush()

    return current


def get_nav_registry() -> list[dict]:
    """Gibt die vollstaendige Nav-Item-Registry zurueck (fuer Settings-UI)."""
    return NAV_ITEMS_REGISTRY


def get_dashboard_widget_registry() -> list[dict]:
    """Gibt die vollstaendige Widget-Registry zurueck (fuer Settings-UI)."""
    return DASHBOARD_WIDGETS_REGISTRY


def _merge_preferences(stored: dict, defaults: dict) -> dict:
    """Merged gespeicherte Preferences mit Defaults (neue Items werden ergaenzt)."""
    result = dict(defaults)

    # Nav: gespeicherte Reihenfolge/Einstellungen uebernehmen, neue Items anhaengen
    if "nav" in stored and "items" in stored["nav"]:
        stored_ids = {item["id"] for item in stored["nav"]["items"]}
        merged_nav = list(stored["nav"]["items"])
        max_order = max((i.get("order", 0) for i in merged_nav), default=0)
        for default_item in defaults["nav"]["items"]:
            if default_item["id"] not in stored_ids:
                max_order += 1
                default_item["order"] = max_order
                merged_nav.append(default_item)
        result["nav"]["items"] = merged_nav

    # Dashboard: gleiche Logik
    if "dashboard" in stored and "widgets" in stored["dashboard"]:
        stored_ids = {w["id"] for w in stored["dashboard"]["widgets"]}
        merged_widgets = list(stored["dashboard"]["widgets"])
        max_order = max((w.get("order", 0) for w in merged_widgets), default=0)
        for default_widget in defaults["dashboard"]["widgets"]:
            if default_widget["id"] not in stored_ids:
                max_order += 1
                default_widget["order"] = max_order
                merged_widgets.append(default_widget)
        result["dashboard"]["widgets"] = merged_widgets

    # Appearance
    if "appearance" in stored:
        result["appearance"] = {**defaults.get("appearance", {}), **stored["appearance"]}

    return result


def _validate_nav_items(items: list[dict]) -> None:
    """Validiert Nav-Items: max pinned, required fields."""
    pinned_count = sum(1 for i in items if i.get("pinned"))
    if pinned_count > MAX_PINNED_NAV:
        raise ValueError(f"Maximal {MAX_PINNED_NAV} Nav-Items koennen angepinnt werden.")
    for item in items:
        if "id" not in item:
            raise ValueError("Jedes Nav-Item braucht eine 'id'.")
