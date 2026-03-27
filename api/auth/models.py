"""Pydantic-Modelle für Auth-Endpunkte."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str   # "taake" oder "nina"
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_key: str


class RefreshRequest(BaseModel):
    refresh_token: str
