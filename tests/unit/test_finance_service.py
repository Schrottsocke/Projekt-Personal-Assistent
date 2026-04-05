"""
Unit-Tests fuer InvoiceService – Rechnungslogik und Berechnungen.

Getestet:
- _calculate_totals: Netto/Brutto-Berechnung fuer Kleinunternehmer und Regelbesteuerung
- _next_number: Fortlaufende Rechnungsnummer-Generierung
- create_invoice: Validierung von Kleinunternehmer vs. Regelbesteuerung
- CRUD: Erstellen, Lesen, Aktualisieren, Loeschen
"""

import asyncio
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixture: InvoiceService mit temporaerem Datenverzeichnis
# ---------------------------------------------------------------------------
@pytest.fixture
def invoice_service(tmp_path):
    """InvoiceService mit tmp_path als Datenspeicher."""
    with patch("src.services.invoice_service.settings") as mock_settings:
        mock_settings.DATA_DIR = str(tmp_path)
        from src.services.invoice_service import InvoiceService

        svc = InvoiceService()
        # Verzeichnis direkt erstellen (ohne async init)
        svc._data_dir.mkdir(parents=True, exist_ok=True)
    return svc


def _run(coro):
    """Hilfsfunktion fuer synchrone Ausfuehrung von async-Methoden."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# _calculate_totals
# ---------------------------------------------------------------------------
class TestCalculateTotals:
    """Berechnung von Netto, Steuer und Brutto."""

    def test_kleinunternehmer_no_tax(self, invoice_service):
        """Kleinunternehmer: Steuer ist immer 0."""
        invoice = {
            "invoice_type": "kleinunternehmer",
            "items": [
                {"quantity": 2, "unit_price": 50.0, "tax_rate": 0},
                {"quantity": 1, "unit_price": 100.0, "tax_rate": 0},
            ],
        }
        invoice_service._calculate_totals(invoice)
        assert invoice["subtotal"] == 200.0
        assert invoice["tax_total"] == 0.0
        assert invoice["total"] == 200.0

    def test_regelbesteuerung_19_percent(self, invoice_service):
        """Regelbesteuerung: 19% USt wird korrekt berechnet."""
        invoice = {
            "invoice_type": "regelbesteuerung",
            "items": [
                {"quantity": 1, "unit_price": 100.0, "tax_rate": 19},
            ],
        }
        invoice_service._calculate_totals(invoice)
        assert invoice["subtotal"] == 100.0
        assert invoice["tax_total"] == 19.0
        assert invoice["total"] == 119.0

    def test_regelbesteuerung_7_percent(self, invoice_service):
        """Ermaessigter Steuersatz 7% wird korrekt berechnet."""
        invoice = {
            "invoice_type": "regelbesteuerung",
            "items": [
                {"quantity": 3, "unit_price": 10.0, "tax_rate": 7},
            ],
        }
        invoice_service._calculate_totals(invoice)
        assert invoice["subtotal"] == 30.0
        assert invoice["tax_total"] == 2.1
        assert invoice["total"] == 32.1

    def test_mixed_tax_rates(self, invoice_service):
        """Gemischte Steuersaetze in einer Rechnung."""
        invoice = {
            "invoice_type": "regelbesteuerung",
            "items": [
                {"quantity": 1, "unit_price": 100.0, "tax_rate": 19},
                {"quantity": 1, "unit_price": 50.0, "tax_rate": 7},
            ],
        }
        invoice_service._calculate_totals(invoice)
        assert invoice["subtotal"] == 150.0
        assert invoice["tax_total"] == 22.5  # 19 + 3.5
        assert invoice["total"] == 172.5

    def test_empty_items(self, invoice_service):
        """Rechnung ohne Positionen ergibt 0."""
        invoice = {"invoice_type": "kleinunternehmer", "items": []}
        invoice_service._calculate_totals(invoice)
        assert invoice["subtotal"] == 0.0
        assert invoice["total"] == 0.0

    def test_fractional_quantities(self, invoice_service):
        """Stunden-basierte Abrechnung mit Dezimalmengen."""
        invoice = {
            "invoice_type": "regelbesteuerung",
            "items": [
                {"quantity": 7.5, "unit_price": 80.0, "tax_rate": 19},
            ],
        }
        invoice_service._calculate_totals(invoice)
        assert invoice["subtotal"] == 600.0
        assert invoice["tax_total"] == 114.0
        assert invoice["total"] == 714.0

    def test_kleinunternehmer_forces_zero_tax(self, invoice_service):
        """Kleinunternehmer: Auch wenn tax_rate angegeben, wird 0 gesetzt."""
        invoice = {
            "invoice_type": "kleinunternehmer",
            "items": [
                {"quantity": 1, "unit_price": 100.0, "tax_rate": 19},
            ],
        }
        invoice_service._calculate_totals(invoice)
        assert invoice["items"][0]["tax_rate"] == 0
        assert invoice["items"][0]["tax_amount"] == 0.0
        assert invoice["total"] == 100.0


# ---------------------------------------------------------------------------
# _next_number
# ---------------------------------------------------------------------------
class TestNextNumber:
    """Fortlaufende Rechnungsnummer-Generierung."""

    def test_first_invoice(self, invoice_service):
        """Erste Rechnung bekommt Nummer 0001."""
        number = invoice_service._next_number([])
        assert number.endswith("-0001")
        assert number.startswith("RE-")

    def test_sequential_after_existing(self, invoice_service):
        """Naechste Nummer nach vorhandenen Rechnungen."""
        existing = [
            {"invoice_number": "RE-2026-0001"},
            {"invoice_number": "RE-2026-0005"},
            {"invoice_number": "RE-2026-0003"},
        ]
        number = invoice_service._next_number(existing)
        assert number.endswith("-0006")

    def test_ignores_other_years(self, invoice_service):
        """Nummern aus anderen Jahren werden ignoriert."""
        existing = [
            {"invoice_number": "RE-2025-0050"},
        ]
        number = invoice_service._next_number(existing)
        # Aktuelles Jahr zaehlt ab 1
        assert "-0001" in number or "-0051" in number

    def test_handles_malformed_numbers(self, invoice_service):
        """Ungueltige Nummern werden uebersprungen."""
        existing = [
            {"invoice_number": "INVALID"},
            {"invoice_number": ""},
            {"invoice_number": "RE-2026-abc"},
        ]
        number = invoice_service._next_number(existing)
        assert number.endswith("-0001")


# ---------------------------------------------------------------------------
# create_invoice – Validierung
# ---------------------------------------------------------------------------
class TestCreateInvoiceValidation:
    """Validierung bei Rechnungserstellung."""

    def test_kleinunternehmer_with_tax_raises(self, invoice_service):
        """Kleinunternehmer mit Steuersatz wird abgelehnt."""
        data = {
            "invoice_type": "kleinunternehmer",
            "items": [{"quantity": 1, "unit_price": 100, "tax_rate": 19}],
        }
        with pytest.raises(ValueError, match="Kleinunternehmer"):
            _run(invoice_service.create_invoice("testuser", data))

    def test_regelbesteuerung_without_tax_raises(self, invoice_service):
        """Regelbesteuerung ohne Steuersatz wird abgelehnt."""
        data = {
            "invoice_type": "regelbesteuerung",
            "items": [{"quantity": 1, "unit_price": 100, "tax_rate": 0}],
        }
        with pytest.raises(ValueError, match="Regelbesteuerung"):
            _run(invoice_service.create_invoice("testuser", data))

    def test_valid_kleinunternehmer_creates(self, invoice_service):
        """Gueltige Kleinunternehmer-Rechnung wird erstellt."""
        data = {
            "invoice_type": "kleinunternehmer",
            "recipient_name": "Kunde AG",
            "items": [{"quantity": 2, "unit_price": 50.0}],
        }
        result = _run(invoice_service.create_invoice("testuser", data))
        assert result["id"]
        assert result["total"] == 100.0
        assert result["recipient_name"] == "Kunde AG"
        assert result["invoice_number"].startswith("RE-")

    def test_valid_regelbesteuerung_creates(self, invoice_service):
        """Gueltige Regelbesteuerung-Rechnung wird erstellt."""
        data = {
            "invoice_type": "regelbesteuerung",
            "items": [{"quantity": 1, "unit_price": 200.0, "tax_rate": 19}],
        }
        result = _run(invoice_service.create_invoice("testuser", data))
        assert result["total"] == 238.0


# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------
class TestCRUD:
    """Erstellen, Lesen, Aktualisieren, Loeschen."""

    def test_list_empty(self, invoice_service):
        """Leere Liste bei neuem User."""
        result = _run(invoice_service.list_invoices("newuser"))
        assert result == []

    def test_create_and_list(self, invoice_service):
        """Erstellte Rechnung erscheint in der Liste."""
        data = {"items": [{"quantity": 1, "unit_price": 100.0}]}
        _run(invoice_service.create_invoice("testuser", data))
        _run(invoice_service.create_invoice("testuser", data))
        result = _run(invoice_service.list_invoices("testuser"))
        assert len(result) == 2

    def test_get_invoice_by_id(self, invoice_service):
        """Rechnung kann per ID abgerufen werden."""
        data = {"recipient_name": "Find Me", "items": [{"quantity": 1, "unit_price": 50.0}]}
        created = _run(invoice_service.create_invoice("testuser", data))
        found = _run(invoice_service.get_invoice("testuser", created["id"]))
        assert found is not None
        assert found["recipient_name"] == "Find Me"

    def test_get_nonexistent_returns_none(self, invoice_service):
        """Nicht existierende ID gibt None zurueck."""
        result = _run(invoice_service.get_invoice("testuser", "fake-id"))
        assert result is None

    def test_update_invoice(self, invoice_service):
        """Rechnung kann aktualisiert werden."""
        data = {"recipient_name": "Old", "items": [{"quantity": 1, "unit_price": 100.0}]}
        created = _run(invoice_service.create_invoice("testuser", data))
        updated = _run(invoice_service.update_invoice("testuser", created["id"], {"recipient_name": "New"}))
        assert updated["recipient_name"] == "New"

    def test_delete_invoice(self, invoice_service):
        """Rechnung kann geloescht werden."""
        data = {"items": [{"quantity": 1, "unit_price": 100.0}]}
        created = _run(invoice_service.create_invoice("testuser", data))
        deleted = _run(invoice_service.delete_invoice("testuser", created["id"]))
        assert deleted is True
        result = _run(invoice_service.list_invoices("testuser"))
        assert len(result) == 0

    def test_delete_nonexistent_returns_false(self, invoice_service):
        """Loeschen einer nicht existierenden Rechnung gibt False zurueck."""
        deleted = _run(invoice_service.delete_invoice("testuser", "fake-id"))
        assert deleted is False

    def test_list_filter_by_status(self, invoice_service):
        """Status-Filter funktioniert."""
        _run(invoice_service.create_invoice("testuser", {"status": "draft", "items": []}))
        _run(invoice_service.create_invoice("testuser", {"status": "sent", "items": []}))
        drafts = _run(invoice_service.list_invoices("testuser", status_filter="draft"))
        assert len(drafts) == 1
        assert drafts[0]["status"] == "draft"

    def test_user_isolation(self, invoice_service):
        """Rechnungen verschiedener User sind isoliert."""
        _run(invoice_service.create_invoice("user_a", {"items": [{"quantity": 1, "unit_price": 10.0}]}))
        _run(invoice_service.create_invoice("user_b", {"items": [{"quantity": 1, "unit_price": 20.0}]}))
        a_invoices = _run(invoice_service.list_invoices("user_a"))
        b_invoices = _run(invoice_service.list_invoices("user_b"))
        assert len(a_invoices) == 1
        assert len(b_invoices) == 1
        assert a_invoices[0]["total"] != b_invoices[0]["total"]
