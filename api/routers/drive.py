"""GET /drive/files, POST /drive/upload"""

import logging
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_drive_service
from api.schemas.drive import DriveFileOut, DriveUploadResponse
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.get("/files")
async def list_files(
    user_key: Annotated[str, Depends(get_current_user)],
    drive_svc=Depends(get_drive_service),
    q: str = "",
    limit: int = 20,
):
    if not drive_svc.is_connected(user_key):
        return {"connected": False, "files": []}
    try:
        if q:
            files = await drive_svc.search_files(user_key, q, limit=limit)
        else:
            files = await drive_svc.list_files(user_key, limit=limit)
        return {
            "connected": True,
            "files": [
                DriveFileOut(
                    id=f.get("id", ""),
                    name=f.get("name", ""),
                    mime_type=f.get("mimeType"),
                    modified_time=f.get("modifiedTime"),
                    size=f.get("size"),
                    web_view_link=f.get("webViewLink"),
                )
                for f in (files or [])
            ],
        }
    except Exception as e:
        logger.error("Drive list_files Fehler: %s", e)
        raise HTTPException(status_code=500, detail="Drive-Fehler.")


@router.post("/upload", response_model=DriveUploadResponse)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_file(
    request: Request,
    user_key: Annotated[str, Depends(get_current_user)],
    drive_svc=Depends(get_drive_service),
    file: UploadFile = File(...),
):
    if not drive_svc.is_connected(user_key):
        raise HTTPException(status_code=503, detail="Google Drive nicht verbunden.")
    try:
        max_size = settings.MAX_UPLOAD_SIZE
        content = bytearray()
        while chunk := await file.read(8192):
            content.extend(chunk)
            if len(content) > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Datei zu gross. Maximum: {max_size // (1024 * 1024)}MB",
                )
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or "upload").suffix) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        result = await drive_svc.upload_file(user_key, tmp_path)
        tmp_path.unlink(missing_ok=True)
        if not result:
            raise HTTPException(status_code=500, detail="Upload fehlgeschlagen.")
        return DriveUploadResponse(
            id=result.get("id", ""),
            name=result.get("name", file.filename or ""),
            web_view_link=result.get("webViewLink"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Drive upload Fehler: %s", e)
        raise HTTPException(status_code=500, detail="Upload fehlgeschlagen.")
