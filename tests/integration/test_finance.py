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
        assert data["imported"] == 10
        assert data["skipped_duplicates"] == 0
        assert data["total_rows"] == 10

    def test_csv_duplicate_detection(self, client, auth_headers):
        """#645: Zweiter CSV-Import erkennt Duplikate."""
        csv_path = Path(__file__).parent.parent / "fixtures" / "sample_transactions.csv"
        # First import
        with open(csv_path, "rb") as f:
            resp1 = client.post(
                "/finance/transactions/csv",
                files={"file": ("test.csv", f, "text/csv")},
                headers=auth_headers,
            )
        assert resp1.json()["imported"] == 10
        # Second import — all should be duplicates
        with open(csv_path, "rb") as f:
            resp2 = client.post(
                "/finance/transactions/csv",
                files={"file": ("test.csv", f, "text/csv")},
                headers=auth_headers,
            )
        assert resp2.status_code == 201
        data = resp2.json()
        assert data["imported"] == 0
        assert data["skipped_duplicates"] == 10

    def test_csv_auto_categorization(self, client, auth_headers):
        """#645: CSV-Zeilen ohne Kategorie werden auto-kategorisiert."""
        csv_content = "date;amount;description\n2026-01-15;-42,50;REWE Schwerin\n2026-01-16;-15,99;Netflix Abo\n"
        resp = client.post(
            "/finance/transactions/csv",
            files={"file": ("auto.csv", csv_content.encode(), "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["imported"] == 2
        # Check that categories were assigned
        txns = client.get("/finance/transactions", headers=auth_headers).json()
        csv_txns = [t for t in txns if t["source"] == "csv"]
        categories = [t["category"] for t in csv_txns]
        assert "Lebensmittel" in categories  # REWE → Lebensmittel
        assert "Unterhaltung" in categories  # Netflix → Unterhaltung

    def test_transactions_by_category(self, client, auth_headers):
        """#645: Aggregation nach Kategorie."""
        client.post(
            "/finance/transactions",
            json={"date": "2026-03-10T10:00:00", "amount": -50.0, "category": "Essen"},
            headers=auth_headers,
        )
        client.post(
            "/finance/transactions",
            json={"date": "2026-03-11T10:00:00", "amount": -30.0, "category": "Essen"},
            headers=auth_headers,
        )
        resp = client.get("/finance/transactions/by-category?year=2026&month=3", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "Essen" in data["categories"]
        assert data["categories"]["Essen"] == 80.0

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


class TestContractDetection:
    """#646: Vertrags-Erkennung und Deadline-Berechnung."""

    def test_calculate_deadlines(self, client, auth_headers):
        create = client.post(
            "/finance/contracts",
            json={
                "name": "Fitness Studio",
                "amount": 29.99,
                "interval": "monthly",
                "start_date": "2025-01-01",
                "cancellation_days": 30,
                "end_date": "2026-12-31",
            },
            headers=auth_headers,
        )
        cid = create.json()["id"]
        resp = client.post(f"/finance/contracts/{cid}/calculate-deadlines", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["next_billing"] is not None
        assert data["cancellation_deadline"] is not None

    def test_detect_from_transactions(self, client, auth_headers):
        # Create recurring transactions
        for month in range(1, 5):
            client.post(
                "/finance/transactions",
                json={
                    "date": f"2026-{month:02d}-15T10:00:00",
                    "amount": -9.99,
                    "description": "Spotify Premium",
                    "category": "Unterhaltung",
                },
                headers=auth_headers,
            )
        resp = client.get("/finance/contracts/detect-from-transactions?min_occurrences=3", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["description"] == "Spotify Premium"
        assert data[0]["amount"] == 9.99


class TestFinanceInvoices:
    def test_create_invoice(self, client, auth_headers):
        resp = client.post(
            "/finance/invoices",
            json={"recipient": "Kunde A", "total": 1200.0, "due_date": "2026-02-01", "status": "open"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["recipient"] == "Kunde A"

    def test_auto_invoice_number(self, client, auth_headers):
        """#647: Auto-generierte Rechnungsnummer."""
        resp = client.post(
            "/finance/invoices",
            json={"recipient": "Auto-Nr Test", "total": 100.0, "due_date": "2026-06-01"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["invoice_number"].startswith("RE-2026-")

    def test_sequential_invoice_numbers(self, client, auth_headers):
        """#647: Fortlaufende Rechnungsnummern."""
        resp1 = client.post(
            "/finance/invoices",
            json={"recipient": "Seq1", "total": 100.0, "due_date": "2026-06-01"},
            headers=auth_headers,
        )
        resp2 = client.post(
            "/finance/invoices",
            json={"recipient": "Seq2", "total": 200.0, "due_date": "2026-06-15"},
            headers=auth_headers,
        )
        nr1 = resp1.json()["invoice_number"]
        nr2 = resp2.json()["invoice_number"]
        seq1 = int(nr1.split("-")[-1])
        seq2 = int(nr2.split("-")[-1])
        assert seq2 == seq1 + 1

    def test_mark_invoice_paid(self, client, auth_headers):
        """#647: Rechnung als bezahlt markieren."""
        create = client.post(
            "/finance/invoices",
            json={"recipient": "PayTest", "total": 500.0, "due_date": "2026-06-01", "status": "open"},
            headers=auth_headers,
        )
        iid = create.json()["id"]
        resp = client.post(f"/finance/invoices/{iid}/mark-paid", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paid"
        assert data["payment_date"] is not None

    def test_mark_already_paid_fails(self, client, auth_headers):
        """#647: Doppelt-bezahlt-Schutz."""
        create = client.post(
            "/finance/invoices",
            json={"recipient": "DblPay", "total": 100.0, "due_date": "2026-06-01", "status": "open"},
            headers=auth_headers,
        )
        iid = create.json()["id"]
        client.post(f"/finance/invoices/{iid}/mark-paid", headers=auth_headers)
        resp = client.post(f"/finance/invoices/{iid}/mark-paid", headers=auth_headers)
        assert resp.status_code == 400

    def test_mark_invoice_overdue(self, client, auth_headers):
        """#647: Rechnung als ueberfaellig markieren."""
        create = client.post(
            "/finance/invoices",
            json={"recipient": "OverdueTest", "total": 100.0, "due_date": "2026-01-01", "status": "open"},
            headers=auth_headers,
        )
        iid = create.json()["id"]
        resp = client.post(f"/finance/invoices/{iid}/mark-overdue", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "overdue"

    def test_invoice_stats(self, client, auth_headers):
        """#647: Rechnungsstatistik."""
        client.post(
            "/finance/invoices",
            json={"recipient": "StatA", "total": 100.0, "due_date": "2026-06-01", "status": "open"},
            headers=auth_headers,
        )
        client.post(
            "/finance/invoices",
            json={"recipient": "StatB", "total": 200.0, "due_date": "2026-06-01", "status": "draft"},
            headers=auth_headers,
        )
        resp = client.get("/finance/invoices/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "open" in data
        assert "paid" in data
        assert "draft" in data

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
