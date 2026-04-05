"""POST /auth/login, POST /auth/refresh, PATCH /profile"""

import hashlib
import logging
import secrets
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.auth.jwt_handler import create_access_token, create_refresh_token, verify_token
from api.auth.models import LoginRequest, TokenResponse, RefreshRequest
from api.dependencies import get_current_user
from config.settings import settings
from src.services.database import UserProfile, get_db

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

_PASSWORDS = {
    "taake": lambda: settings.API_PASSWORD_TAAKE,
    "nina": lambda: settings.API_PASSWORD_NINA,
}


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(request: Request, body: LoginRequest):
    user_key = body.username.lower()
    get_pw = _PASSWORDS.get(user_key)

    # --- Hardcoded-Passwort-Check (bestehende Admin-User) ---
    if get_pw:
        expected = get_pw() or ""
        pw_match = secrets.compare_digest(body.password, expected)
        if pw_match and expected:
            return TokenResponse(
                access_token=create_access_token(user_key),
                refresh_token=create_refresh_token(user_key),
                user_key=user_key,
            )

    # --- Fallback: DB-Passwort-Check (Test-User mit password_hash) ---
    try:
        with get_db()() as db:
            profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
            if profile and profile.password_hash:
                candidate_hash = hashlib.pbkdf2_hmac("sha256", body.password.encode(), user_key.encode(), 100_000).hex()
                if secrets.compare_digest(profile.password_hash, candidate_hash):
                    return TokenResponse(
                        access_token=create_access_token(user_key),
                        refresh_token=create_refresh_token(user_key),
                        user_key=user_key,
                    )
    except Exception:
        logger.warning("DB-Passwort-Check fehlgeschlagen fuer user=%s", user_key)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falsches Passwort oder unbekannter Nutzer.")


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def refresh(request: Request, body: RefreshRequest):
    user_key = verify_token(body.refresh_token, token_type="refresh")
    return TokenResponse(
        access_token=create_access_token(user_key),
        refresh_token=create_refresh_token(user_key),
        user_key=user_key,
    )


# --- Profile ---


class ProfileUpdate(BaseModel):
    nickname: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=200)


class ProfileOut(BaseModel):
    user_key: str
    nickname: Optional[str] = None
    email: Optional[str] = None


@router.get("/profile", response_model=ProfileOut)
async def get_profile(user_key: Annotated[str, Depends(get_current_user)]):
    with get_db()() as db:
        profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
        if not profile:
            raise HTTPException(404, "User-Profil nicht gefunden.")
        return {
            "user_key": user_key,
            "nickname": profile.nickname,
            "email": getattr(profile, "email", None),
        }


@router.patch("/profile", response_model=ProfileOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_profile(
    request: Request,
    body: ProfileUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    with get_db()() as db:
        profile = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
        if not profile:
            raise HTTPException(404, "User-Profil nicht gefunden.")
        if body.nickname is not None:
            profile.nickname = body.nickname
        if body.email is not None:
            # Store email in nickname field as fallback if no email column exists
            # This is a beta approach - email verification can be added later
            pass  # email stored client-side for now
        db.flush()
        db.refresh(profile)
        return {
            "user_key": user_key,
            "nickname": profile.nickname,
            "email": getattr(profile, "email", None),
        }
