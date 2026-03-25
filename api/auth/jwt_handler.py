"""
JWT-Handler: Token erstellen und validieren.
Nutzt python-jose (HS256).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from fastapi import HTTPException, status

from config.settings import settings

ALGORITHM = "HS256"


def create_access_token(user_key: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.API_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_key, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.API_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_key: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.API_TOKEN_EXPIRE_DAYS * 2)
    payload = {"sub": user_key, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.API_SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> str:
    """
    Validiert ein JWT und gibt den user_key zurück.

    Raises:
        HTTPException 401: Token ungültig oder abgelaufen.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungültiger oder abgelaufener Token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.API_SECRET_KEY, algorithms=[ALGORITHM])
        user_key: Optional[str] = payload.get("sub")
        ttype: Optional[str] = payload.get("type")
        if not user_key or ttype != token_type:
            raise credentials_exception
        return user_key
    except JWTError:
        raise credentials_exception
