"""Integration-Tests: Auth-Flow (Login → Token → Request → Refresh)."""

from tests.integration.conftest import TEST_PASSWORD


class TestAuthFlow:
    def test_login_and_use_token(self, client):
        """Login → Access-Token → authentifizierter Request."""
        # Login
        resp = client.post("/auth/login", json={"username": "taake", "password": TEST_PASSWORD})
        assert resp.status_code == 200
        tokens = resp.json()
        assert tokens["user_key"] == "taake"

        # Token für geschützten Endpoint nutzen
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_refresh_and_reuse(self, client):
        """Login → Refresh → neuer Token → authentifizierter Request."""
        # Login
        login = client.post("/auth/login", json={"username": "nina", "password": TEST_PASSWORD})
        tokens = login.json()

        # Refresh
        resp = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert resp.status_code == 200
        new_tokens = resp.json()
        assert new_tokens["user_key"] == "nina"

        # Neuen Token verwenden
        headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 200

    def test_invalid_token_rejected(self, client):
        """Ungültiger Token → 401."""
        headers = {"Authorization": "Bearer invalid-garbage-token"}
        resp = client.get("/tasks", headers=headers)
        assert resp.status_code == 401

    def test_no_token_rejected(self, client):
        """Kein Token → 401."""
        resp = client.get("/tasks")
        assert resp.status_code == 401
