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
    Transaction,
    Budget,
    Contract,
    FinanceInvoice,
    InvoiceItem,
    HouseholdDocument,
    BudgetCategory,
    HouseholdWorkspace,
    WorkspaceMember,
    Routine,
    RoutineCompletion,
    InventoryItem,
    Warranty,
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


# --- Helpers ---

def _create_user(session, key="taake"):
    """Create and return a UserProfile for FK tests."""
    user = UserProfile(user_key=key)
    session.add(user)
    session.commit()
    return user


# --- Finance Models ---

class TestTransaction:
    def test_create_transaction(self, session):
        user = _create_user(session)
        tx = Transaction(user_id=user.id, date=datetime.utcnow(), amount=-42.50, category="Lebensmittel")
        session.add(tx)
        session.commit()
        result = session.query(Transaction).first()
        assert result.amount == -42.50
        assert result.source == "manual"
        assert result.currency == "EUR"

    def test_transaction_with_contract_fk(self, session):
        user = _create_user(session)
        from datetime import date
        contract = Contract(user_id=user.id, name="Netflix", amount=12.99, start_date=date(2026, 1, 1))
        session.add(contract)
        session.commit()
        tx = Transaction(user_id=user.id, date=datetime.utcnow(), amount=-12.99, contract_id=contract.id)
        session.add(tx)
        session.commit()
        assert session.query(Transaction).first().contract_id == contract.id


class TestBudget:
    def test_create_budget(self, session):
        user = _create_user(session)
        b = Budget(user_id=user.id, category="Essen", monthly_limit=400.0)
        session.add(b)
        session.commit()
        result = session.query(Budget).first()
        assert result.category == "Essen"
        assert result.monthly_limit == 400.0


class TestBudgetCategory:
    def test_create_budget_category(self, session):
        user = _create_user(session)
        bc = BudgetCategory(user_id=user.id, name="Freizeit", monthly_limit=200.0, color="#FF5733", icon="gamepad")
        session.add(bc)
        session.commit()
        result = session.query(BudgetCategory).first()
        assert result.name == "Freizeit"
        assert result.color == "#FF5733"
        assert result.icon == "gamepad"


class TestContract:
    def test_create_contract(self, session):
        user = _create_user(session)
        from datetime import date
        c = Contract(
            user_id=user.id, name="Spotify", provider="Spotify AB",
            category="Streaming", amount=9.99, start_date=date(2026, 1, 1),
            cancellation_days=30, notes="Familienabo",
        )
        session.add(c)
        session.commit()
        result = session.query(Contract).first()
        assert result.name == "Spotify"
        assert result.provider == "Spotify AB"
        assert result.status == "active"
        assert result.cancellation_days == 30

    def test_contract_cancel(self, session):
        user = _create_user(session)
        from datetime import date
        c = Contract(user_id=user.id, name="Test", amount=5.0, start_date=date(2026, 1, 1))
        session.add(c)
        session.commit()
        c.status = "cancelled"
        c.end_date = date(2026, 6, 30)
        session.commit()
        result = session.query(Contract).first()
        assert result.status == "cancelled"
        assert result.end_date == date(2026, 6, 30)


class TestFinanceInvoice:
    def test_create_invoice(self, session):
        user = _create_user(session)
        from datetime import date
        inv = FinanceInvoice(
            user_id=user.id, recipient="Max Mustermann",
            invoice_number="RE-2026-001", total=119.0,
            tax_rate=19.0, due_date=date(2026, 5, 1),
        )
        session.add(inv)
        session.commit()
        result = session.query(FinanceInvoice).first()
        assert result.invoice_number == "RE-2026-001"
        assert result.tax_rate == 19.0
        assert result.status == "open"

    def test_invoice_pay(self, session):
        user = _create_user(session)
        from datetime import date
        inv = FinanceInvoice(user_id=user.id, recipient="Test", total=50.0, due_date=date(2026, 5, 1))
        session.add(inv)
        session.commit()
        inv.status = "paid"
        inv.payment_date = date(2026, 4, 20)
        session.commit()
        assert session.query(FinanceInvoice).first().payment_date == date(2026, 4, 20)


