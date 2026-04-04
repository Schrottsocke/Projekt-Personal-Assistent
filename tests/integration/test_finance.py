"""Integration-Tests: Finance CRUD (Transactions, Budgets, Contracts, Invoices)."""

from pathlib import Path


class TestTransactions:
    def test_create_transaction(self, client, auth_headers):
        resp = client.post(
            "/finance/transactions",
            json={
                "date": "2026-01-15T10:00:00",
                "amount": -42.50,
                "currency": "EUR",
                "category": "Lebensmittel",
                "description": "REWE Einkauf",
                "source": "manual",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["amount"] == -42.50
        assert data["category"] == "Lebensmittel"
        assert data["source"] == "manual"

    def test_list_transactions(self, client, auth_headers):
        client.post(
            "/finance/transactions",
            json={"date": "2026-01-15T10:00:00", "amount": -10.0},
            headers=auth_headers,
        )
        client.post(
            "/finance/transactions",
            json={"date": "2026-01-16T10:00:00", "amount": -20.0, "category": "Essen"},
            headers=auth_headers,
        )
        resp = client.get("/finance/transactions", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_filter_by_category(self, client, auth_headers):
        client.post(
            "/finance/transactions",
            json={"date": "2026-01-15T10:00:00", "amount": -5.0, "category": "Unique"},
            headers=auth_headers,
        )
        resp = client.get("/finance/transactions?category=Unique", headers=auth_headers)
        assert resp.status_code == 200
        assert all(t["category"] == "Unique" for t in resp.json())

    def test_delete_transaction(self, client, auth_headers):
        create = client.post(
            "/finance/transactions",
            json={"date": "2026-01-15T10:00:00", "amount": -1.0},
            headers=auth_headers,
        )
        tid = create.json()["id"]
        resp = client.delete(f"/finance/transactions/{tid}", headers=auth_headers)
        assert resp.status_code == 204

    def test_monthly_overview(self, client, auth_headers):
        client.post(
            "/finance/transactions",
            json={"date": "2026-03-10T10:00:00", "amount": -100.0, "category": "Test"},
            headers=auth_headers,
        )
        client.post(
            "/finance/transactions",
            json={"date": "2026-03-15T10:00:00", "amount": 2000.0},
            headers=auth_headers,
        )
        resp = client.get("/finance/transactions/monthly-overview?year=2026&month=3", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2026
        assert data["month"] == 3
        assert data["total_income"] >= 2000.0
        assert data["total_expenses"] >= 100.0

    def test_csv_upload(self, client, auth_headers):
        csv_path = Path(__file__).parent.parent / "fixtures" / "sample_transactions.csv"
        with open(csv_path, "rb") as f:
            resp = client.post(
                "/finance/transactions/csv",
                files={"file": ("test.csv", f, "text/csv")},
                headers=auth_headers,
            )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data) == 10
        assert data[0]["source"] == "csv"

    def test_user_isolation(self, client, auth_headers, auth_headers_nina):
        client.post(
            "/finance/transactions",
            json={"date": "2026-01-15T10:00:00", "amount": -999.0, "category": "Private"},
            headers=auth_headers,
        )
        resp = client.get("/finance/transactions?category=Private", headers=auth_headers_nina)
        assert resp.status_code == 200
        assert len(resp.json()) == 0


class TestBudgets:
    def test_create_budget(self, client, auth_headers):
        resp = client.post(
            "/finance/budgets",
            json={"category": "Lebensmittel", "monthly_limit": 500.0, "alert_threshold": 80.0},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["monthly_limit"] == 500.0

    def test_list_budgets(self, client, auth_headers):
        client.post(
            "/finance/budgets",
            json={"category": "TestCat", "monthly_limit": 100.0},
            headers=auth_headers,
        )
        resp = client.get("/finance/budgets", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_budget_alerts(self, client, auth_headers):
        client.post(
            "/finance/budgets",
            json={"category": "AlertCat", "monthly_limit": 100.0},
            headers=auth_headers,
        )
        resp = client.get("/finance/budgets/alerts", headers=auth_headers)
        assert resp.status_code == 200


class TestContracts:
    def test_create_contract(self, client, auth_headers):
        resp = client.post(
            "/finance/contracts",
            json={
                "name": "Netflix",
                "amount": 15.99,
                "interval": "monthly",
                "start_date": "2026-01-01",
                "status": "active",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Netflix"

    def test_list_contracts(self, client, auth_headers):
        client.post(
            "/finance/contracts",
            json={"name": "Spotify", "amount": 9.99, "interval": "monthly", "start_date": "2026-01-01"},
            headers=auth_headers,
        )
        resp = client.get("/finance/contracts", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_contract(self, client, auth_headers):
        create = client.post(
            "/finance/contracts",
            json={"name": "Old", "amount": 10.0, "interval": "monthly", "start_date": "2026-01-01"},
            headers=auth_headers,
        )
        cid = create.json()["id"]
        resp = client.patch(
            f"/finance/contracts/{cid}",
            json={"name": "Updated", "amount": 20.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"
        assert resp.json()["amount"] == 20.0

    def test_delete_contract(self, client, auth_headers):
        create = client.post(
            "/finance/contracts",
            json={"name": "ToDelete", "amount": 5.0, "interval": "monthly", "start_date": "2026-01-01"},
            headers=auth_headers,
        )
        cid = create.json()["id"]
        resp = client.delete(f"/finance/contracts/{cid}", headers=auth_headers)
        assert resp.status_code == 204

    def test_contract_summary(self, client, auth_headers):
        client.post(
            "/finance/contracts",
            json={"name": "SumTest", "amount": 30.0, "interval": "monthly", "start_date": "2026-01-01"},
            headers=auth_headers,
        )
        resp = client.get("/finance/contracts/summary", headers=auth_headers)
        assert resp.status_code == 200
        assert "total_monthly_cost" in resp.json()


class TestFinanceInvoices:
    def test_create_invoice(self, client, auth_headers):
        resp = client.post(
            "/finance/invoices",
            json={"recipient": "Kunde A", "total": 1200.0, "due_date": "2026-02-01", "status": "open"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["recipient"] == "Kunde A"

    def test_list_invoices(self, client, auth_headers):
        client.post(
            "/finance/invoices",
            json={"recipient": "Test", "total": 100.0, "due_date": "2026-03-01"},
            headers=auth_headers,
        )
        resp = client.get("/finance/invoices", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_overdue_invoices(self, client, auth_headers):
        resp = client.get("/finance/invoices/overdue", headers=auth_headers)
        assert resp.status_code == 200


class TestWidgetSummary:
    def test_finance_widget_summary(self, client, auth_headers):
        resp = client.get("/finance/widget-summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "spending_this_month" in data
        assert "budget_total" in data
        assert "open_invoices_count" in data
