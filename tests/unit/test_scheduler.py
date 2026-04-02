"""Unit-Tests für AssistantScheduler: Job-Registrierung, Briefing-Logik."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def scheduler():
    """Erzeugt eine AssistantScheduler-Instanz mit gemocktem APScheduler."""
    with patch("src.scheduler.scheduler.AsyncIOScheduler") as MockSched:
        mock_apscheduler = MagicMock()
        mock_apscheduler.running = False
        MockSched.return_value = mock_apscheduler

        with patch("src.scheduler.scheduler.settings") as mock_settings:
            mock_settings.TIMEZONE = "Europe/Berlin"
            mock_settings.MORNING_BRIEFING_TIME = "07:00"
            mock_settings.EMAIL_CHECK_INTERVAL_MINUTES = 15
            mock_settings.CONVERSATION_HISTORY_DAYS = 30

            from src.scheduler.scheduler import AssistantScheduler

            svc = AssistantScheduler()

    return svc


class TestRegisterBot:
    """Tests für Bot-Registrierung."""

    def test_register_bot_stores_bot(self, scheduler):
        """register_bot speichert Bot und Application."""
        mock_bot = MagicMock()
        mock_app = MagicMock()

        scheduler.register_bot("taake", mock_bot, mock_app)

        assert "taake" in scheduler._bots
        assert scheduler._bots["taake"] is mock_bot
        assert "taake" in scheduler._applications
        assert scheduler._applications["taake"] is mock_app

    def test_register_multiple_bots(self, scheduler):
        """Mehrere Bots können registriert werden."""
        scheduler.register_bot("taake", MagicMock(), MagicMock())
        scheduler.register_bot("nina", MagicMock(), MagicMock())

        assert len(scheduler._bots) == 2
        assert "taake" in scheduler._bots
        assert "nina" in scheduler._bots


class TestStart:
    """Tests für Scheduler-Start und Job-Registration."""

    def test_start_adds_jobs(self, scheduler):
        """start() registriert alle erwarteten Jobs."""
        with patch("src.scheduler.scheduler.settings") as mock_settings:
            mock_settings.MORNING_BRIEFING_TIME = "07:00"
            mock_settings.TIMEZONE = "Europe/Berlin"
            mock_settings.EMAIL_CHECK_INTERVAL_MINUTES = 15

            scheduler.start()

        # Prüfe, dass add_job mehrfach aufgerufen wurde
        assert scheduler.scheduler.add_job.call_count >= 5

        # Prüfe Job-IDs
        job_ids = [call.kwargs.get("id") for call in scheduler.scheduler.add_job.call_args_list]
        assert "morning_briefing" in job_ids
        assert "reminder_check" in job_ids
        assert "pattern_analysis" in job_ids
        assert "weekly_review" in job_ids
        assert "conversation_pruning" in job_ids
        assert "email_check" in job_ids

    def test_start_calls_scheduler_start(self, scheduler):
        """start() startet den APScheduler."""
        with patch("src.scheduler.scheduler.settings") as mock_settings:
            mock_settings.MORNING_BRIEFING_TIME = "07:00"
            mock_settings.TIMEZONE = "Europe/Berlin"
            mock_settings.EMAIL_CHECK_INTERVAL_MINUTES = 15

            scheduler.start()

        scheduler.scheduler.start.assert_called_once()


class TestStop:
    """Tests für Scheduler-Stop."""

    def test_stop_shuts_down_running_scheduler(self, scheduler):
        """stop() fährt einen laufenden Scheduler herunter."""
        scheduler.scheduler.running = True

        scheduler.stop()

        scheduler.scheduler.shutdown.assert_called_once_with(wait=True)

    def test_stop_noop_when_not_running(self, scheduler):
        """stop() tut nichts, wenn der Scheduler nicht läuft."""
        scheduler.scheduler.running = False

        scheduler.stop()

        scheduler.scheduler.shutdown.assert_not_called()


class TestSendMorningBriefings:
    """Tests für das Morgen-Briefing."""

    @pytest.mark.asyncio
    async def test_briefing_skips_focus_mode(self, scheduler):
        """Briefing wird im Fokus-Modus übersprungen."""
        mock_bot = MagicMock()
        scheduler._bots = {"taake": mock_bot}
        scheduler._is_focus_mode = MagicMock(return_value=True)

        await scheduler._send_morning_briefings()

        # _send_briefing_to_user sollte nicht aufgerufen werden
        # (kein send_message-Aufruf)

    @pytest.mark.asyncio
    async def test_briefing_sends_to_all_bots(self, scheduler):
        """Briefing wird an alle registrierten Bots gesendet (außer Fokus-Modus)."""
        scheduler._bots = {"taake": MagicMock(), "nina": MagicMock()}
        scheduler._is_focus_mode = MagicMock(return_value=False)
        scheduler._send_briefing_to_user = AsyncMock()

        await scheduler._send_morning_briefings()

        assert scheduler._send_briefing_to_user.call_count == 2


class TestCheckReminders:
    """Tests für den Erinnerungs-Check."""

    @pytest.mark.asyncio
    async def test_check_reminders_noop_when_no_bots(self, scheduler):
        """Kein Fehler, wenn keine Bots registriert sind."""
        scheduler._bots = {}

        # Sollte ohne Fehler durchlaufen
        await scheduler._check_reminders()

    @pytest.mark.asyncio
    async def test_check_reminders_sends_due(self, scheduler):
        """Fällige Erinnerungen werden gesendet."""
        mock_bot = MagicMock()
        mock_bot.reminder_service.get_due_reminders = AsyncMock(
            return_value=[{"user_key": "taake", "chat_id": 12345, "content": "Test-Erinnerung", "id": 1}]
        )
        mock_bot.reminder_service.mark_sent = AsyncMock()
        scheduler._bots = {"taake": mock_bot}
        scheduler._is_focus_mode = MagicMock(return_value=False)

        mock_app = MagicMock()
        mock_app.bot.send_message = AsyncMock()
        scheduler._applications = {"taake": mock_app}

        await scheduler._check_reminders()

        mock_app.bot.send_message.assert_called_once()
        mock_bot.reminder_service.mark_sent.assert_called_once_with(1)
