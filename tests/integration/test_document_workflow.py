"""Integration-Tests fuer Document Scan Workflow: OCR -> Kategorie -> Frist -> Task (#648)."""

import io
from datetime import date, timedelta
from unittest.mock import AsyncMock


class TestUploadTriggersOCR:
    """Upload loest OCR-Background-Task mit Klassifikation und Frist-Extraktion aus."""

    def test_upload_triggers_background_ocr(self, client, auth_headers):
        """Upload mit run_ocr=True loest den Background-Task aus (synchron im TestClient)."""
        pdf_content = b"%PDF-1.4 test content"
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("rechnung.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"title": "Rechnung Test", "run_ocr": "true"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Rechnung Test"
        assert data["id"] > 0

    def test_upload_without_ocr_skips_background(self, client, auth_headers):
        """Upload mit run_ocr=false loest keinen Background-Task aus."""
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("manual.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Manuell", "run_ocr": "false"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Manuell"
        # No OCR text since background task was skipped
        assert data["ocr_text"] is None

    def test_ocr_background_classifies_document(self, client, auth_headers):
        """Background-OCR klassifiziert das Dokument und speichert die Kategorie."""
        import api.dependencies as deps

        ocr_svc = deps._svc["ocr"]
        # Mock OCR to return invoice-like text
        invoice_text = "Rechnung Rechnungsnummer 12345 Rechnungsdatum 01.01.2026 Nettobetrag 100 EUR IBAN DE89"
        ocr_svc.extract_text = AsyncMock(
            return_value={"text": invoice_text, "confidence": 95.0, "method": "mock", "words_data": None}
        )
        ocr_svc.classify_document = AsyncMock(return_value="invoice")
        ocr_svc.extract_deadline = AsyncMock(return_value=None)

        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("inv.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Klassifikations-Test"},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["id"]

        # After background task ran, check DB was updated
        detail = client.get(f"/household-documents/{doc_id}", headers=auth_headers)
        assert detail.status_code == 200
        doc = detail.json()
        assert doc["category"] == "invoice"

    def test_ocr_background_extracts_deadline_and_creates_task(self, client, auth_headers):
        """Background-OCR extrahiert Frist und erstellt einen Task."""
        import api.dependencies as deps

        ocr_svc = deps._svc["ocr"]
        task_svc = deps._svc["task"]

        future_date = date.today() + timedelta(days=14)
        ocr_text = f"Zahlbar bis {future_date.strftime('%d.%m.%Y')} bitte ueberweisen"

        ocr_svc.extract_text = AsyncMock(
            return_value={"text": ocr_text, "confidence": 90.0, "method": "mock", "words_data": None}
        )
        ocr_svc.classify_document = AsyncMock(return_value="invoice")
        ocr_svc.extract_deadline = AsyncMock(return_value=future_date)

        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("frist.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Frist-Dokument"},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["id"]

        # Verify deadline saved in DB
        detail = client.get(f"/household-documents/{doc_id}", headers=auth_headers)
        assert detail.status_code == 200
        doc = detail.json()
        assert doc["deadline_date"] == future_date.isoformat()

        # Verify task was created (TaskService is real DB-backed in conftest)
        tasks = task_svc._db()
        from src.services.database import Task

        with tasks as session:
            task = session.query(Task).filter(Task.title.contains("Frist-Dokument")).first()
            assert task is not None
            assert "Frist:" in task.title
            assert future_date.isoformat() in task.title

    def test_ocr_background_creates_notification(self, client, auth_headers):
        """Background-OCR erstellt eine Benachrichtigung nach Verarbeitung."""
        import api.dependencies as deps

        ocr_svc = deps._svc["ocr"]
        deps._svc["notification"]  # ensure service is loaded

        ocr_svc.extract_text = AsyncMock(
            return_value={"text": "Test text", "confidence": 80.0, "method": "mock", "words_data": None}
        )
        ocr_svc.classify_document = AsyncMock(return_value="receipt")
        ocr_svc.extract_deadline = AsyncMock(return_value=None)

        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("bon.jpg", io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 50), "image/jpeg")},
            data={"title": "Kassenbon-Test"},
        )
        assert resp.status_code == 201
        resp.json()["id"]  # verify id present

        # Verify notification was created (real DB-backed service)
        from src.services.database import Notification, get_db

        with get_db()() as session:
            notif = session.query(Notification).filter(Notification.title.contains("Kassenbon-Test")).first()
            assert notif is not None
            assert "receipt" in notif.title


