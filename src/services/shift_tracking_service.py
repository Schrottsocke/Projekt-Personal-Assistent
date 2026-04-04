"""
ShiftTrackingService: Zentrale Geschaeftslogik fuer Schicht-Tracking.

Verwaltet Soll/Ist-Abgleich, Bestaetigungen, Reminder-Logik und Monatsauswertung.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class ShiftTrackingService:
    def __init__(self):
        self._db = None

    async def initialize(self):
        from src.services.database import get_db, init_db

        init_db()
        self._db = get_db()
        logger.info("ShiftTrackingService initialisiert.")

    def _ensure_db(self):
        if self._db is None:
            raise RuntimeError("ShiftTrackingService not initialized")

    # ─── Hilfsfunktionen ─────────────────────────────────────

    @staticmethod
    def compute_duration(start_time: Optional[str], end_time: Optional[str], break_minutes: int = 0) -> Optional[int]:
        """Berechnet Dauer in Minuten aus HH:MM-Strings. Beruecksichtigt Mitternacht."""
        if not start_time or not end_time:
            return None
        try:
            sh, sm = map(int, start_time.split(":"))
            eh, em = map(int, end_time.split(":"))
            start_min = sh * 60 + sm
            end_min = eh * 60 + em
            if end_min <= start_min:
                end_min += 24 * 60  # Mitternachtsueberschreitung
            duration = end_min - start_min - break_minutes
            return max(duration, 0)
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def effective_planned_times(entry, shift_type) -> tuple[Optional[str], Optional[str], int]:
        """Gibt effektive Soll-Zeiten zurueck (Entry-Override oder ShiftType-Default).

        Returns: (planned_start, planned_end, break_minutes)
        """
        p_start = entry.planned_start or (shift_type.start_time if shift_type else None)
        p_end = entry.planned_end or (shift_type.end_time if shift_type else None)
        brk = (
            entry.break_minutes if entry.break_minutes is not None else (shift_type.break_minutes if shift_type else 0)
        )
        return p_start, p_end, brk or 0

    def _entry_to_dict(self, entry, shift_type=None) -> dict:
        """Konvertiert einen ShiftEntry + optionalen ShiftType zu einem Dict."""
        d = {c.name: getattr(entry, c.name) for c in entry.__table__.columns}
        # Serialisiere datetime-Felder
        for key in ("created_at", "confirmation_timestamp", "next_reminder_at"):
            if d.get(key) and isinstance(d[key], datetime):
                d[key] = d[key].isoformat()
        if shift_type:
            d["shift_type_name"] = shift_type.name
            d["shift_type_short_name"] = shift_type.short_name
            d["shift_type_color"] = shift_type.color
            d["shift_type_start_time"] = shift_type.start_time
            d["shift_type_end_time"] = shift_type.end_time
            d["shift_type_category"] = shift_type.category
        return d

    def _get_entry_with_type(self, session, entry_id: int, user_key: str):
        """Laedt ShiftEntry + ShiftType oder wirft ValueError."""
        from src.services.database import ShiftEntry, ShiftType

        result = (
            session.query(ShiftEntry, ShiftType)
            .outerjoin(ShiftType, ShiftEntry.shift_type_id == ShiftType.id)
            .filter(ShiftEntry.id == entry_id, ShiftEntry.user_key == user_key)
            .first()
        )
        if not result:
            raise ValueError(f"Diensteintrag #{entry_id} nicht gefunden.")
        return result

    # ─── Bestaetigungs-Aktionen ──────────────────────────────

    def confirm_shift(self, entry_id: int, user_key: str, source: str = "web") -> dict:
        """Dienst als normal beendet bestaetigen. Soll-Zeiten werden als Ist uebernommen."""
        self._ensure_db()
        with self._db() as session:
            entry, stype = self._get_entry_with_type(session, entry_id, user_key)

            if entry.confirmation_status not in ("pending", None):
                raise ValueError(f"Dienst bereits bestaetigt (Status: {entry.confirmation_status}).")

            p_start, p_end, brk = self.effective_planned_times(entry, stype)
            planned_dur = self.compute_duration(p_start, p_end, brk)

            # Ist = Soll (sofern noch keine Ist-Zeiten gesetzt)
            if not entry.actual_start:
                entry.actual_start = p_start
            if not entry.actual_end:
                entry.actual_end = p_end
            if entry.actual_break_minutes is None:
                entry.actual_break_minutes = brk

            actual_dur = self.compute_duration(entry.actual_start, entry.actual_end, entry.actual_break_minutes or 0)

            entry.planned_duration_minutes = planned_dur
            entry.actual_duration_minutes = actual_dur
            entry.delta_minutes = (actual_dur or 0) - (planned_dur or 0)
            entry.confirmation_status = "confirmed"
            entry.confirmation_source = source
            entry.confirmation_timestamp = datetime.now(timezone.utc)

            session.flush()
            session.refresh(entry)
            return self._entry_to_dict(entry, stype)

    def record_deviation(
        self,
        entry_id: int,
        user_key: str,
        actual_start: str,
        actual_end: str,
        actual_break: int = 0,
        note: Optional[str] = None,
        source: str = "web",
    ) -> dict:
        """Dienst mit Abweichung bestaetigen."""
        self._ensure_db()
        with self._db() as session:
            entry, stype = self._get_entry_with_type(session, entry_id, user_key)

            p_start, p_end, brk = self.effective_planned_times(entry, stype)
            planned_dur = self.compute_duration(p_start, p_end, brk)

            entry.actual_start = actual_start
            entry.actual_end = actual_end
            entry.actual_break_minutes = actual_break
            actual_dur = self.compute_duration(actual_start, actual_end, actual_break)

            entry.planned_duration_minutes = planned_dur
            entry.actual_duration_minutes = actual_dur
            entry.delta_minutes = (actual_dur or 0) - (planned_dur or 0)
            entry.confirmation_status = "deviation"
            entry.confirmation_source = source
            entry.confirmation_timestamp = datetime.now(timezone.utc)
            if note:
                entry.deviation_note = note

            session.flush()
            session.refresh(entry)
            return self._entry_to_dict(entry, stype)

    def cancel_shift(self, entry_id: int, user_key: str, source: str = "web") -> dict:
        """Dienst als ausgefallen markieren."""
        self._ensure_db()
        with self._db() as session:
            entry, stype = self._get_entry_with_type(session, entry_id, user_key)

            p_start, p_end, brk = self.effective_planned_times(entry, stype)
            planned_dur = self.compute_duration(p_start, p_end, brk)

            entry.actual_start = None
            entry.actual_end = None
            entry.actual_break_minutes = 0
            entry.planned_duration_minutes = planned_dur
            entry.actual_duration_minutes = 0
            entry.delta_minutes = -(planned_dur or 0)
            entry.confirmation_status = "cancelled"
            entry.confirmation_source = source
            entry.confirmation_timestamp = datetime.now(timezone.utc)

            session.flush()
            session.refresh(entry)
            return self._entry_to_dict(entry, stype)

    def snooze_reminder(self, entry_id: int, user_key: str, minutes: int = 60) -> dict:
        """Erinnerung verschieben."""
        self._ensure_db()
        with self._db() as session:
            entry, stype = self._get_entry_with_type(session, entry_id, user_key)

            entry.next_reminder_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
            entry.reminder_count = (entry.reminder_count or 0) + 1

            session.flush()
            session.refresh(entry)
            return self._entry_to_dict(entry, stype)

    # ─── Manuelle Bearbeitung ────────────────────────────────

    def update_entry(self, entry_id: int, user_key: str, updates: dict) -> dict:
        """Manuelle Bearbeitung der Ist-Zeiten und anderer Felder."""
        self._ensure_db()
        ALLOWED_FIELDS = {
            "actual_start",
            "actual_end",
            "actual_break_minutes",
            "planned_start",
            "planned_end",
            "break_minutes",
            "deviation_note",
            "note",
            "confirmation_status",
        }

        with self._db() as session:
            entry, stype = self._get_entry_with_type(session, entry_id, user_key)

            for key, val in updates.items():
                if key in ALLOWED_FIELDS:
                    setattr(entry, key, val)

            # Dauern neu berechnen
            p_start, p_end, brk = self.effective_planned_times(entry, stype)
            entry.planned_duration_minutes = self.compute_duration(p_start, p_end, brk)

            if entry.actual_start and entry.actual_end:
                entry.actual_duration_minutes = self.compute_duration(
                    entry.actual_start, entry.actual_end, entry.actual_break_minutes or 0
                )
                entry.delta_minutes = (entry.actual_duration_minutes or 0) - (entry.planned_duration_minutes or 0)

            entry.confirmation_source = "manual"
            entry.confirmation_timestamp = datetime.now(timezone.utc)

            session.flush()
            session.refresh(entry)
            return self._entry_to_dict(entry, stype)

    # ─── Reminder-Logik ──────────────────────────────────────

    def get_due_shift_reminders(self, now_local: datetime) -> list[dict]:
        """Findet alle Dienste, die jetzt eine Erinnerung brauchen.

        Args:
            now_local: Aktuelle Zeit in der lokalen Zeitzone (Europe/Berlin)
        """
        self._ensure_db()
        from src.services.database import ShiftEntry, ShiftType

        today_str = now_local.strftime("%Y-%m-%d")
        yesterday_str = (now_local - timedelta(days=1)).strftime("%Y-%m-%d")
        now_utc = datetime.now(timezone.utc)

        with self._db() as session:
            candidates = (
                session.query(ShiftEntry, ShiftType)
                .outerjoin(ShiftType, ShiftEntry.shift_type_id == ShiftType.id)
                .filter(
                    ShiftEntry.confirmation_status.in_(["pending", None]),
                    ShiftEntry.date.in_([today_str, yesterday_str]),
                    ShiftEntry.reminder_count < 3,
                )
                .all()
            )

            due = []
            for entry, stype in candidates:
                if not stype or stype.category != "work":
                    continue

                # Effektive Endzeit
                end_time = entry.planned_end or (stype.end_time if stype else None)
                if not end_time:
                    continue

                # Planned-End als datetime berechnen
                eh, em = map(int, end_time.split(":"))
                start_time = entry.planned_start or (stype.start_time if stype else None)
                entry_date = datetime.strptime(entry.date, "%Y-%m-%d")

                # Mitternachtsueberschreitung: wenn end < start, Ende am naechsten Tag
                if start_time:
                    sh, sm = map(int, start_time.split(":"))
                    if eh * 60 + em <= sh * 60 + sm:
                        entry_date += timedelta(days=1)

                planned_end_local = entry_date.replace(hour=eh, minute=em, second=0, microsecond=0)
                reminder_trigger = planned_end_local + timedelta(minutes=30)

                if now_local < reminder_trigger:
                    continue

                # Snooze-Check
                if entry.next_reminder_at and now_utc < entry.next_reminder_at:
                    continue

                # Erster Reminder oder Snooze abgelaufen
                if entry.reminder_sent and not entry.next_reminder_at:
                    continue  # Bereits gesendet, kein Snooze aktiv

                due.append(self._entry_to_dict(entry, stype))

            return due

    def mark_reminder_sent(self, entry_id: int) -> None:
        """Markiert einen Dienst als Reminder-gesendet."""
        self._ensure_db()
        from src.services.database import ShiftEntry

        with self._db() as session:
            entry = session.query(ShiftEntry).filter_by(id=entry_id).first()
            if entry:
                entry.reminder_sent = True
                entry.reminder_count = (entry.reminder_count or 0) + 1
                entry.next_reminder_at = None

    # ─── Monatsauswertung ────────────────────────────────────

    def get_monthly_report(self, user_key: str, year: int, month: int) -> dict:
        """Soll/Ist-Abgleich fuer einen Monat."""
        self._ensure_db()
        from src.services.database import ShiftEntry, ShiftType

        start = f"{year:04d}-{month:02d}-01"
        last_day = 28
        for d in (31, 30, 29, 28):
            try:
                datetime(year, month, d)
                last_day = d
                break
            except ValueError:
                continue
        end = f"{year:04d}-{month:02d}-{last_day:02d}"

        with self._db() as session:
            rows = (
                session.query(ShiftEntry, ShiftType)
                .outerjoin(ShiftType, ShiftEntry.shift_type_id == ShiftType.id)
                .filter(
                    ShiftEntry.user_key == user_key,
                    ShiftEntry.date >= start,
                    ShiftEntry.date <= end,
                )
                .order_by(ShiftEntry.date)
                .all()
            )

            entries = []
            summary = {
                "planned_hours": 0.0,
                "actual_hours": 0.0,
                "delta_hours": 0.0,
                "confirmed_count": 0,
                "pending_count": 0,
                "deviation_count": 0,
                "cancelled_count": 0,
            }

            for entry, stype in rows:
                p_start, p_end, brk = self.effective_planned_times(entry, stype)
                planned_dur = entry.planned_duration_minutes or self.compute_duration(p_start, p_end, brk)
                actual_dur = entry.actual_duration_minutes
                delta = entry.delta_minutes
                status = entry.confirmation_status or "pending"

                # Wenn noch keine gespeicherten Dauern, on-the-fly berechnen
                if planned_dur is None:
                    planned_dur = self.compute_duration(p_start, p_end, brk)
                if actual_dur is None and entry.actual_start and entry.actual_end:
                    actual_dur = self.compute_duration(
                        entry.actual_start, entry.actual_end, entry.actual_break_minutes or 0
                    )
                if delta is None and planned_dur is not None and actual_dur is not None:
                    delta = actual_dur - planned_dur

                report_entry = {
                    "id": entry.id,
                    "date": entry.date,
                    "shift_type": stype.name if stype else "?",
                    "shift_type_short": stype.short_name if stype else "?",
                    "shift_color": stype.color if stype else "#7c4dff",
                    "planned_start": p_start,
                    "planned_end": p_end,
                    "actual_start": entry.actual_start,
                    "actual_end": entry.actual_end,
                    "planned_duration": planned_dur,
                    "actual_duration": actual_dur,
                    "delta_minutes": delta,
                    "status": status,
                    "note": entry.deviation_note or entry.note or "",
                    "confirmation_source": entry.confirmation_source,
                }
                entries.append(report_entry)

                # Summierung
                if planned_dur:
                    summary["planned_hours"] += planned_dur / 60
                if actual_dur:
                    summary["actual_hours"] += actual_dur / 60
                if delta:
                    summary["delta_hours"] += delta / 60

                status_key = f"{status}_count"
                if status_key in summary:
                    summary[status_key] += 1

            # Runden
            summary["planned_hours"] = round(summary["planned_hours"], 2)
            summary["actual_hours"] = round(summary["actual_hours"], 2)
            summary["delta_hours"] = round(summary["delta_hours"], 2)

            return {
                "month": f"{year:04d}-{month:02d}",
                "entries": entries,
                "summary": summary,
            }

    def generate_csv(self, user_key: str, year: int, month: int) -> str:
        """Erzeugt CSV-String fuer die Monatsauswertung."""
        report = self.get_monthly_report(user_key, year, month)
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")

        # Header
        writer.writerow(
            [
                "Datum",
                "Typ",
                "Soll-Beginn",
                "Soll-Ende",
                "Ist-Beginn",
                "Ist-Ende",
                "Soll-Dauer (Min)",
                "Ist-Dauer (Min)",
                "Abweichung (Min)",
                "Status",
                "Notiz",
            ]
        )

        for e in report["entries"]:
            writer.writerow(
                [
                    e["date"],
                    e["shift_type"],
                    e["planned_start"] or "",
                    e["planned_end"] or "",
                    e["actual_start"] or "",
                    e["actual_end"] or "",
                    e["planned_duration"] or "",
                    e["actual_duration"] or "",
                    e["delta_minutes"] if e["delta_minutes"] is not None else "",
                    e["status"],
                    e["note"],
                ]
            )

        # Summenzeile
        s = report["summary"]
        writer.writerow([])
        writer.writerow(["Zusammenfassung"])
        writer.writerow(["Soll-Stunden", f"{s['planned_hours']:.2f}"])
        writer.writerow(["Ist-Stunden", f"{s['actual_hours']:.2f}"])
        writer.writerow(["Abweichung (Std)", f"{s['delta_hours']:.2f}"])
        writer.writerow(["Bestaetigt", s["confirmed_count"]])
        writer.writerow(["Offen", s["pending_count"]])
        writer.writerow(["Abweichung", s["deviation_count"]])
        writer.writerow(["Ausgefallen", s["cancelled_count"]])

        return output.getvalue()

    # ─── Offene Dienste ──────────────────────────────────────

    def get_pending_shifts(self, user_key: str) -> list[dict]:
        """Alle offenen (nicht bestaetigten) Dienste."""
        self._ensure_db()
        from src.services.database import ShiftEntry, ShiftType

        with self._db() as session:
            rows = (
                session.query(ShiftEntry, ShiftType)
                .outerjoin(ShiftType, ShiftEntry.shift_type_id == ShiftType.id)
                .filter(
                    ShiftEntry.user_key == user_key,
                    ShiftEntry.confirmation_status.in_(["pending", None]),
                )
                .order_by(ShiftEntry.date.desc())
                .all()
            )
            return [self._entry_to_dict(entry, stype) for entry, stype in rows]
