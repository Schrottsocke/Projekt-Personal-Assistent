"""
Storage-Service: Abstrahiert Dateispeicherung (lokal / Google Drive).

Konfiguration via STORAGE_BACKEND env var: local | gdrive
"""

import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

# Erlaubte MIME-Types
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


def _sanitize_filename(name: str) -> str:
    """Sanitize filename: remove path traversal, normalize unicode, limit length."""
    # Strip directory components
    name = Path(name).name
    # Normalize unicode
    name = unicodedata.normalize("NFKD", name)
    # Remove dangerous characters
    name = re.sub(r"[^\w.\-]", "_", name)
    # Limit length (keep extension)
    stem, ext = (name.rsplit(".", 1) + [""])[:2]
    if ext:
        ext = f".{ext.lower()}"
    return f"{stem[:150]}{ext}"


def _validate_file(filename: str, content_type: str, size: int) -> None:
    """Validate file type and size. Raises ValueError on failure."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Dateityp '{ext}' nicht erlaubt. Erlaubt: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"MIME-Type '{content_type}' nicht erlaubt.")
    if size > settings.MAX_UPLOAD_SIZE:
        mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise ValueError(f"Datei zu gross ({size} Bytes). Maximum: {mb:.0f} MB.")
    if size == 0:
        raise ValueError("Leere Datei.")


class StorageService:
    """Abstraktes Storage-Backend fuer Datei-Uploads."""

    def __init__(self, drive_service=None):
        self.backend = getattr(settings, "STORAGE_BACKEND", "local")
        self._drive = drive_service

    async def save(
        self,
        user_key: str,
        filename: str,
        data: bytes,
        content_type: str = "",
    ) -> str:
        """
        Speichert Datei und gibt den relativen Pfad/Identifier zurueck.

        Returns:
            str – relativer Pfad (local) oder Drive-File-ID (gdrive).
        """
        safe_name = _sanitize_filename(filename)
        _validate_file(safe_name, content_type, len(data))

        if self.backend == "gdrive" and self._drive:
            return await self._save_gdrive(user_key, safe_name, data)
        return self._save_local(user_key, safe_name, data)

    def _save_local(self, user_key: str, filename: str, data: bytes) -> str:
        """Speichert Datei im lokalen Dateisystem."""
        now = datetime.now()
        rel_dir = Path(user_key) / str(now.year) / f"{now.month:02d}"
        abs_dir = settings.DOCUMENTS_DIR / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)

        # Unique filename to avoid collisions
        ts = now.strftime("%H%M%S")
        target = abs_dir / f"{ts}_{filename}"
        counter = 0
        while target.exists():
            counter += 1
            target = abs_dir / f"{ts}_{counter}_{filename}"

        target.write_bytes(data)
        rel_path = str(rel_dir / target.name)
        logger.info("Datei lokal gespeichert: %s (%d Bytes)", rel_path, len(data))
        return rel_path

    async def _save_gdrive(self, user_key: str, filename: str, data: bytes) -> str:
        """Speichert Datei via Google Drive Service."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)

        try:
            folder_id = await self._drive.get_or_create_document_folder(user_key, "documents")
            result = await self._drive.upload_file(user_key, tmp_path, folder_id)
            if result and result.get("id"):
                logger.info("Datei in Drive gespeichert: %s", result["id"])
                return f"gdrive:{result['id']}"
            raise RuntimeError("Drive-Upload gab keine ID zurueck")
        finally:
            tmp_path.unlink(missing_ok=True)

    async def read(self, file_path: str) -> Optional[bytes]:
        """Liest Datei aus dem Storage-Backend."""
        if file_path.startswith("gdrive:"):
            return None  # Drive-Download via Drive-Service (separate Logik)
        abs_path = settings.DOCUMENTS_DIR / file_path
        if abs_path.exists():
            return abs_path.read_bytes()
        return None

    async def delete(self, file_path: str) -> bool:
        """Loescht Datei aus dem Storage-Backend."""
        if file_path.startswith("gdrive:"):
            return False  # Drive-Delete via Drive-Service
        abs_path = settings.DOCUMENTS_DIR / file_path
        if abs_path.exists():
            abs_path.unlink()
            logger.info("Datei geloescht: %s", file_path)
            return True
        return False