class TestReprocessEndpoint:
    """POST /household-documents/{doc_id}/reprocess Tests."""

    def test_reprocess_existing_document(self, client, auth_headers):
        """Reprocess loest erneut OCR-Background fuer ein bestehendes Dokument aus."""
        # Upload first
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("reprocess.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Reprocess-Test", "run_ocr": "false"},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["id"]

        # Now reprocess
        import api.dependencies as deps

        ocr_svc = deps._svc["ocr"]
        ocr_svc.extract_text = AsyncMock(
            return_value={"text": "Reprocessed text", "confidence": 85.0, "method": "mock", "words_data": None}
        )
        ocr_svc.classify_document = AsyncMock(return_value="contract")
        ocr_svc.extract_deadline = AsyncMock(return_value=None)

        resp = client.post(f"/household-documents/{doc_id}/reprocess", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == doc_id

        # After background task, check classification was applied
        detail = client.get(f"/household-documents/{doc_id}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["category"] == "contract"

    def test_reprocess_nonexistent_document(self, client, auth_headers):
        """Reprocess eines nicht existierenden Dokuments gibt 404."""
        resp = client.post("/household-documents/99999/reprocess", headers=auth_headers)
        assert resp.status_code == 404

    def test_reprocess_without_auth(self, client):
        """Reprocess ohne JWT wird abgelehnt."""
        resp = client.post("/household-documents/1/reprocess")
        assert resp.status_code == 401

    def test_reprocess_other_users_document(self, client, auth_headers, auth_headers_nina):
        """User kann Dokumente eines anderen Users nicht reprocessen."""
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("own.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Eigenes Dokument", "run_ocr": "false"},
        )
        doc_id = resp.json()["id"]

        resp = client.post(f"/household-documents/{doc_id}/reprocess", headers=auth_headers_nina)
        assert resp.status_code == 404


class TestStatsEndpoint:
    """GET /household-documents/stats Tests."""

    def test_stats_empty(self, client, auth_headers):
        """Stats fuer User ohne Dokumente."""
        resp = client.get("/household-documents/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["categories"] == {}
        assert data["upcoming_deadlines"] == 0

    def test_stats_counts_per_category(self, client, auth_headers):
        """Stats zaehlt Dokumente pro Kategorie korrekt."""
        for cat in ("invoice", "invoice", "warranty", "contract"):
            client.post(
                "/household-documents/upload",
                headers=auth_headers,
                files={"file": (f"{cat}.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
                data={"title": f"Dok {cat}", "category": cat, "run_ocr": "false"},
            )

        resp = client.get("/household-documents/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["categories"]["invoice"] == 2
        assert data["categories"]["warranty"] == 1
        assert data["categories"]["contract"] == 1

    def test_stats_upcoming_deadlines(self, client, auth_headers):
        """Stats zaehlt Dokumente mit Frist in den naechsten 30 Tagen."""
        import api.dependencies as deps

        ocr_svc = deps._svc["ocr"]
        future_date = date.today() + timedelta(days=10)

        ocr_svc.extract_text = AsyncMock(
            return_value={"text": "Frist text", "confidence": 90.0, "method": "mock", "words_data": None}
        )
        ocr_svc.classify_document = AsyncMock(return_value="invoice")
        ocr_svc.extract_deadline = AsyncMock(return_value=future_date)

        # Upload with OCR that sets a deadline
        client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("frist.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Mit Frist"},
        )

        # Upload without deadline
        ocr_svc.extract_deadline = AsyncMock(return_value=None)
        client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("nofrist.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Ohne Frist"},
        )

        resp = client.get("/household-documents/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["upcoming_deadlines"] == 1

    def test_stats_ignores_past_deadlines(self, client, auth_headers):
        """Stats zaehlt keine Dokumente mit vergangener Frist."""
        from src.services.database import HouseholdDocument, UserProfile, get_db

        # Directly insert a document with past deadline
        with get_db()() as session:
            user = session.query(UserProfile).filter_by(user_key="taake").first()
            doc = HouseholdDocument(
                user_id=user.id,
                title="Vergangene Frist",
                category="invoice",
                deadline_date=date.today() - timedelta(days=5),
            )
            session.add(doc)

        resp = client.get("/household-documents/stats", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["upcoming_deadlines"] == 0

    def test_stats_without_auth(self, client):
        """Stats ohne JWT wird abgelehnt."""
        resp = client.get("/household-documents/stats")
        assert resp.status_code == 401

    def test_stats_user_isolation(self, client, auth_headers, auth_headers_nina):
        """Stats zeigt nur eigene Dokumente."""
        # Taake uploads
        client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("t.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Taakes Dok", "category": "invoice", "run_ocr": "false"},
        )

        # Nina's stats should be empty
        resp = client.get("/household-documents/stats", headers=auth_headers_nina)
        assert resp.status_code == 200
        assert resp.json()["categories"] == {}
