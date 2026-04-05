"""Integration-Tests fuer Household Documents Upload/Download/Delete (#688)."""

import io


class TestHouseholdDocumentsUpload:
    """Upload-Endpoint Tests."""

    def test_upload_pdf(self, client, auth_headers):
        """Upload einer PDF-Datei erstellt einen DB-Eintrag."""
        pdf_content = b"%PDF-1.4 test content"
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            data={"title": "Mietvertrag 2026", "category": "contract"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Mietvertrag 2026"
        assert data["category"] == "contract"
        assert data["id"] > 0

    def test_upload_jpg(self, client, auth_headers):
        """Upload einer JPG-Datei funktioniert."""
        # Minimal JFIF header
        jpg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("foto.jpg", io.BytesIO(jpg_content), "image/jpeg")},
            data={"title": "Kassenbon"},
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "Kassenbon"

    def test_upload_empty_file_rejected(self, client, auth_headers):
        """Leere Datei wird mit 400 abgelehnt."""
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        )
        assert resp.status_code == 400

    def test_upload_without_auth(self, client):
        """Upload ohne JWT wird mit 401 abgelehnt."""
        resp = client.post(
            "/household-documents/upload",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        )
        assert resp.status_code == 401

    def test_upload_auto_title(self, client, auth_headers):
        """Ohne expliziten Titel wird der Dateiname verwendet."""
        pdf_content = b"%PDF-1.4 content"
        resp = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("Rechnung_April.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
        assert resp.status_code == 201
        assert "Rechnung_April" in resp.json()["title"]


class TestHouseholdDocumentsList:
    """List-Endpoint Tests."""

    def test_list_empty(self, client, auth_headers):
        """Leere Liste bei neuem User."""
        resp = client.get("/household-documents", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_after_upload(self, client, auth_headers):
        """Nach Upload erscheint das Dokument in der Liste."""
        client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Test-Dok", "category": "invoice"},
        )
        resp = client.get("/household-documents", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Test-Dok"

    def test_list_filter_by_category(self, client, auth_headers):
        """Kategorie-Filter funktioniert."""
        for cat in ("invoice", "warranty", "invoice"):
            client.post(
                "/household-documents/upload",
                headers=auth_headers,
                files={"file": (f"{cat}.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
                data={"category": cat},
            )
        resp = client.get("/household-documents?category=invoice", headers=auth_headers)
        assert resp.json()["total"] == 2


class TestHouseholdDocumentsDelete:
    """Delete-Endpoint Tests."""

    def test_delete_document(self, client, auth_headers):
        """Dokument loeschen funktioniert."""
        upload = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("del.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Zum Loeschen"},
        )
        doc_id = upload.json()["id"]

        resp = client.delete(f"/household-documents/{doc_id}", headers=auth_headers)
        assert resp.status_code == 204

        # Verify deleted
        resp = client.get(f"/household-documents/{doc_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_nonexistent(self, client, auth_headers):
        """Loeschen eines nicht existierenden Dokuments gibt 404."""
        resp = client.delete("/household-documents/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestHouseholdDocumentsIsolation:
    """User-Isolation Tests."""

    def test_user_cannot_see_others_documents(self, client, auth_headers, auth_headers_nina):
        """User A kann Dokumente von User B nicht sehen."""
        upload = client.post(
            "/household-documents/upload",
            headers=auth_headers,  # taake
            files={"file": ("secret.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Taakes Geheim-Dokument"},
        )
        doc_id = upload.json()["id"]

        # Nina kann es nicht sehen
        resp = client.get(f"/household-documents/{doc_id}", headers=auth_headers_nina)
        assert resp.status_code == 404

    def test_user_cannot_delete_others_documents(self, client, auth_headers, auth_headers_nina):
        """User A kann Dokumente von User B nicht loeschen."""
        upload = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("keep.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            data={"title": "Nicht loeschen"},
        )
        doc_id = upload.json()["id"]

        resp = client.delete(f"/household-documents/{doc_id}", headers=auth_headers_nina)
        assert resp.status_code == 404

        # Original-User kann es noch sehen
        resp = client.get(f"/household-documents/{doc_id}", headers=auth_headers)
        assert resp.status_code == 200


class TestHouseholdDocumentsDownload:
    """Download-Endpoint Tests."""

    def test_download_uploaded_file(self, client, auth_headers):
        """Hochgeladene Datei kann wieder heruntergeladen werden."""
        content = b"%PDF-1.4 test download content"
        upload = client.post(
            "/household-documents/upload",
            headers=auth_headers,
            files={"file": ("download.pdf", io.BytesIO(content), "application/pdf")},
            data={"title": "Download-Test"},
        )
        doc_id = upload.json()["id"]

        resp = client.get(f"/household-documents/{doc_id}/download", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.content == content
        assert "application/pdf" in resp.headers.get("content-type", "")
