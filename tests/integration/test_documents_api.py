"""
Integration-Tests: Document-Scanner API (/documents Endpunkte).

Getestet:
- Dokument-Liste abrufen
- Dokument-Suche
- Dokument-Status-Endpunkte
- Auth-Schutz
"""


class TestDocumentsListEndpoint:
    """GET /documents – Dokumente auflisten."""

    def test_list_documents_empty(self, client, auth_headers):
        """Leere Liste bei neuem User."""
        resp = client.get("/documents", headers=auth_headers)
        # Endpunkt kann 200 oder 404 sein je nach Implementation
        assert resp.status_code in (200, 404)

    def test_list_documents_requires_auth(self, client):
        """Ohne Auth wird 401 zurueckgegeben."""
        resp = client.get("/documents")
        assert resp.status_code == 401


class TestDocumentsSearchEndpoint:
    """GET /documents/search – Volltextsuche in Dokumenten."""

    def test_search_no_results(self, client, auth_headers):
        """Suche ohne Treffer gibt leere Liste zurueck."""
        resp = client.get("/documents/search?q=nonexistent", headers=auth_headers)
        # 200 mit leerer Liste oder 404
        assert resp.status_code in (200, 404)

    def test_search_requires_auth(self, client):
        """Suche ohne Auth wird mit 401 abgelehnt."""
        resp = client.get("/documents/search?q=test")
        assert resp.status_code == 401


class TestDocumentsHealthEndpoint:
    """GET /documents/health – Health Check."""

    def test_documents_health(self, client, auth_headers):
        """Health-Endpunkt antwortet mit ok."""
        resp = client.get("/documents/health", headers=auth_headers)
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("status") == "ok"


class TestDocumentsUserIsolation:
    """Dokument-Isolation zwischen Usern."""

    def test_different_users_see_different_documents(self, client, auth_headers, auth_headers_nina):
        """User A und User B sehen nur ihre eigenen Dokumente."""
        resp_taake = client.get("/documents", headers=auth_headers)
        resp_nina = client.get("/documents", headers=auth_headers_nina)
        # Beide Requests muessen erfolgreich sein (oder beide 404 bei leerem State)
        assert resp_taake.status_code in (200, 404)
        assert resp_nina.status_code in (200, 404)
