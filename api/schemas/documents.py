from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentUpload(BaseModel):
    filename: str = Field(..., min_length=1, max_length=300)
    content_type: str = Field("image/jpeg", max_length=100)


class DocumentOut(BaseModel):
    id: int
    user_key: str
    doc_type: str
    filename: str
    summary: Optional[str] = None
    sender: Optional[str] = None
    amount: Optional[str] = None
    drive_link: Optional[str] = None
    drive_file_id: Optional[str] = None
    scanned_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]
    total: int
