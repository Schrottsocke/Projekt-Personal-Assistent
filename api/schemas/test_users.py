"""Pydantic-Schemas fuer Testuser-Einladungen."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InvitationCreate(BaseModel):
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=200)
    note: Optional[str] = Field(None, max_length=1000)


class InvitationResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    note: Optional[str] = None
    status: str
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationCreateResponse(InvitationResponse):
    """Antwort bei Erstellung – enthaelt den einmaligen Einladungstoken."""

    invite_token: str


class InvitationListResponse(BaseModel):
    invitations: list[InvitationResponse]
    total: int


class AcceptInvitationRequest(BaseModel):
    password: str = Field(..., min_length=8, max_length=200)
