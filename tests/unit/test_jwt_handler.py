"""Tests für api/auth/jwt_handler.py – Token-Erstellung, Validierung, Ablauf."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from jose import jwt
from fastapi import HTTPException

from config.settings import Settings


# Konstanten aus jwt_handler
ALGORITHM = "HS256"
SECRET = "test-secret-key-that-is-at-least-32-characters-long"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch):
    """Patcht Settings-Attribute für JWT-Tests."""
    monkeypatch.setattr(Settings, "API_SECRET_KEY", SECRET)
    monkeypatch.setattr(Settings, "API_TOKEN_EXPIRE_DAYS", 30)


class TestCreateAccessToken:
    def test_returns_string(self):
        from api.auth.jwt_handler import create_access_token
        token = create_access_token("taake")
        assert isinstance(token, str)

    def test_token_contains_correct_claims(self):
        from api.auth.jwt_handler import create_access_token
        token = create_access_token("taake")
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        assert payload["sub"] == "taake"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_token_expiry_is_future(self):
        from api.auth.jwt_handler import create_access_token
        token = create_access_token("nina")
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > datetime.now(timezone.utc)


class TestCreateRefreshToken:
    def test_returns_string(self):
        from api.auth.jwt_handler import create_refresh_token
        token = create_refresh_token("taake")
        assert isinstance(token, str)

    def test_refresh_token_type(self):
        from api.auth.jwt_handler import create_refresh_token
        token = create_refresh_token("taake")
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        assert payload["type"] == "refresh"

    def test_refresh_expiry_longer_than_access(self):
        from api.auth.jwt_handler import create_access_token, create_refresh_token
        access = create_access_token("taake")
        refresh = create_refresh_token("taake")
        a_exp = jwt.decode(access, SECRET, algorithms=[ALGORITHM])["exp"]
        r_exp = jwt.decode(refresh, SECRET, algorithms=[ALGORITHM])["exp"]
        assert r_exp > a_exp


class TestVerifyToken:
    def test_valid_access_token(self):
        from api.auth.jwt_handler import create_access_token, verify_token
        token = create_access_token("taake")
        user_key = verify_token(token, token_type="access")
        assert user_key == "taake"

    def test_valid_refresh_token(self):
        from api.auth.jwt_handler import create_refresh_token, verify_token
        token = create_refresh_token("nina")
        user_key = verify_token(token, token_type="refresh")
        assert user_key == "nina"

    def test_wrong_token_type_raises(self):
        from api.auth.jwt_handler import create_access_token, verify_token
        token = create_access_token("taake")
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, token_type="refresh")
        assert exc_info.value.status_code == 401

    def test_invalid_token_raises(self):
        from api.auth.jwt_handler import verify_token
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid-garbage-token")
        assert exc_info.value.status_code == 401

    def test_expired_token_raises(self):
        from api.auth.jwt_handler import verify_token
        payload = {
            "sub": "taake",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401

    def test_missing_sub_raises(self):
        from api.auth.jwt_handler import verify_token
        payload = {
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401

    def test_wrong_secret_raises(self):
        from api.auth.jwt_handler import verify_token
        payload = {
            "sub": "taake",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "wrong-secret-key-wrong-secret-key", algorithm=ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401
