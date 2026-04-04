"""Integration-Tests: GDPR/DSGVO (Data Export, Account Deletion, Consents)."""


class TestDataExport:
    def test_export_contains_all_tables(self, client, auth_headers):
        """Data export should return data from all product line tables."""
        # Create test data across tables
        client.post(
            "/finance/transactions",
            json={"date": "2026-01-15T10:00:00", "amount": -50.0, "category": "Test"},
            headers=auth_headers,
        )
        client.post(
            "/finance/budgets",
            json={"category": "GDPR", "monthly_limit": 100.0},
            headers=auth_headers,
        )
        client.post(
            "/inventory/items",
            json={"name": "GDPR Item"},
            headers=auth_headers,
        )
        client.post(
            "/inventory/warranties",
            json={"product_name": "GDPR Warranty"},
            headers=auth_headers,
        )
        client.post(
            "/notifications-v2/events",
            json={"type": "test", "title": "GDPR Event"},
            headers=auth_headers,
        )

        resp = client.get("/gdpr/data-export", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["transactions"]) >= 1
        assert len(data["budgets"]) >= 1
        assert len(data["inventory_items"]) >= 1
        assert len(data["warranties"]) >= 1
        assert len(data["notification_events"]) >= 1

    def test_export_empty_for_new_user(self, client, auth_headers_nina):
        """Fresh user should have empty data export."""
        resp = client.get("/gdpr/data-export", headers=auth_headers_nina)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["transactions"]) == 0
        assert len(data["budgets"]) == 0


class TestAccountDeletion:
    def test_delete_removes_all_data(self, client, auth_headers, auth_headers_nina):
        """Account deletion should remove all user data."""
        # Create data for nina
        client.post(
            "/finance/transactions",
            json={"date": "2026-01-15T10:00:00", "amount": -10.0},
            headers=auth_headers_nina,
        )
        client.post(
            "/inventory/items",
            json={"name": "Nina Item"},
            headers=auth_headers_nina,
        )
        client.post(
            "/finance/budgets",
            json={"category": "Nina Budget", "monthly_limit": 50.0},
            headers=auth_headers_nina,
        )

        # Delete nina's account
        resp = client.delete("/gdpr/account", headers=auth_headers_nina)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True
        counts = resp.json()["counts"]
        assert counts["transactions"] >= 1
        assert counts["inventory_items"] >= 1


class TestSelectiveDeletion:
    def test_delete_finance_only(self, client, auth_headers):
        """Deleting finance data should not affect inventory."""
        client.post(
            "/finance/transactions",
            json={"date": "2026-01-15T10:00:00", "amount": -10.0},
            headers=auth_headers,
        )
        client.post(
            "/inventory/items",
            json={"name": "Preserved Item"},
            headers=auth_headers,
        )

        resp = client.delete("/gdpr/data/finance", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["category"] == "finance"

        # Inventory should still exist
        items = client.get("/inventory/items", headers=auth_headers)
        assert items.status_code == 200
        names = [i["name"] for i in items.json()]
        assert "Preserved Item" in names

    def test_delete_notifications(self, client, auth_headers):
        client.post(
            "/notifications-v2/events",
            json={"type": "test", "title": "To Delete"},
            headers=auth_headers,
        )
        resp = client.delete("/gdpr/data/notifications", headers=auth_headers)
        assert resp.status_code == 200


class TestConsents:
    def test_grant_consent(self, client, auth_headers):
        resp = client.post("/gdpr/consents/finance", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["consented"] is True

    def test_list_consents(self, client, auth_headers):
        client.post("/gdpr/consents/finance", headers=auth_headers)
        resp = client.get("/gdpr/consents", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["consents"].get("finance") is True

    def test_revoke_consent(self, client, auth_headers):
        client.post("/gdpr/consents/finance", headers=auth_headers)
        resp = client.delete("/gdpr/consents/finance", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["consented"] is False

        # Verify removal
        consents = client.get("/gdpr/consents", headers=auth_headers)
        assert "finance" not in consents.json()["consents"]
