"""Integration-Tests fuer Feedback-Service (Issue #728)."""

import os
import tempfile
import unittest


class TestFeedbackService(unittest.TestCase):
    """Testet FeedbackService: Bug-Reports, UX-Bewertungen und Triage."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db_path = os.path.join(self._tmpdir, "feedback.db")

        import src.services.feedback_service as mod

        self._original_db_path = mod.DB_PATH
        from pathlib import Path

        mod.DB_PATH = Path(self._db_path)

        from src.services.feedback_service import FeedbackService

        self.service = FeedbackService()

    def tearDown(self):
        import src.services.feedback_service as mod

        mod.DB_PATH = self._original_db_path
        import shutil

        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_create_bug_report(self):
        """Bug-Report wird korrekt erstellt."""
        result = self.service.create_bug_report(
            user_key="taake",
            title="Button reagiert nicht",
            area="dashboard",
            expected="Button oeffnet Dialog",
            actual="Nichts passiert",
            steps="1. Dashboard oeffnen\n2. Auf Button klicken",
            device="iPhone 15, Safari",
            severity="medium",
        )
        self.assertIn("id", result)
        self.assertEqual(result["feedback_type"], "bug")
        self.assertEqual(result["triage_status"], "new")
        self.assertEqual(result["title"], "Button reagiert nicht")
        self.assertEqual(result["severity"], "medium")

    def test_create_ux_rating(self):
        """UX-Bewertung wird korrekt erstellt."""
        result = self.service.create_ux_rating(
            user_key="nina",
            area="onboarding",
            rating_clarity=4,
            rating_speed=5,
            rating_trust=3,
            rating_mobile_comfort=4,
            comment="Insgesamt gut, aber Vertrauen koennte besser sein.",
        )
        self.assertIn("id", result)
        self.assertEqual(result["feedback_type"], "ux")
        self.assertEqual(result["rating_clarity"], 4)
        self.assertEqual(result["rating_speed"], 5)

    def test_get_all(self):
        """Alle Feedback-Eintraege werden zurueckgegeben."""
        self.service.create_bug_report(user_key="a", title="Bug 1")
        self.service.create_ux_rating(user_key="b", rating_clarity=3)
        self.service.create_bug_report(user_key="c", title="Bug 2")

        all_items = self.service.get_all()
        self.assertEqual(len(all_items), 3)

    def test_filter_by_type(self):
        """Feedback kann nach Typ gefiltert werden."""
        self.service.create_bug_report(user_key="a", title="Bug")
        self.service.create_ux_rating(user_key="b")

        bugs = self.service.get_all(feedback_type="bug")
        self.assertEqual(len(bugs), 1)

        ux = self.service.get_all(feedback_type="ux")
        self.assertEqual(len(ux), 1)

    def test_filter_by_triage_status(self):
        """Feedback kann nach Triage-Status gefiltert werden."""
        self.service.create_bug_report(user_key="a", title="Bug")
        new_items = self.service.get_all(triage_status="new")
        self.assertEqual(len(new_items), 1)

        accepted_items = self.service.get_all(triage_status="accepted")
        self.assertEqual(len(accepted_items), 0)

    def test_update_triage(self):
        """Triage-Status kann geaendert werden."""
        bug = self.service.create_bug_report(user_key="a", title="Bug")
        updated = self.service.update_triage(bug["id"], "accepted")
        self.assertEqual(updated["triage_status"], "accepted")

    def test_update_triage_all_states(self):
        """Alle gueltigen Triage-States werden akzeptiert."""
        from src.services.feedback_service import VALID_TRIAGE_STATES

        bug = self.service.create_bug_report(user_key="a", title="Bug")
        for state in VALID_TRIAGE_STATES:
            updated = self.service.update_triage(bug["id"], state)
            self.assertEqual(updated["triage_status"], state)

    def test_update_triage_invalid_state(self):
        """Ungueltiger Triage-Status wird abgelehnt."""
        bug = self.service.create_bug_report(user_key="a", title="Bug")
        with self.assertRaises(ValueError):
            self.service.update_triage(bug["id"], "invalid_state")

    def test_update_triage_not_found(self):
        """Nicht existierende ID gibt None zurueck."""
        result = self.service.update_triage(99999, "accepted")
        self.assertIsNone(result)

    def test_get_by_id(self):
        """Einzelnes Feedback kann per ID abgerufen werden."""
        bug = self.service.create_bug_report(user_key="a", title="Test")
        fetched = self.service.get_by_id(bug["id"])
        self.assertEqual(fetched["title"], "Test")

    def test_get_by_id_not_found(self):
        """Nicht existierende ID gibt None."""
        result = self.service.get_by_id(99999)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
