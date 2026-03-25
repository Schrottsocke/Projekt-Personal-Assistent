from typing import Optional
from pydantic import BaseModel


class DriveFileOut(BaseModel):
    id: str
    name: str
    mime_type: Optional[str] = None
    modified_time: Optional[str] = None
    size: Optional[str] = None
    web_view_link: Optional[str] = None


class DriveUploadResponse(BaseModel):
    id: str
    name: str
    web_view_link: Optional[str] = None
