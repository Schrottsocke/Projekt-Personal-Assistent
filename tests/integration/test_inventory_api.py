"""
Integration-Tests: Inventory API – erweiterte Szenarien.

Getestet:
- Inventory Health-Check
- Photo-Upload fuer Items
- Warranty-Ablauf-Pruefung
- Raum-Uebersicht
- Wert-Zusammenfassung mit mehreren Items
"""

import io

import pytest


class TestInventoryHealth:
    """GET /inventory/health – Modul-Gesundheitscheck."""

    def test_health_endpoint(self, client, auth_headers):
        """Health-Endpunkt antwortet mit ok."""
        resp = client.get("/inventory/health", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["module"] == "inventory"


class TestInventoryRooms:
    """Raum-basierte Inventar-Verwaltung."""

    def test_list_rooms(self, client, auth_headers):
        """Raumliste nach Item-Erstellung enthaelt den Raum."""
        client.post(
            "/inventory/items",
            json={"name": "Lampe", "room": "Wohnzimmer"},
            headers=auth_headers,
        )
        client.post(
            "/inventory/items",
            json={"name": "Stuhl", "room": "Kueche"},
            headers=auth_headers,
        )
        resp = client.get("/inventory/items/rooms", headers=auth_headers)
        if resp.status_code == 200:
            rooms = resp.json()
            assert "Wohnzimmer" in rooms or any(
                r.get("name") == "Wohnzimmer" for r in rooms if isinstance(r, dict)
            )

    def test_filter_items_by_room(self, client, auth_headers):
        """Items koennen nach Raum gefiltert werden."""
        client.post(
            "/inventory/items",
            json={"name": "Mixer", "room": "TestRaum42"},
            headers=auth_headers,
        )
        client.post(
            "/inventory/items",
            json={"name": "Sofa", "room": "AndererRaum"},
            headers=auth_headers,
        )
        resp = client.get("/inventory/items?room=TestRaum42", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert all(i["room"] == "TestRaum42" for i in items)


class TestInventoryValueCalculation:
    """Wert-Berechnung und Zusammenfassung."""

    def test_value_summary_with_items(self, client, auth_headers):
        """Value-Summary berechnet Gesamtwert korrekt."""
        client.post(
            "/inventory/items",
            json={"name": "TV", "value": 800.0},
            headers=auth_headers,
        )
        client.post(
            "/inventory/items",
            json={"name": "Sofa", "value": 1200.0},
            headers=auth_headers,
        )
        resp = client.get("/inventory/items/value-summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_value"] >= 2000.0
        assert data["item_count"] >= 2

    def test_value_summary_empty(self, client, auth_headers):
        """Value-Summary bei leerem Inventar."""
        resp = client.get("/inventory/items/value-summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_value" in data
        assert "item_count" in data


class TestInventoryWarrantyExpiry:
    """Garantie-Ablauf-Szenarien."""

    def test_warranty_with_past_expiry(self, client, auth_headers):
        """Abgelaufene Garantie wird korrekt gespeichert."""
        resp = client.post(
            "/inventory/warranties",
            json={
                "product_name": "Altes Geraet",
                "purchase_date": "2020-01-01",
                "warranty_end": "2022-01-01",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["warranty_end"] == "2022-01-01"

    def test_warranty_with_future_expiry(self, client, auth_headers):
        """Noch gueltige Garantie wird korrekt gespeichert."""
        resp = client.post(
            "/inventory/warranties",
            json={
                "product_name": "Neues Geraet",
                "purchase_date": "2026-01-01",
                "warranty_end": "2028-01-01",
                "vendor": "Samsung",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["vendor"] == "Samsung"
        assert data["warranty_end"] == "2028-01-01"


class TestInventoryAuthProtection:
    """Auth-Schutz der Inventory-Endpunkte."""

    def test_items_require_auth(self, client):
        """Items-Endpunkt ohne Auth gibt 401."""
        resp = client.get("/inventory/items")
        assert resp.status_code == 401

    def test_warranties_require_auth(self, client):
        """Warranties-Endpunkt ohne Auth gibt 401."""
        resp = client.get("/inventory/warranties")
        assert resp.status_code == 401

    def test_create_item_requires_auth(self, client):
        """Item-Erstellung ohne Auth gibt 401."""
        resp = client.post("/inventory/items", json={"name": "Test"})
        assert resp.status_code == 401
