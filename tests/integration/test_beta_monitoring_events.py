"""Integration-Tests fuer Beta-Monitoring-Service (Issue #730)."""

import os
import tempfile
import unittest
from unittest.mock import patch


class TestMonitoringService(unittest.TestCase):
    """Testet MonitoringService Event-Tracking, Error-Logging und Dashboard."""

    def setUp(self):
        # Temporaere DB fuer isolierte Tests
        self._tmpdir = tempfile.mkdtemp()
        self._db_path = os.path.join(self._tmpdir, "monitoring.db")

        import src.services.monitoring_service as mod
        self._original_db_path = mod.DB_PATH
        from pathlib import Path
        mod.DB_PATH = Path(self._db_path)

        from src.services.monitoring_service import MonitoringService
        self.service = MonitoringService()

    def tearDown(self):
        import src.services.monitoring_service as mod
        mod.DB_PATH = self._original_db_path
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_track_valid_event(self):
        """Gueltige Events werden gespeichert."""
        result = self.service.track_event("invite_sent", user_key="taake")
        self.assertIn("id", result)
        self.assertEqual(result["event_type"], "invite_sent")
        self.assertEqual(result["user_key"], "taake")

    def test_track_invalid_event(self):
        """Unbekannte Event-Typen werden abgelehnt."""
        with self.assertRaises(ValueError):
            self.service.track_event("unknown_event")

    def test_log_error(self):
        """Fehler werden gespeichert."""
        result = self.service.log_error(
            source="frontend",
            message="TypeError: undefined",
            user_key="taake",
            url="/app#/dashboard",
        )
        self.assertIn("id", result)
        self.assertEqual(result["source"], "frontend")

    def test_dashboard_empty(self):
        """Dashboard mit leerer DB gibt Null-Werte."""
        dashboard = self.service.get_dashboard()
        self.assertEqual(dashboard["total_events"], 0)
        self.assertEqual(dashboard["errors"]["total"], 0)
        self.assertEqual(dashboard["metrics"]["activation_rate"], 0.0)

    def test_dashboard_with_events(self):
        """Dashboard berechnet Metriken korrekt."""
        self.service.track_event("invite_sent", user_key="a")
        self.service.track_event("invite_sent", user_key="b")
        self.service.track_event("invite_accepted", user_key="a")
        self.service.track_event("first_login", user_key="a")

        dashboard = self.service.get_dashboard()
        self.assertEqual(dashboard["total_events"], 4)
        self.assertEqual(dashboard["event_counts"]["invite_sent"], 2)
        self.assertEqual(dashboard["event_counts"]["invite_accepted"], 1)
        self.assertEqual(dashboard["metrics"]["activation_rate"], 50.0)
        self.assertEqual(dashboard["metrics"]["login_rate"], 100.0)

    def test_get_errors_with_filter(self):
        """Fehler koennen nach Source gefiltert werden."""
        self.service.log_error("frontend", "Error 1")
        self.service.log_error("backend", "Error 2")
        self.service.log_error("frontend", "Error 3")

        frontend_errors = self.service.get_errors(source="frontend")
        self.assertEqual(len(frontend_errors), 2)

        backend_errors = self.service.get_errors(source="backend")
        self.assertEqual(len(backend_errors), 1)

    def test_get_events_with_filter(self):
        """Events koennen nach Typ gefiltert werden."""
        self.service.track_event("invite_sent")
        self.service.track_event("first_login")
        self.service.track_event("invite_sent")

        events = self.service.get_events(event_type="invite_sent")
        self.assertEqual(len(events), 2)

    def test_all_valid_event_types(self):
        """Alle definierten Event-Typen koennen getracked werden."""
        from src.services.monitoring_service import VALID_EVENT_TYPES
        for event_type in VALID_EVENT_TYPES:
            result = self.service.track_event(event_type)
            self.assertEqual(result["event_type"], event_type)


if __name__ == "__main__":
    unittest.main()
