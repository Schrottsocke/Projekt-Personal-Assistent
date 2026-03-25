"""
Feature-Service: Verwaltet per-User Feature-Aktivierung.
Liest/schreibt enabled_features JSON in UserProfile.
"""

import json
import logging
from typing import Any

from config.settings import settings
from src.features.catalog import CATALOG, CATALOG_MAP, Feature
from src.services.database import UserProfile, get_db

logger = logging.getLogger(__name__)


def _settings_satisfied(feature: Feature) -> bool:
    """Prüft ob alle benötigten Settings für ein Feature gesetzt sind."""
    for key in feature.required_settings:
        val = getattr(settings, key, None)
        if not val:
            return False
    return True


def _load_user_flags(user_key: str) -> dict[str, bool]:
    """Lädt den enabled_features JSON-Dict aus der DB."""
    db = get_db()()
    try:
        profile = db.query(UserProfile).filter_by(user_key=user_key).first()
        if profile and profile.enabled_features:
            return json.loads(profile.enabled_features)
    except Exception as e:
        logger.warning(f"Feature-Flags laden fehlgeschlagen für {user_key}: {e}")
    finally:
        db.close()
    return {}


def _save_user_flags(user_key: str, flags: dict[str, bool]) -> None:
    """Speichert enabled_features JSON in die DB."""
    db = get_db()()
    try:
        profile = db.query(UserProfile).filter_by(user_key=user_key).first()
        if not profile:
            profile = UserProfile(user_key=user_key)
            db.add(profile)
        profile.enabled_features = json.dumps(flags)
        db.commit()
    except Exception as e:
        logger.error(f"Feature-Flags speichern fehlgeschlagen für {user_key}: {e}")
        db.rollback()
    finally:
        db.close()


def get_available_features() -> list[Feature]:
    """Gibt Features zurück, deren required_settings alle gesetzt sind."""
    return [f for f in CATALOG if _settings_satisfied(f)]


def is_available(feature_id: str) -> bool:
    """Prüft ob ein Feature auf diesem Server verfügbar ist (Settings vorhanden)."""
    feat = CATALOG_MAP.get(feature_id)
    return feat is not None and _settings_satisfied(feat)


def is_enabled(user_key: str, feature_id: str) -> bool:
    """Prüft ob ein Feature für einen User aktiv ist."""
    feat = CATALOG_MAP.get(feature_id)
    if not feat or not _settings_satisfied(feat):
        return False
    flags = _load_user_flags(user_key)
    return flags.get(feature_id, feat.default_enabled)


def get_enabled_features(user_key: str) -> list[Feature]:
    """Gibt alle aktiven Features eines Users zurück."""
    flags = _load_user_flags(user_key)
    result = []
    for feat in CATALOG:
        if not _settings_satisfied(feat):
            continue
        if flags.get(feat.id, feat.default_enabled):
            result.append(feat)
    return result


def get_enabled_intents(user_key: str) -> list[str]:
    """Gibt alle Intents zurück, die für diesen User aktiv sind (dedupliziert)."""
    seen: set[str] = set()
    intents: list[str] = []
    for feat in get_enabled_features(user_key):
        for intent in feat.intents:
            if intent not in seen:
                seen.add(intent)
                intents.append(intent)
    # chat ist immer dabei als Fallback
    if "chat" not in seen:
        intents.append("chat")
    return intents


def toggle_feature(user_key: str, feature_id: str) -> bool:
    """
    Schaltet ein Feature um.
    Gibt den neuen Zustand zurück (True = aktiv).
    Raises ValueError wenn Feature nicht existiert oder nicht verfügbar.
    """
    feat = CATALOG_MAP.get(feature_id)
    if not feat:
        raise ValueError(f"Unbekanntes Feature: {feature_id}")
    if not _settings_satisfied(feat):
        raise ValueError(f"Feature '{feature_id}' nicht verfügbar – Settings fehlen: {feat.required_settings}")
    if feature_id == "core":
        raise ValueError("KI-Chat kann nicht deaktiviert werden.")

    flags = _load_user_flags(user_key)
    current = flags.get(feature_id, feat.default_enabled)
    flags[feature_id] = not current
    _save_user_flags(user_key, flags)
    return flags[feature_id]


def get_feature_status_list(user_key: str) -> list[dict[str, Any]]:
    """
    Gibt eine vollständige Liste aller Features mit Status zurück.
    Für API und Telegram-Anzeige.
    """
    flags = _load_user_flags(user_key)
    result = []
    for feat in CATALOG:
        available = _settings_satisfied(feat)
        enabled = available and flags.get(feat.id, feat.default_enabled)
        result.append({
            "id": feat.id,
            "emoji": feat.emoji,
            "name": feat.name,
            "description": feat.description,
            "available": available,
            "enabled": enabled,
            "required_settings": feat.required_settings,
            "default_enabled": feat.default_enabled,
        })
    return result
