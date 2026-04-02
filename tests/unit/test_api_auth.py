"""Tests für api/routers/auth.py – Login und Refresh Endpoints."""

import pytest
from unittest.mock import patch, AsyncMock

from config.settings import Settings

SECRET = "test-secret-key-that-is-at-least-32-characters-long"
PASSWORD = "test-password-123"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    monkeypatch.setattr(Settings, "API_SECRET_KEY", SECRET)
    monkeypatch.setattr(Settings, "API_TOKEN_EXPIRE_DAYS", 30)
    monkeypatch.setattr(Settings, "API_PASSWORD_TAAKE", PASSWORD)
    monkeypatch.setattr(Settings, "API_PASSWORD_NINA", PASSWORD)
    monkeypatch.setattr(Settings, "API_CORS_ORIGINS", ["http://localhost"])


@pytest.fixture
def client():
    """TestClient mit gemocktem Startup."""
    with patch("api.dependencies.startup", new_callable=AsyncMock):
        from api.main import app
        from fastapi.testclient import TestClient

        return TestClient(app)


class TestLogin:
    def test_login_success_taake(self, client):
        resp = client.post("/auth/login", json={"username": "taake", "password": PASSWORD})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user_key"] == "taake"
        assert data["token_type"] == "bearer"

    def test_login_success_nina(self, client):
        resp = client.post("/auth/login", json={"username": "nina", "password": PASSWORD})
        assert resp.status_code == 200
        assert resp.json()["user_key"] == "nina"

    def test_login_case_insensitive(self, client):
        resp = client.post("/auth/login", json={"username": "TAAKE", "password": PASSWORD})
        assert resp.status_code == 200
        assert resp.json()["user_key"] == "taake"

    def test_login_unknown_user(self, client):
        resp = client.post("/auth/login", json={"username": "hacker", "password": PASSWORD})
        assert resp.status_code == 401

    def test_login_wrong_password(self, client):
        resp = client.post("/auth/login", json={"username": "taake", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_empty_password(self, client):
        resp = client.post("/auth/login", json={"username": "taake", "password": ""})
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/auth/login", json={"username": "taake"})
        assert resp.status_code == 422  # Pydantic validation error


class TestRefresh:
    def test_refresh_success(self, client):
        # Erst Login
        login_resp = client.post("/auth/login", json={"username": "taake", "password": PASSWORD})
        refresh_token = login_resp.json()["refresh_token"]
        # Dann Refresh
        resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user_key"] == "taake"

    def test_refresh_with_access_token_fails(self, client):
        login_resp = client.post("/auth/login", json={"username": "taake", "password": PASSWORD})
        access_token = login_resp.json()["access_token"]
        resp = client.post("/auth/refresh", json={"refresh_token": access_token})
        assert resp.status_code == 401

    def test_refresh_with_invalid_token(self, client):
        resp = client.post("/auth/refresh", json={"refresh_token": "garbage"})
        assert resp.status_code == 401


class TestProtectedEndpoints:
    def test_health_endpoint_no_auth(self, client):
        resp = client.get("/health")
        assert resp.status_code in (200, 503)  # kein Auth nötig; Services ggf. nicht initialisiert
        assert "status" in resp.json()

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
