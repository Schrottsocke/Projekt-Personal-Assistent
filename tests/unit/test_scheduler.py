"""Unit-Tests für AssistantScheduler: Job-Registrierung, Briefing-Logik, Deadline-Jobs."""

import sys
import types
import pytest
from datetime import date, timedelta
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

    def test_start_adds_legacy_jobs(self, scheduler):
        """start() registriert die 7 Legacy-Jobs."""
        with patch("src.scheduler.scheduler.settings") as mock_settings:
            mock_settings.MORNING_BRIEFING_TIME = "07:00"
            mock_settings.TIMEZONE = "Europe/Berlin"
            mock_settings.EMAIL_CHECK_INTERVAL_MINUTES = 15

            scheduler.start()

        # Prüfe Legacy Job-IDs
        job_ids = [call.kwargs.get("id") for call in scheduler.scheduler.add_job.call_args_list]
        assert "morning_briefing" in job_ids
        assert "reminder_check" in job_ids
        assert "pattern_analysis" in job_ids
        assert "weekly_review" in job_ids
        assert "conversation_pruning" in job_ids
        assert "email_check" in job_ids
        assert "shift_reminder_check" in job_ids

    def test_start_adds_deadline_jobs(self, scheduler):
        """start() registriert die 5 neuen Deadline/Fristen-Jobs."""
        with patch("src.scheduler.scheduler.settings") as mock_settings:
            mock_settings.MORNING_BRIEFING_TIME = "07:00"
            mock_settings.TIMEZONE = "Europe/Berlin"
            mock_settings.EMAIL_CHECK_INTERVAL_MINUTES = 15

            scheduler.start()

        job_ids = [call.kwargs.get("id") for call in scheduler.scheduler.add_job.call_args_list]
        assert "contract_deadline_check" in job_ids
        assert "overdue_invoice_check" in job_ids
        assert "warranty_expiry_check" in job_ids
        assert "document_deadline_check" in job_ids
        assert "routine_reminder_check" in job_ids

    def test_start_registers_12_jobs_total(self, scheduler):
        """start() registriert insgesamt 12 Jobs (7 Legacy + 5 Deadline)."""
        with patch("src.scheduler.scheduler.settings") as mock_settings:
            mock_settings.MORNING_BRIEFING_TIME = "07:00"
            mock_settings.TIMEZONE = "Europe/Berlin"
            mock_settings.EMAIL_CHECK_INTERVAL_MINUTES = 15

            scheduler.start()

        assert scheduler.scheduler.add_job.call_count == 12

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


# ---------------------------------------------------------------------------
# Deadline/Fristen-Job Tests
# ---------------------------------------------------------------------------


def _mock_db_and_notif():
    """Create mock NotificationService and prepare DB mock module."""
    mock_notif_svc = MagicMock()
    mock_notif_svc.initialize = AsyncMock()
    mock_notif_svc.create = AsyncMock()

    mock_notif_mod = types.ModuleType("src.services.notification_service")
    mock_notif_mod.NotificationService = MagicMock(return_value=mock_notif_svc)

    mock_db_mod = types.ModuleType("src.services.database")
    mock_db_mod.Contract = MagicMock()
    mock_db_mod.UserProfile = MagicMock()
    mock_db_mod.FinanceInvoice = MagicMock()
    mock_db_mod.HouseholdDocument = MagicMock()
    mock_db_mod.Warranty = MagicMock()
    mock_db_mod.Routine = MagicMock()
    mock_db_mod.RoutineCompletion = MagicMock()
    mock_db_mod.get_db = MagicMock()

    return mock_notif_svc, mock_notif_mod, mock_db_mod


class TestContractDeadlineJob:
    """Tests für check_contract_deadlines."""

    @pytest.mark.asyncio
    async def test_creates_notification_at_7_day_threshold(self):
        """Erzeugt Benachrichtigung wenn Frist genau auf 7-Tage-Threshold fällt."""
        today = date.today()
        deadline = today + timedelta(days=7)

        mock_contract_data = [
            {
                "id": 1,
                "name": "Internet-Vertrag",
                "provider": "Telekom",
                "cancellation_deadline": deadline,
                "next_billing": None,
                "cancellation_days": None,
                "user_key": "taake",
            }
        ]

        mock_notif_svc, mock_notif_mod, mock_db_mod = _mock_db_and_notif()

        with patch.dict(
            sys.modules,
            {
                "src.services.database": mock_db_mod,
                "src.services.notification_service": mock_notif_mod,
            },
        ):
            with patch(
                "asyncio.to_thread", new_callable=lambda: lambda *a, **k: AsyncMock(return_value=mock_contract_data)
            ):
                import importlib
                import src.scheduler.jobs.contract_jobs as mod

                importlib.reload(mod)

                with patch.object(mod.asyncio, "to_thread", AsyncMock(return_value=mock_contract_data)):
                    await mod.check_contract_deadlines()

        mock_notif_svc.create.assert_called_once()
        call_kwargs = mock_notif_svc.create.call_args.kwargs
        assert call_kwargs["user_key"] == "taake"
        assert "Kuendigungsfrist" in call_kwargs["title"]
        assert "Internet-Vertrag" in call_kwargs["title"]

    @pytest.mark.asyncio
    async def test_calculates_deadline_from_next_billing(self):
        """Berechnet Deadline aus next_billing - cancellation_days wenn kein cancellation_deadline."""
        today = date.today()
        # next_billing in 37 days, cancellation_days=30 -> deadline in 7 days
        next_billing = today + timedelta(days=37)

        mock_contract_data = [
            {
                "id": 2,
                "name": "Strom-Vertrag",
                "provider": "EON",
                "cancellation_deadline": None,
                "next_billing": next_billing,
                "cancellation_days": 30,
                "user_key": "taake",
            }
        ]

        mock_notif_svc, mock_notif_mod, mock_db_mod = _mock_db_and_notif()

        with patch.dict(
            sys.modules,
            {
                "src.services.database": mock_db_mod,
                "src.services.notification_service": mock_notif_mod,
            },
        ):
            import importlib
            import src.scheduler.jobs.contract_jobs as mod

            importlib.reload(mod)

            with patch.object(mod.asyncio, "to_thread", AsyncMock(return_value=mock_contract_data)):
                await mod.check_contract_deadlines()

        mock_notif_svc.create.assert_called_once()
        assert "Strom-Vertrag" in mock_notif_svc.create.call_args.kwargs["title"]

    @pytest.mark.asyncio
    async def test_no_notification_outside_thresholds(self):
        """Keine Benachrichtigung wenn Frist nicht auf Threshold-Tag fällt."""
        today = date.today()
        deadline = today + timedelta(days=20)  # Not a threshold day

        mock_contract_data = [
            {
                "id": 3,
                "name": "Handy-Vertrag",
                "provider": "O2",
                "cancellation_deadline": deadline,
                "next_billing": None,
                "cancellation_days": None,
                "user_key": "taake",
            }
        ]

        mock_notif_svc, mock_notif_mod, mock_db_mod = _mock_db_and_notif()

        with patch.dict(
            sys.modules,
            {
                "src.services.database": mock_db_mod,
                "src.services.notification_service": mock_notif_mod,
            },
        ):
            import importlib
            import src.scheduler.jobs.contract_jobs as mod

            importlib.reload(mod)

            with patch.object(mod.asyncio, "to_thread", AsyncMock(return_value=mock_contract_data)):
                await mod.check_contract_deadlines()

        mock_notif_svc.create.assert_not_called()


