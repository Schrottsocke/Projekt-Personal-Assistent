"""Integration-Tests fuer das Demo-Seed-Skript.

Prueft, dass seed_demo.py deterministisch und idempotent laeuft
und die erwarteten Daten in der Datenbank anlegt.
"""

import pytest

from src.services.database import (
    BudgetCategory,
    Contract,
    FinanceInvoice,
    HouseholdDocument,
    InvoiceItem,
    InventoryItem,
    ShoppingItem,
    Task,
    Transaction,
    UserProfile,
    get_db,
)
from scripts.seed_demo import cleanup_demo_data, run_seed, seed_users, DEMO_USERS


# ── Helpers ────────────────────────────────────────────────────────────────


def _count(db, model, **filters):
    q = db.query(model)
    for k, v in filters.items():
        q = q.filter(getattr(model, k) == v)
    return q.count()


# ── Tests ──────────────────────────────────────────────────────────────────


class TestSeedDemo:
    """Tests fuer scripts/seed_demo.py."""

    def test_seed_creates_demo_users(self, client):
        """Seed erstellt 3 Demo-User mit korrekten Attributen."""
        run_seed()

        with get_db()() as db:
            for u in DEMO_USERS:
                profile = db.query(UserProfile).filter_by(user_key=u["user_key"]).first()
                assert profile is not None, f"User {u['user_key']} nicht gefunden"
                assert profile.nickname == u["nickname"]
                assert profile.is_onboarded is True

    def test_seed_creates_transactions(self, client):
        """Seed erstellt mindestens 20 Transaktionen."""
        run_seed()

        with get_db()() as db:
            profiles = db.query(UserProfile).filter(
                UserProfile.user_key.in_(["demo_max", "demo_lisa"])
            ).all()
            user_ids = [p.id for p in profiles]
            count = db.query(Transaction).filter(Transaction.user_id.in_(user_ids)).count()
            assert count >= 20, f"Erwartet >= 20 Transaktionen, gefunden: {count}"

    def test_seed_creates_contracts(self, client):
        """Seed erstellt genau 2 aktive Vertraege."""
        run_seed()

        with get_db()() as db:
            profile = db.query(UserProfile).filter_by(user_key="demo_max").first()
            count = _count(db, Contract, user_id=profile.id, status="active")
            assert count == 2

    def test_seed_creates_invoices(self, client):
        """Seed erstellt 4 Rechnungen mit Positionen."""
        run_seed()

        with get_db()() as db:
            profile = db.query(UserProfile).filter_by(user_key="demo_max").first()
            invoices = db.query(FinanceInvoice).filter_by(user_id=profile.id).all()
            assert len(invoices) == 4

            # Jede Rechnung hat mindestens eine Position
            for inv in invoices:
                items = db.query(InvoiceItem).filter_by(invoice_id=inv.id).all()
                assert len(items) >= 1, f"Rechnung {inv.invoice_number} hat keine Positionen"

    def test_seed_creates_budgets(self, client):
        """Seed erstellt Budget-Kategorien."""
        run_seed()

        with get_db()() as db:
            profile = db.query(UserProfile).filter_by(user_key="demo_max").first()
            count = _count(db, BudgetCategory, user_id=profile.id)
            assert count >= 4

    def test_seed_creates_documents(self, client):
        """Seed erstellt 4 Dokumente mit OCR-Metadaten."""
        run_seed()

        with get_db()() as db:
            profile = db.query(UserProfile).filter_by(user_key="demo_max").first()
            docs = db.query(HouseholdDocument).filter_by(user_id=profile.id).all()
            assert len(docs) == 4

            for doc in docs:
                assert doc.ocr_text is not None and len(doc.ocr_text) > 10

    def test_seed_creates_inventory(self, client):
        """Seed erstellt 8-15 Inventar-Gegenstaende ueber mehrere Raeume."""
        run_seed()

        with get_db()() as db:
            profile = db.query(UserProfile).filter_by(user_key="demo_max").first()
            items = db.query(InventoryItem).filter_by(user_id=profile.id).all()
            assert 8 <= len(items) <= 15, f"Erwartet 8-15 Items, gefunden: {len(items)}"

            rooms = {i.room for i in items}
            assert len(rooms) >= 3, f"Erwartet >= 3 Raeume, gefunden: {rooms}"

    def test_seed_creates_tasks(self, client):
        """Seed erstellt offene und erledigte Aufgaben."""
        run_seed()

        with get_db()() as db:
            open_tasks = _count(db, Task, user_key="demo_max", status="open")
            done_tasks = _count(db, Task, user_key="demo_max", status="done")
            assert open_tasks >= 3, f"Erwartet >= 3 offene Aufgaben, gefunden: {open_tasks}"
            assert done_tasks >= 1, f"Erwartet >= 1 erledigte Aufgabe, gefunden: {done_tasks}"

    def test_seed_creates_shopping_list(self, client):
        """Seed erstellt eine Einkaufsliste mit abgehakten und offenen Eintraegen."""
        run_seed()

        with get_db()() as db:
            total = _count(db, ShoppingItem, user_key="demo_max")
            checked = _count(db, ShoppingItem, user_key="demo_max", checked=True)
            assert total >= 8
            assert checked >= 1

    def test_seed_is_idempotent(self, client):
        """Zweimaliges Ausfuehren erzeugt keine doppelten Daten."""
        run_seed()
        run_seed()

        with get_db()() as db:
            user_count = db.query(UserProfile).filter(
                UserProfile.user_key.in_(["demo_max", "demo_lisa", "demo_finn"])
            ).count()
            assert user_count == 3, f"Erwartet 3 User nach doppeltem Seed, gefunden: {user_count}"

    def test_cleanup_removes_all_demo_data(self, client):
        """cleanup_demo_data entfernt alle Demo-Eintraege."""
        run_seed()

        with get_db()() as db:
            cleanup_demo_data(db)

            for key in ["demo_max", "demo_lisa", "demo_finn"]:
                assert db.query(UserProfile).filter_by(user_key=key).first() is None
                assert _count(db, Task, user_key=key) == 0
                assert _count(db, ShoppingItem, user_key=key) == 0
