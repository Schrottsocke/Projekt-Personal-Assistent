"""Tests für src/services/database.py – Models, Session, CRUD."""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.services.database import (
    Base,
    UserProfile,
    Note,
    Reminder,
    Task,
    MemoryFact,
    ConversationHistory,
    ShoppingItem,
    Proposal,
)


@pytest.fixture
def session():
    """Frische In-Memory-DB pro Test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()
    engine.dispose()


class TestUserProfile:
    def test_create_user_profile(self, session):
        profile = UserProfile(user_key="taake", is_onboarded=False)
        session.add(profile)
        session.commit()
        result = session.query(UserProfile).filter_by(user_key="taake").first()
        assert result is not None
        assert result.user_key == "taake"
        assert result.is_onboarded is False

    def test_user_profile_defaults(self, session):
        profile = UserProfile(user_key="nina")
        session.add(profile)
        session.commit()
        result = session.query(UserProfile).first()
        assert result.communication_style == "casual"
        assert result.auto_approve_types == "timer_create"
        assert result.tts_enabled is False

    def test_user_key_unique_constraint(self, session):
        session.add(UserProfile(user_key="taake"))
        session.commit()
        session.add(UserProfile(user_key="taake"))
        with pytest.raises(Exception):
            session.commit()


class TestNote:
    def test_create_note(self, session):
        note = Note(user_key="taake", content="Testnotiz")
        session.add(note)
        session.commit()
        result = session.query(Note).first()
        assert result.content == "Testnotiz"
        assert result.is_shared is False

    def test_note_shared_flag(self, session):
        note = Note(user_key="taake", content="Geteilt", is_shared=True)
        session.add(note)
        session.commit()
        assert session.query(Note).first().is_shared is True


class TestTask:
    def test_create_task(self, session):
        task = Task(user_key="taake", title="Test-Aufgabe")
        session.add(task)
        session.commit()
        result = session.query(Task).first()
        assert result.title == "Test-Aufgabe"
        assert result.status == "open"
        assert result.priority == "medium"

    def test_task_status_update(self, session):
        task = Task(user_key="taake", title="Aufgabe")
        session.add(task)
        session.commit()
        task.status = "done"
        session.commit()
        assert session.query(Task).first().status == "done"

    def test_task_with_priority(self, session):
        task = Task(user_key="nina", title="Dringend", priority="high")
        session.add(task)
        session.commit()
        assert session.query(Task).first().priority == "high"

    def test_task_with_due_date(self, session):
        due = datetime(2026, 12, 31, 23, 59)
        task = Task(user_key="taake", title="Deadline", due_date=due)
        session.add(task)
        session.commit()
        assert session.query(Task).first().due_date == due


class TestReminder:
    def test_create_reminder(self, session):
        remind_at = datetime(2026, 4, 1, 10, 0)
        reminder = Reminder(user_key="taake", chat_id="123", content="Termin", remind_at=remind_at)
        session.add(reminder)
        session.commit()
        result = session.query(Reminder).first()
        assert result.content == "Termin"
        assert result.is_sent is False


class TestMemoryFact:
    def test_create_fact(self, session):
        fact = MemoryFact(user_key="taake", content="Mag Kaffee")
        session.add(fact)
        session.commit()
        result = session.query(MemoryFact).first()
        assert result.content == "Mag Kaffee"
        assert result.confirmation_count == 1

    def test_increment_confirmation(self, session):
        fact = MemoryFact(user_key="taake", content="Fakt")
        session.add(fact)
        session.commit()
        fact.confirmation_count += 1
        session.commit()
        assert session.query(MemoryFact).first().confirmation_count == 2


class TestConversationHistory:
    def test_create_entry(self, session):
        entry = ConversationHistory(user_key="taake", role="user", content="Hallo")
        session.add(entry)
        session.commit()
        result = session.query(ConversationHistory).first()
        assert result.role == "user"
        assert result.content == "Hallo"

    def test_multiple_entries(self, session):
        session.add(ConversationHistory(user_key="taake", role="user", content="Hi"))
        session.add(ConversationHistory(user_key="taake", role="assistant", content="Hallo!"))
        session.commit()
        count = session.query(ConversationHistory).count()
        assert count == 2


class TestShoppingItem:
    def test_create_item(self, session):
        item = ShoppingItem(user_key="nina", name="Milch", quantity="1", unit="l")
        session.add(item)
        session.commit()
        result = session.query(ShoppingItem).first()
        assert result.name == "Milch"
        assert result.checked is False

    def test_check_item(self, session):
        item = ShoppingItem(user_key="nina", name="Brot")
        session.add(item)
        session.commit()
        item.checked = True
        session.commit()
        assert session.query(ShoppingItem).first().checked is True


class TestProposal:
    def test_create_proposal(self, session):
        prop = Proposal(
            proposal_type="calendar_create",
            title="Termin anlegen",
            payload_json='{"date": "2026-04-01"}',
            user_key="taake",
            created_by="ai",
        )
        session.add(prop)
        session.commit()
        result = session.query(Proposal).first()
        assert result.status == "pending"
        assert result.proposal_type == "calendar_create"

    def test_approve_proposal(self, session):
        prop = Proposal(
            proposal_type="reminder_create",
            title="Erinnerung",
            payload_json="{}",
            user_key="nina",
            created_by="bot_nina",
        )
        session.add(prop)
        session.commit()
        prop.status = "approved"
        prop.decided_at = datetime.utcnow()
        session.commit()
        assert session.query(Proposal).first().status == "approved"
