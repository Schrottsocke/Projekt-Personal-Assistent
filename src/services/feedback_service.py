"""
Feedback Service: Bug-Reports und UX-Bewertungen von Beta-Testern.

Speichert Feedback in SQLite (data/feedback.db).
"""

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

VALID_TRIAGE_STATES = {"new", "needs-info", "accepted", "duplicate", "wontfix", "done"}

DB_PATH = settings.DATA_DIR / "feedback.db"


def _get_conn() -> sqlite3.Connection:
    """Gibt eine SQLite-Verbindung zurueck und erstellt Tabellen bei Bedarf."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT NOT NULL,
            feedback_type TEXT NOT NULL,
            triage_status TEXT NOT NULL DEFAULT 'new',
            area TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            -- Bug-Report Felder
            title TEXT,
            expected TEXT,
            actual TEXT,
            steps TEXT,
            device TEXT,
            severity TEXT,

            -- UX-Bewertung Felder
            rating_clarity INTEGER,
            rating_speed INTEGER,
            rating_trust INTEGER,
            rating_mobile_comfort INTEGER,
            comment TEXT
        )
    """)
    conn.commit()
    return conn


class FeedbackService:
    """Bug-Reports und UX-Bewertungen verwalten."""

    def create_bug_report(
        self,
        user_key: str,
        title: str,
        area: Optional[str] = None,
        expected: Optional[str] = None,
        actual: Optional[str] = None,
        steps: Optional[str] = None,
        device: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> dict:
        """Erstellt einen neuen Bug-Report."""
        now = datetime.now(timezone.utc).isoformat()
        conn = _get_conn()
        try:
            cur = conn.execute(
                """INSERT INTO feedback
                   (user_key, feedback_type, triage_status, area, title, expected, actual, steps, device, severity, created_at, updated_at)
                   VALUES (?, 'bug', 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_key, area, title, expected, actual, steps, device, severity, now, now),
            )
            conn.commit()
            return self._get_by_id(conn, cur.lastrowid)
        finally:
            conn.close()

    def create_ux_rating(
        self,
        user_key: str,
        area: Optional[str] = None,
        rating_clarity: Optional[int] = None,
        rating_speed: Optional[int] = None,
        rating_trust: Optional[int] = None,
        rating_mobile_comfort: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> dict:
        """Erstellt eine neue UX-Bewertung."""
        now = datetime.now(timezone.utc).isoformat()
        conn = _get_conn()
        try:
            cur = conn.execute(
                """INSERT INTO feedback
                   (user_key, feedback_type, triage_status, area, rating_clarity, rating_speed, rating_trust, rating_mobile_comfort, comment, created_at, updated_at)
                   VALUES (?, 'ux', 'new', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_key, area, rating_clarity, rating_speed, rating_trust, rating_mobile_comfort, comment, now, now),
            )
            conn.commit()
            return self._get_by_id(conn, cur.lastrowid)
        finally:
            conn.close()

    def get_all(
        self,
        feedback_type: Optional[str] = None,
        triage_status: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Gibt alle Feedback-Eintraege zurueck, optional gefiltert."""
        conn = _get_conn()
        try:
            query = "SELECT * FROM feedback WHERE 1=1"
            params: list = []
            if feedback_type:
                query += " AND feedback_type = ?"
                params.append(feedback_type)
            if triage_status:
                query += " AND triage_status = ?"
                params.append(triage_status)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def update_triage(self, feedback_id: int, new_status: str) -> Optional[dict]:
        """Aendert den Triage-Status eines Feedback-Eintrags."""
        if new_status not in VALID_TRIAGE_STATES:
            raise ValueError(f"Ungueltiger Triage-Status: {new_status}. Erlaubt: {VALID_TRIAGE_STATES}")

        now = datetime.now(timezone.utc).isoformat()
        conn = _get_conn()
        try:
            conn.execute(
                "UPDATE feedback SET triage_status = ?, updated_at = ? WHERE id = ?",
                (new_status, now, feedback_id),
            )
            conn.commit()
            return self._get_by_id(conn, feedback_id)
        finally:
            conn.close()

    def get_by_id(self, feedback_id: int) -> Optional[dict]:
        """Gibt ein Feedback anhand der ID zurueck."""
        conn = _get_conn()
        try:
            return self._get_by_id(conn, feedback_id)
        finally:
            conn.close()

    def _get_by_id(self, conn: sqlite3.Connection, feedback_id: int) -> Optional[dict]:
        row = conn.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
        if row:
            return dict(row)
        return None
