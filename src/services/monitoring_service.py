"""
Monitoring Service: Beta-Start Event-Tracking, Error-Logging und Aktivierungsmetriken.

Speichert Events und Fehler in SQLite (data/monitoring.db).
"""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

# Erlaubte Event-Typen
VALID_EVENT_TYPES = {
    "invite_sent",
    "invite_opened",
    "invite_accepted",
    "first_login",
    "onboarding_completed",
    "first_document_uploaded",
    "first_transaction_added",
    "first_task_completed",
}

DB_PATH = settings.DATA_DIR / "monitoring.db"


def _get_conn() -> sqlite3.Connection:
    """Gibt eine SQLite-Verbindung zurueck und erstellt Tabellen bei Bedarf."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monitoring_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            user_key TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monitoring_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            message TEXT NOT NULL,
            stack_trace TEXT,
            user_key TEXT,
            url TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


class MonitoringService:
    """Beta-Monitoring: Events tracken, Fehler erfassen, KPIs berechnen."""

    def track_event(
        self,
        event_type: str,
        user_key: Optional[str] = None,
        metadata: Optional[str] = None,
    ) -> dict:
        """Erfasst ein Monitoring-Event."""
        if event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"Unbekannter Event-Typ: {event_type}. Erlaubt: {VALID_EVENT_TYPES}")

        now = datetime.now(timezone.utc).isoformat()
        conn = _get_conn()
        try:
            cur = conn.execute(
                "INSERT INTO monitoring_events (event_type, user_key, metadata, created_at) VALUES (?, ?, ?, ?)",
                (event_type, user_key, metadata, now),
            )
            conn.commit()
            return {"id": cur.lastrowid, "event_type": event_type, "user_key": user_key, "metadata": metadata, "created_at": now}
        finally:
            conn.close()

    def log_error(
        self,
        source: str,
        message: str,
        stack_trace: Optional[str] = None,
        user_key: Optional[str] = None,
        url: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        """Erfasst einen Frontend- oder Backend-Fehler."""
        now = datetime.now(timezone.utc).isoformat()
        conn = _get_conn()
        try:
            cur = conn.execute(
                "INSERT INTO monitoring_errors (source, message, stack_trace, user_key, url, user_agent, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (source, message, stack_trace, user_key, url, user_agent, now),
            )
            conn.commit()
            return {"id": cur.lastrowid, "source": source, "message": message, "stack_trace": stack_trace, "user_key": user_key, "url": url, "user_agent": user_agent, "created_at": now}
        finally:
            conn.close()

    def get_dashboard(self) -> dict:
        """Berechnet KPIs fuer das Monitoring-Dashboard."""
        conn = _get_conn()
        try:
            # Event-Counts nach Typ
            rows = conn.execute(
                "SELECT event_type, COUNT(*) as cnt FROM monitoring_events GROUP BY event_type"
            ).fetchall()
            event_counts = {row["event_type"]: row["cnt"] for row in rows}

            # Aktivierungsmetriken
            invited = event_counts.get("invite_sent", 0)
            accepted = event_counts.get("invite_accepted", 0)
            first_login = event_counts.get("first_login", 0)
            onboarded = event_counts.get("onboarding_completed", 0)

            activation_rate = round(accepted / invited * 100, 1) if invited > 0 else 0.0
            login_rate = round(first_login / accepted * 100, 1) if accepted > 0 else 0.0
            onboarding_rate = round(onboarded / first_login * 100, 1) if first_login > 0 else 0.0

            # Fehler-Counts (letzte 24h und gesamt)
            total_errors = conn.execute("SELECT COUNT(*) FROM monitoring_errors").fetchone()[0]
            recent_errors = conn.execute(
                "SELECT COUNT(*) FROM monitoring_errors WHERE created_at >= datetime('now', '-1 day')"
            ).fetchone()[0]

            # Gesamtzahl Events
            total_events = conn.execute("SELECT COUNT(*) FROM monitoring_events").fetchone()[0]

            return {
                "event_counts": event_counts,
                "total_events": total_events,
                "metrics": {
                    "activation_rate": activation_rate,
                    "login_rate": login_rate,
                    "onboarding_rate": onboarding_rate,
                },
                "errors": {
                    "total": total_errors,
                    "last_24h": recent_errors,
                },
            }
        finally:
            conn.close()

    def get_errors(self, limit: int = 50, source: Optional[str] = None) -> list[dict]:
        """Gibt die letzten Fehler zurueck."""
        conn = _get_conn()
        try:
            if source:
                rows = conn.execute(
                    "SELECT * FROM monitoring_errors WHERE source = ? ORDER BY created_at DESC LIMIT ?",
                    (source, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM monitoring_errors ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_events(self, event_type: Optional[str] = None, limit: int = 100) -> list[dict]:
        """Gibt Events zurueck, optional gefiltert nach Typ."""
        conn = _get_conn()
        try:
            if event_type:
                rows = conn.execute(
                    "SELECT * FROM monitoring_events WHERE event_type = ? ORDER BY created_at DESC LIMIT ?",
                    (event_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM monitoring_events ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