class TestOverdueInvoiceJob:
    """Tests für check_overdue_invoices."""

    @pytest.mark.asyncio
    async def test_marks_overdue_and_notifies(self):
        """Ueberfaellige Rechnungen werden erkannt und Notification erstellt."""
        overdue_data = [
            {
                "id": 1,
                "recipient": "Max Mustermann",
                "total": 150.00,
                "due_date": (date.today() - timedelta(days=3)).isoformat(),
                "invoice_number": "INV-001",
                "user_key": "taake",
            }
        ]

        mock_notif_svc, mock_notif_mod, mock_db_mod = _mock_db_and_notif()

        with patch.dict(
            sys.modules,
            {
                "src.services.database": mock_db_mod,
                "src.services.notification_service": mock_notif_mod,
            },
        ):
            import importlib
            import src.scheduler.jobs.invoice_jobs as mod

            importlib.reload(mod)

            with patch.object(mod.asyncio, "to_thread", AsyncMock(return_value=overdue_data)):
                await mod.check_overdue_invoices()

        mock_notif_svc.create.assert_called_once()
        call_kwargs = mock_notif_svc.create.call_args.kwargs
        assert call_kwargs["user_key"] == "taake"
        assert "ueberfaellig" in call_kwargs["title"]
        assert "150.00" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_no_notification_when_none_overdue(self):
        """Keine Benachrichtigung wenn keine ueberfaelligen Rechnungen."""
        mock_notif_svc, mock_notif_mod, mock_db_mod = _mock_db_and_notif()

        with patch.dict(
            sys.modules,
            {
                "src.services.database": mock_db_mod,
                "src.services.notification_service": mock_notif_mod,
            },
        ):
            import importlib
            import src.scheduler.jobs.invoice_jobs as mod

            importlib.reload(mod)

            with patch.object(mod.asyncio, "to_thread", AsyncMock(return_value=[])):
                await mod.check_overdue_invoices()

        mock_notif_svc.create.assert_not_called()


class TestWarrantyExpiryJob:
    """Tests für check_warranty_expiry."""

    @pytest.mark.asyncio
    async def test_finds_expiring_warranties(self):
        """Erkennt Garantien die innerhalb von 30 Tagen ablaufen."""
        expiry_date = date.today() + timedelta(days=15)
        expiring_data = [
            {
                "id": 1,
                "product_name": "Waschmaschine",
                "warranty_end": expiry_date.isoformat(),
                "vendor": "Bosch",
                "user_key": "taake",
            }
        ]

        mock_notif_svc, mock_notif_mod, mock_db_mod = _mock_db_and_notif()

        with patch.dict(
            sys.modules,
            {
                "src.services.database": mock_db_mod,
                "src.services.notification_service": mock_notif_mod,
            },
        ):
            import importlib
            import src.scheduler.jobs.inventory_jobs as mod

            importlib.reload(mod)

            with patch.object(mod.asyncio, "to_thread", AsyncMock(return_value=expiring_data)):
                await mod.check_warranty_expiry()

        mock_notif_svc.create.assert_called_once()
        call_kwargs = mock_notif_svc.create.call_args.kwargs
        assert "Waschmaschine" in call_kwargs["title"]
        assert "Bosch" in call_kwargs["message"]
        assert "15 Tage" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_no_notification_when_none_expiring(self):
        """Keine Benachrichtigung wenn keine Garantien ablaufen."""
        mock_notif_svc, mock_notif_mod, mock_db_mod = _mock_db_and_notif()

        with patch.dict(
            sys.modules,
            {
                "src.services.database": mock_db_mod,
                "src.services.notification_service": mock_notif_mod,
            },
        ):
            import importlib
            import src.scheduler.jobs.inventory_jobs as mod

            importlib.reload(mod)

            with patch.object(mod.asyncio, "to_thread", AsyncMock(return_value=[])):
                await mod.check_warranty_expiry()

        mock_notif_svc.create.assert_not_called()
