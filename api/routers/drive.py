"""GET /drive/files, POST /drive/upload, DELETE /drive/files/{id}, GET /drive/files/{id}/download"""

import logging
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import Response
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
    limit: int = Query(20, ge=1, le=100),
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
        try:
            result = await drive_svc.upload_file(user_key, tmp_path)
        finally:
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


@router.delete("/files/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    drive_svc=Depends(get_drive_service),
):
    if not drive_svc.is_connected(user_key):
        raise HTTPException(status_code=503, detail="Google Drive nicht verbunden.")
    try:
        ok = await drive_svc.delete_file(user_key, file_id)
        if not ok:
            raise HTTPException(status_code=500, detail="Datei konnte nicht geloescht werden.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Drive delete Fehler: %s", e)
        raise HTTPException(status_code=500, detail="Drive-Fehler.")


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    user_key: Annotated[str, Depends(get_current_user)],
    drive_svc=Depends(get_drive_service),
):
    if not drive_svc.is_connected(user_key):
        raise HTTPException(status_code=503, detail="Google Drive nicht verbunden.")
    try:
        # Get file metadata for name/mime
        service = drive_svc._get_service(user_key)
        import asyncio

        meta = await asyncio.to_thread(service.files().get(fileId=file_id, fields="name,mimeType").execute)
        content = await drive_svc.download_file(user_key, file_id)
        if content is None:
            raise HTTPException(status_code=500, detail="Download fehlgeschlagen.")
        filename = meta.get("name", "download")
        mime = meta.get("mimeType", "application/octet-stream")
        return Response(
            content=content,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Drive download Fehler: %s", e)
        raise HTTPException(status_code=500, detail="Drive-Fehler.")
