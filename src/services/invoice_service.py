"""Invoice Service – CRUD, Nummernlogik, Berechnung."""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class InvoiceService:
    """Rechnungen erstellen, speichern und verwalten (JSON-basiert pro User)."""

    def __init__(self):
        self._data_dir = Path(settings.DATA_DIR) / "invoices"

    async def initialize(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)
        logger.info("InvoiceService initialisiert.")

    # ── CRUD ──

    async def list_invoices(self, user_key: str, status_filter: str = "") -> list[dict]:
        invoices = await self._load(user_key)
        if status_filter:
            invoices = [i for i in invoices if i.get("status") == status_filter]
        # Neueste zuerst
        invoices.sort(key=lambda i: i.get("created_at", ""), reverse=True)
        return invoices

    async def get_invoice(self, user_key: str, invoice_id: str) -> Optional[dict]:
        invoices = await self._load(user_key)
        return next((i for i in invoices if i.get("id") == invoice_id), None)

    async def create_invoice(self, user_key: str, data: dict) -> dict:
        invoices = await self._load(user_key)

        # Validierung: Kleinunternehmer darf keine USt ausweisen
        inv_type = data.get("invoice_type", "kleinunternehmer")
        if inv_type == "kleinunternehmer":
            for item in data.get("items", []):
                if item.get("tax_rate") and item["tax_rate"] > 0:
                    raise ValueError(
                        "Kleinunternehmer-Rechnungen duerfen keine Umsatzsteuer ausweisen."
                    )

        # Regelbesteuerung muss Steuersatz haben
        if inv_type == "regelbesteuerung":
            for item in data.get("items", []):
                if not item.get("tax_rate") or item["tax_rate"] <= 0:
                    raise ValueError(
                        "Regelbesteuerung erfordert einen gueltigen Steuersatz pro Position."
                    )

        now = datetime.now(timezone.utc).isoformat()
        invoice = {
            "id": str(uuid.uuid4()),
            "invoice_number": data.get("invoice_number") or self._next_number(invoices),
            "invoice_type": inv_type,
            "status": data.get("status", "draft"),
            # Absender
            "sender_name": data.get("sender_name", ""),
            "sender_address": data.get("sender_address", ""),
            "sender_tax_id": data.get("sender_tax_id", ""),
            "sender_vat_id": data.get("sender_vat_id", ""),
            "sender_bank": data.get("sender_bank", ""),
            # Empfaenger
            "recipient_name": data.get("recipient_name", ""),
            "recipient_address": data.get("recipient_address", ""),
            # Daten
            "invoice_date": data.get("invoice_date", now[:10]),
            "delivery_date": data.get("delivery_date", ""),
            "delivery_period": data.get("delivery_period", ""),
            "payment_terms": data.get("payment_terms", "14 Tage netto"),
            # Positionen
            "items": data.get("items", []),
            # Berechnete Summen
            "subtotal": 0.0,
            "tax_total": 0.0,
            "total": 0.0,
            # Hinweis (fuer Kleinunternehmer automatisch)
            "notes": data.get("notes", ""),
            "created_at": now,
            "updated_at": now,
        }

        # Summen berechnen
        self._calculate_totals(invoice)

        invoices.append(invoice)
        await self._save(user_key, invoices)
        return invoice

    async def update_invoice(self, user_key: str, invoice_id: str, data: dict) -> Optional[dict]:
        invoices = await self._load(user_key)
        invoice = next((i for i in invoices if i.get("id") == invoice_id), None)
        if not invoice:
            return None

        # Typ-Validierung bei Update
        inv_type = data.get("invoice_type", invoice.get("invoice_type", "kleinunternehmer"))
        items = data.get("items", invoice.get("items", []))

        if inv_type == "kleinunternehmer":
            for item in items:
                if item.get("tax_rate") and item["tax_rate"] > 0:
                    raise ValueError(
                        "Kleinunternehmer-Rechnungen duerfen keine Umsatzsteuer ausweisen."
                    )
        if inv_type == "regelbesteuerung":
            for item in items:
                if not item.get("tax_rate") or item["tax_rate"] <= 0:
                    raise ValueError(
                        "Regelbesteuerung erfordert einen gueltigen Steuersatz pro Position."
                    )

        # Felder aktualisieren
        updatable = [
            "invoice_type", "status", "sender_name", "sender_address",
            "sender_tax_id", "sender_vat_id", "sender_bank",
            "recipient_name", "recipient_address",
            "invoice_date", "delivery_date", "delivery_period",
            "payment_terms", "items", "notes", "invoice_number",
        ]
        for key in updatable:
            if key in data:
                invoice[key] = data[key]

        invoice["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._calculate_totals(invoice)

        await self._save(user_key, invoices)
        return invoice

    async def delete_invoice(self, user_key: str, invoice_id: str) -> bool:
        invoices = await self._load(user_key)
        before = len(invoices)
        invoices = [i for i in invoices if i.get("id") != invoice_id]
        if len(invoices) < before:
            await self._save(user_key, invoices)
            return True
        return False

    # ── Berechnung ──

    def _calculate_totals(self, invoice: dict):
        """Berechnet subtotal, tax_total, total basierend auf Positionen und Typ."""
        inv_type = invoice.get("invoice_type", "kleinunternehmer")
        subtotal = 0.0
        tax_total = 0.0

        for item in invoice.get("items", []):
            qty = float(item.get("quantity", 1))
            price = float(item.get("unit_price", 0))
            item_net = round(qty * price, 2)
            item["net_total"] = item_net
            subtotal += item_net

            if inv_type == "regelbesteuerung":
                rate = float(item.get("tax_rate", 19))
                item_tax = round(item_net * rate / 100, 2)
                item["tax_amount"] = item_tax
                tax_total += item_tax
            else:
                item["tax_rate"] = 0
                item["tax_amount"] = 0.0

        invoice["subtotal"] = round(subtotal, 2)
        invoice["tax_total"] = round(tax_total, 2)
        invoice["total"] = round(subtotal + tax_total, 2)

    # ── Rechnungsnummer ──

    def _next_number(self, invoices: list[dict]) -> str:
        """Erzeugt fortlaufende Rechnungsnummer: RE-JJJJ-NNNN."""
        year = datetime.now().year
        prefix = f"RE-{year}-"
        max_num = 0
        for inv in invoices:
            num_str = inv.get("invoice_number", "")
            if num_str.startswith(prefix):
                try:
                    n = int(num_str[len(prefix):])
                    max_num = max(max_num, n)
                except ValueError:
                    pass
        return f"{prefix}{max_num + 1:04d}"

    # ── Persistenz (JSON) ──

    async def _load(self, user_key: str) -> list[dict]:
        path = self._data_dir / f"{user_key}.json"
        if path.exists():
            return json.loads(path.read_text())
        return []

    async def _save(self, user_key: str, invoices: list[dict]):
        path = self._data_dir / f"{user_key}.json"
        path.write_text(json.dumps(invoices, ensure_ascii=False, indent=2))
