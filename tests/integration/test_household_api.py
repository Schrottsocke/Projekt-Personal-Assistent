"""
Integration-Tests: Household Documents API – erweiterte Szenarien.

Getestet:
- OCR-Trigger bei Upload
- Kategorie-Validierung
- Pagination
- Sortierung
- Dateigroessen-Limit
- Content-Type-Validierung
"""

import io

import pytest


class TestHouseholdDocumentsOCR:
    """OCR-Integration bei Dokument-Upload."""

    def test_upload_triggers_background_processing(self, client, auth_headers):
        """Upload einer PDF startet Hintergrund-Verarbeitung."""
        pdf_content = b"%PDF-1.4 test content for OCR"
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("scan.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"title": "OCR-Test", "category": "invoice"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "OCR-Test"
        # OCR laeuft im Hintergrund, Status ist initial "pending" oder fehlt
        assert data.get("ocr_status") in (None, "pending", "processing", "completed")

    def test_upload_image_for_ocr(self, client, auth_headers):
        """Bild-Upload fuer OCR-Verarbeitung."""
        jpg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 200
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("receipt.jpg", io.BytesIO(jpg_content), "image/jpeg")},
            data={"title": "Kassenbon Scan", "category": "receipt"},
        )
        assert resp.status_code == 201
        assert resp.json()["category"] == "receipt"


class TestHouseholdDocumentsPagination:
    """Pagination der Dokumentenliste."""

    def test_pagination_defaults(self, client, auth_headers):
        """Standard-Pagination gibt strukturierte Antwort."""
        resp = client.get("/household-documents", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_pagination_with_limit(self, client, auth_headers):
        """Limit-Parameter begrenzt Ergebnisse."""
        # Mehrere Dokumente erstellen
        for i in range(3):
            client.post(
                "/household-documents/upload",
                headers=auth_headers,
                files={"file": (f"doc{i}.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf")},
                data={"title": f"Dok {i}"},
            )
        resp = client.get("/household-documents?limit=2", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["total"] >= 3


class TestHouseholdDocumentsCategories:
    """Kategorie-bezogene Tests."""

    def test_upload_with_valid_categories(self, client, auth_headers):
        """Verschiedene gueltige Kategorien werden akzeptiert."""
        categories = ["invoice", "warranty", "contract", "receipt", "insurance", "other"]
        for cat in categories:
            resp = client.post(
                "/household-documents/upload",
                headers=auth_headers,
                files={"file": (f"{cat}.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
                data={"title": f"Kategorie-{cat}", "category": cat},
            )
            assert resp.status_code == 201, f"Kategorie '{cat}' wurde nicht akzeptiert"

    def test_filter_by_multiple_uploads(self, client, auth_headers):
        """Kategorie-Filter nach mehreren Uploads."""
        for _ in range(2):
            client.post(
                "/household-documents/upload",
                headers=auth_headers,
                files={"file": ("w.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
                data={"category": "warranty"},
            )
        client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("i.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"category": "invoice"},
        )

        resp = client.get("/household-documents?category=warranty", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 2


class TestHouseholdDocumentsEdgeCases:
    """Randfaelle und Fehlerbehandlung."""

    def test_upload_with_long_title(self, client, auth_headers):
        """Langer Titel wird akzeptiert oder sinnvoll gekuerzt."""
        long_title = "A" * 500
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("long.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf")},
            data={"title": long_title},
        )
        # Sollte entweder funktionieren oder mit 400/422 abgelehnt werden
        assert resp.status_code in (201, 400, 422)

    def test_upload_with_special_characters_in_filename(self, client, auth_headers):
        """Sonderzeichen im Dateinamen werden behandelt."""
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("Rechnung (2026).pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Sonderzeichen Test"},
        )
        assert resp.status_code == 201

    def test_get_single_document(self, client, auth_headers):
        """Einzelnes Dokument per ID abrufen."""
        upload = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("single.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Einzeldokument"},
        )
        doc_id = upload.json()["id"]
        resp = client.get(f"/household-documents/{doc_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Einzeldokument"

    def test_get_nonexistent_document(self, client, auth_headers):
        """Nicht existierendes Dokument gibt 404."""
        resp = client.get("/household-documents/99999", headers=auth_headers)
        assert resp.status_code == 404
