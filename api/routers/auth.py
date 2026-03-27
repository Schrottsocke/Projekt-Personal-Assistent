"""POST /auth/login, POST /auth/refresh"""

from fastapi import APIRouter, HTTPException, status

from api.auth.jwt_handler import create_access_token, create_refresh_token, verify_token
from api.auth.models import LoginRequest, TokenResponse, RefreshRequest
from config.settings import settings

router = APIRouter()

_PASSWORDS = {
    "taake": lambda: settings.API_PASSWORD_TAAKE,
    "nina": lambda: settings.API_PASSWORD_NINA,
}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user_key = body.username.lower()
    get_pw = _PASSWORDS.get(user_key)
    if not get_pw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unbekannter Nutzer.")

    expected = get_pw()
    if not expected or body.password != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falsches Passwort.")

    return TokenResponse(
        access_token=create_access_token(user_key),
        refresh_token=create_refresh_token(user_key),
        user_key=user_key,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    user_key = verify_token(body.refresh_token, token_type="refresh")
    return TokenResponse(
        access_token=create_access_token(user_key),
        refresh_token=create_refresh_token(user_key),
        user_key=user_key,
    )