class TestInvoiceItem:
    def test_create_invoice_item(self, session):
        user = _create_user(session)
        from datetime import date
        inv = FinanceInvoice(user_id=user.id, recipient="Kunde", total=238.0, due_date=date(2026, 5, 1))
        session.add(inv)
        session.commit()
        item = InvoiceItem(invoice_id=inv.id, description="Beratung", quantity=2, unit_price=100.0, total=200.0)
        session.add(item)
        session.commit()
        result = session.query(InvoiceItem).first()
        assert result.description == "Beratung"
        assert result.quantity == 2
        assert result.total == 200.0


# --- Inventory Models ---

class TestInventoryItem:
    def test_create_inventory_item(self, session):
        user = _create_user(session)
        item = InventoryItem(
            user_id=user.id, name="Staubsauger", room="Abstellkammer",
            box_label="K3", serial_number="SN-12345", value=299.99,
        )
        session.add(item)
        session.commit()
        result = session.query(InventoryItem).first()
        assert result.name == "Staubsauger"
        assert result.box_label == "K3"
        assert result.serial_number == "SN-12345"


class TestWarranty:
    def test_create_warranty(self, session):
        user = _create_user(session)
        from datetime import date
        item = InventoryItem(user_id=user.id, name="Laptop")
        session.add(item)
        session.commit()
        w = Warranty(
            user_id=user.id, product_name="Laptop",
            purchase_date=date(2026, 1, 15), warranty_end=date(2028, 1, 15),
            vendor="Lenovo", inventory_item_id=item.id,
        )
        session.add(w)
        session.commit()
        result = session.query(Warranty).first()
        assert result.vendor == "Lenovo"
        assert result.inventory_item_id == item.id


class TestHouseholdDocument:
    def test_create_document(self, session):
        user = _create_user(session)
        doc = HouseholdDocument(
            user_id=user.id, title="Stromrechnung 2026",
            category="invoice", issuer="Stadtwerke", amount=85.50,
        )
        session.add(doc)
        session.commit()
        result = session.query(HouseholdDocument).first()
        assert result.title == "Stromrechnung 2026"
        assert result.category == "invoice"
        assert result.amount == 85.50

    def test_document_linked_to_inventory(self, session):
        user = _create_user(session)
        item = InventoryItem(user_id=user.id, name="Waschmaschine")
        session.add(item)
        session.commit()
        doc = HouseholdDocument(
            user_id=user.id, title="Kaufbeleg Waschmaschine",
            category="receipt", linked_inventory_item_id=item.id,
        )
        session.add(doc)
        session.commit()
        assert session.query(HouseholdDocument).first().linked_inventory_item_id == item.id


# --- Family Models ---

class TestHouseholdWorkspace:
    def test_create_workspace(self, session):
        user = _create_user(session)
        ws = HouseholdWorkspace(name="Familie Mueller", owner_id=user.id)
        session.add(ws)
        session.commit()
        result = session.query(HouseholdWorkspace).first()
        assert result.name == "Familie Mueller"

    def test_add_member(self, session):
        owner = _create_user(session, "owner")
        member = _create_user(session, "member")
        ws = HouseholdWorkspace(name="Test-WS", owner_id=owner.id)
        session.add(ws)
        session.commit()
        wm = WorkspaceMember(workspace_id=ws.id, user_id=member.id, role="editor")
        session.add(wm)
        session.commit()
        assert session.query(WorkspaceMember).first().role == "editor"


class TestRoutine:
    def test_create_routine(self, session):
        user = _create_user(session)
        ws = HouseholdWorkspace(name="Haushalt", owner_id=user.id)
        session.add(ws)
        session.commit()
        r = Routine(workspace_id=ws.id, name="Staubsaugen", interval="weekly")
        session.add(r)
        session.commit()
        assert session.query(Routine).first().name == "Staubsaugen"

    def test_complete_routine(self, session):
        user = _create_user(session)
        ws = HouseholdWorkspace(name="H", owner_id=user.id)
        session.add(ws)
        session.commit()
        r = Routine(workspace_id=ws.id, name="Muell")
        session.add(r)
        session.commit()
        rc = RoutineCompletion(routine_id=r.id, completed_by=user.id)
        session.add(rc)
        session.commit()
        assert session.query(RoutineCompletion).first().completed_by == user.id
