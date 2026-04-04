"""Integration-Tests: Inventory CRUD (Items, Warranties, Documents)."""


class TestInventoryItems:
    def test_create_item(self, client, auth_headers):
        resp = client.post(
            "/inventory/items",
            json={
                "name": "MacBook Pro",
                "description": "Laptop 2024",
                "room": "Buero",
                "value": 2499.0,
                "purchase_date": "2024-06-15",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "MacBook Pro"
        assert data["room"] == "Buero"
        assert data["value"] == 2499.0

    def test_list_items(self, client, auth_headers):
        client.post(
            "/inventory/items",
            json={"name": "Item A", "room": "Kueche"},
            headers=auth_headers,
        )
        client.post(
            "/inventory/items",
            json={"name": "Item B", "room": "Bad"},
            headers=auth_headers,
        )
        resp = client.get("/inventory/items", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_filter_by_room(self, client, auth_headers):
        client.post(
            "/inventory/items",
            json={"name": "Kueche Item", "room": "UniqueRoom"},
            headers=auth_headers,
        )
        resp = client.get("/inventory/items?room=UniqueRoom", headers=auth_headers)
        assert resp.status_code == 200
        assert all(i["room"] == "UniqueRoom" for i in resp.json())

    def test_update_item(self, client, auth_headers):
        create = client.post(
            "/inventory/items",
            json={"name": "Old Name"},
            headers=auth_headers,
        )
        iid = create.json()["id"]
        resp = client.patch(
            f"/inventory/items/{iid}",
            json={"name": "New Name", "room": "Wohnzimmer"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_delete_item(self, client, auth_headers):
        create = client.post(
            "/inventory/items",
            json={"name": "ToDelete"},
            headers=auth_headers,
        )
        iid = create.json()["id"]
        resp = client.delete(f"/inventory/items/{iid}", headers=auth_headers)
        assert resp.status_code == 204

    def test_value_summary(self, client, auth_headers):
        client.post(
            "/inventory/items",
            json={"name": "Expensive", "value": 1000.0},
            headers=auth_headers,
        )
        resp = client.get("/inventory/items/value-summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_value" in data
        assert "item_count" in data

    def test_user_isolation(self, client, auth_headers, auth_headers_nina):
        client.post(
            "/inventory/items",
            json={"name": "Private Item"},
            headers=auth_headers,
        )
        resp = client.get("/inventory/items", headers=auth_headers_nina)
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()]
        assert "Private Item" not in names


class TestWarranties:
    def test_create_warranty(self, client, auth_headers):
        resp = client.post(
            "/inventory/warranties",
            json={
                "product_name": "Waschmaschine",
                "purchase_date": "2025-01-15",
                "warranty_end": "2027-01-15",
                "vendor": "Bosch",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["product_name"] == "Waschmaschine"

    def test_list_warranties(self, client, auth_headers):
        client.post(
            "/inventory/warranties",
            json={"product_name": "W1", "warranty_end": "2027-06-01"},
            headers=auth_headers,
        )
        resp = client.get("/inventory/warranties", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_warranty(self, client, auth_headers):
        create = client.post(
            "/inventory/warranties",
            json={"product_name": "Old Product"},
            headers=auth_headers,
        )
        wid = create.json()["id"]
        resp = client.patch(
            f"/inventory/warranties/{wid}",
            json={"product_name": "Updated Product"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["product_name"] == "Updated Product"

    def test_delete_warranty(self, client, auth_headers):
        create = client.post(
            "/inventory/warranties",
            json={"product_name": "ToDelete"},
            headers=auth_headers,
        )
        wid = create.json()["id"]
        resp = client.delete(f"/inventory/warranties/{wid}", headers=auth_headers)
        assert resp.status_code == 204


class TestWidgetSummary:
    def test_inventory_widget_summary(self, client, auth_headers):
        resp = client.get("/inventory/widget-summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "expiring_warranties_count" in data
        assert "unprocessed_documents_count" in data
