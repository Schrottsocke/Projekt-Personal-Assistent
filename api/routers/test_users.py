"""Testuser-Einladungssystem: Einladen, Akzeptieren, Verwalten."""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.auth.jwt_handler import create_access_token, create_refresh_token
from api.dependencies import get_current_user
from api.schemas.test_users import (
    AcceptInvitationRequest,
    InvitationCreate,
    InvitationCreateResponse,
    InvitationListResponse,
    InvitationResponse,
)
from config.settings import settings
from src.services.database import TestUserInvitation, UserProfile, get_db

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

INVITE_EXPIRY_DAYS = 7

# Erlaubte Admin-User, die Einladungen erstellen duerfen
_ADMIN_USERS = {"taake", "nina"}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ------------------------------------------------------------------
# Admin-Endpunkte (erfordern Auth)
# ------------------------------------------------------------------


@router.post("/invitations", response_model=InvitationCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_invitation(
    request: Request,
    body: InvitationCreate,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Erstellt eine neue Testuser-Einladung (nur Admin)."""
    if user_key not in _ADMIN_USERS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nur Admins duerfen Einladungen erstellen.")

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS)

    with get_db()() as db:
        invitation = TestUserInvitation(
            email=body.email,
            display_name=body.display_name,
            note=body.note,
            token_hash=token_hash,
            invited_by_user_id=user_key,
            status="pending",
            expires_at=expires_at,
        )
        db.add(invitation)
        db.flush()

        logger.info("Einladung erstellt: id=%s, email=%s, von=%s", invitation.id, body.email, user_key)

        return InvitationCreateResponse(
            id=invitation.id,
            email=invitation.email,
            display_name=invitation.display_name,
            note=invitation.note,
            status=invitation.status,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
            invite_token=raw_token,
        )


@router.get("/invitations", response_model=InvitationListResponse)
async def list_invitations(
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Listet alle Einladungen auf (nur Admin)."""
    if user_key not in _ADMIN_USERS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nur Admins duerfen Einladungen einsehen.")

    with get_db()() as db:
        invitations = db.query(TestUserInvitation).order_by(TestUserInvitation.created_at.desc()).all()
        return InvitationListResponse(
            invitations=[InvitationResponse.model_validate(inv) for inv in invitations],
            total=len(invitations),
        )


@router.post("/invitations/{token}/accept")
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def accept_invitation(
    request: Request,
    token: str,
    body: AcceptInvitationRequest,
):
    """Akzeptiert eine Einladung und erstellt den Testuser (oeffentlich)."""
    token_hash = _hash_token(token)

    with get_db()() as db:
        invitation = db.query(TestUserInvitation).filter(TestUserInvitation.token_hash == token_hash).first()

        if not invitation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Einladung nicht gefunden.")

        if invitation.status == "accepted":
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Einladung wurde bereits verwendet.")

        if invitation.status == "revoked":
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Einladung wurde widerrufen.")

        if invitation.status == "expired" or invitation.expires_at < datetime.now(timezone.utc):
            invitation.status = "expired"
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Einladung ist abgelaufen.")

        # User-Key aus E-Mail ableiten (Prefix vor @, lowercase, max 50 Zeichen)
        email_prefix = invitation.email.split("@")[0].lower().replace(".", "_").replace("+", "_")
        user_key = f"test_{email_prefix}"[:50]

        # Pruefen ob User-Key schon existiert
        existing = db.query(UserProfile).filter(UserProfile.user_key == user_key).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ein Benutzer mit diesem Schluessel existiert bereits.",
            )

        # Passwort hashen (PBKDF2-SHA256)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", body.password.encode(), user_key.encode(), 100_000
        ).hex()

        # UserProfile erstellen
        profile = UserProfile(
            user_key=user_key,
            is_onboarded=False,
            nickname=invitation.display_name,
            communication_style="casual",
            password_hash=password_hash,
        )
        db.add(profile)

        # Einladung als akzeptiert markieren
        invitation.status = "accepted"
        invitation.accepted_at = datetime.now(timezone.utc)
        db.flush()

        logger.info(
            "Einladung akzeptiert: id=%s, user_key=%s, email=%s",
            invitation.id,
            user_key,
            invitation.email,
        )

        # JWT-Tokens erstellen
        return {
            "access_token": create_access_token(user_key),
            "refresh_token": create_refresh_token(user_key),
            "token_type": "bearer",
            "user_key": user_key,
        }


@router.post("/invitations/{invitation_id}/resend", response_model=InvitationCreateResponse)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def resend_invitation(
    request: Request,
    invitation_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Generiert einen neuen Token fuer eine bestehende Einladung (nur Admin)."""
    if user_key not in _ADMIN_USERS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nur Admins duerfen Einladungen erneut senden.")

    with get_db()() as db:
        invitation = db.query(TestUserInvitation).filter(TestUserInvitation.id == invitation_id).first()

        if not invitation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Einladung nicht gefunden.")

        if invitation.status == "accepted":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Einladung wurde bereits akzeptiert.")

        # Neuen Token generieren
        raw_token = secrets.token_urlsafe(32)
        invitation.token_hash = _hash_token(raw_token)
        invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS)
        invitation.status = "pending"
        db.flush()

        logger.info("Einladung erneut gesendet: id=%s, email=%s", invitation.id, invitation.email)

        return InvitationCreateResponse(
            id=invitation.id,
            email=invitation.email,
            display_name=invitation.display_name,
            note=invitation.note,
            status=invitation.status,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
            invite_token=raw_token,
        )


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
):
    """Widerruft eine Einladung (nur Admin)."""
    if user_key not in _ADMIN_USERS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nur Admins duerfen Einladungen widerrufen.")

    with get_db()() as db:
        invitation = db.query(TestUserInvitation).filter(TestUserInvitation.id == invitation_id).first()

        if not invitation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Einladung nicht gefunden.")

        if invitation.status == "accepted":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Einladung wurde bereits akzeptiert.")

        invitation.status = "revoked"
        db.flush()

        logger.info("Einladung widerrufen: id=%s, email=%s", invitation.id, invitation.email)
