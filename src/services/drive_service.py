"""
Google Drive Service: OAuth2-Authentifizierung und Datei-Operationen.
Jeder User hat eigene OAuth-Credentials (per-User token files).
Modelliert nach dem Muster von calendar_service.py.
"""

import logging
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# MIME-Type-Zuordnung für bekannte Office-Formate
_MIME_TYPES: dict[str, str] = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".txt": "text/plain",
}

# Icons für verschiedene MIME-Typen in Telegram-Nachrichten
_MIME_ICONS: dict[str, str] = {
    "application/vnd.google-apps.folder": "🗂",
    "application/vnd.google-apps.document": "📄",
    "application/vnd.google-apps.spreadsheet": "📊",
    "application/vnd.google-apps.presentation": "📄",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "📊",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "📄",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "📄",
    "application/vnd.ms-excel": "📊",
    "application/vnd.ms-powerpoint": "📄",
    "application/msword": "📄",
    "text/plain": "📝",
    "text/csv": "📝",
    "application/pdf": "📄",
}


class DriveService:
    """
    Google Drive Service mit per-User OAuth2.

    Tokens werden in ``data/google_drive_token_{user_key}.json`` gespeichert.
    Unterstützte Operationen: Dateien auflisten, hochladen, löschen.

    Verwendung::

        drive = DriveService()
        await drive.initialize()

        # OAuth verbinden (einmalig pro User)
        url = await drive.get_auth_url("taake")
        # … User besucht URL und gibt Code ein …
        ok = await drive.exchange_code("taake", code)

        # Dateien auflisten
        files = await drive.list_files("taake")

        # Datei hochladen
        result = await drive.upload_file("taake", Path("/tmp/report.xlsx"))
    """

    def __init__(self):
        self._credentials: dict = {}       # user_key → google.oauth2.credentials.Credentials
        self._pending_flows: dict = {}     # user_key → google_auth_oauthlib.flow.Flow

    # ------------------------------------------------------------------
    # Initialisierung
    # ------------------------------------------------------------------

    async def initialize(self):
        """
        Lädt bestehende Drive-Tokens beim Anwendungsstart.

        Iteriert über alle konfigurierten Bots und versucht,
        vorhandene Token-Dateien einzulesen.
        """
        bot_configs = settings.get_bot_configs()
        for user_key in bot_configs:
            token_path = self._get_token_path(user_key)
            if token_path.exists():
                try:
                    self._load_credentials(user_key, token_path)
                    logger.info("Google Drive Token für '%s' geladen.", user_key)
                except Exception as e:
                    logger.warning(
                        "Drive-Token für '%s' konnte nicht geladen werden: %s",
                        user_key, e,
                    )

    # ------------------------------------------------------------------
    # Interne Hilfsmethoden
    # ------------------------------------------------------------------

    def _get_token_path(self, user_key: str) -> Path:
        """Gibt den Pfad zur Token-Datei für einen User zurück."""
        return Path(settings.BASE_DIR / "data" / f"google_drive_token_{user_key}.json")

    def _load_credentials(self, user_key: str, token_path: Path):
        """Liest Credentials aus einer JSON-Token-Datei."""
        from google.oauth2.credentials import Credentials

        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        self._credentials[user_key] = creds

    def _save_token(self, user_key: str, creds):
        """Speichert Credentials als JSON-Datei auf Disk."""
        token_path = self._get_token_path(user_key)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        logger.debug("Drive-Token für '%s' gespeichert: %s", user_key, token_path)

    def _get_service(self, user_key: str):
        """
        Erstellt einen authentifizierten Google Drive API-Service (v3).

        Erneuert den Access-Token automatisch, falls er abgelaufen ist.

        Raises:
            ValueError: Wenn für ``user_key`` keine Credentials vorhanden sind.
        """
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request

        creds = self._credentials.get(user_key)
        if not creds:
            raise ValueError(
                f"Keine Drive-Credentials für '{user_key}'. "
                "Bitte Google Drive verbinden."
            )

        # Access-Token erneuern falls abgelaufen
        if creds.expired and creds.refresh_token:
            logger.debug("Drive-Token für '%s' abgelaufen – erneuere.", user_key)
            creds.refresh(Request())
            self._save_token(user_key, creds)

        return build("drive", "v3", credentials=creds, cache_discovery=False)

    # ------------------------------------------------------------------
    # OAuth2-Flow
    # ------------------------------------------------------------------

    async def get_auth_url(self, user_key: str) -> str:
        """
        Erzeugt eine OAuth2-Autorisierungs-URL für den Desktop-Flow (OOB).

        Der erzeugte Flow wird in ``_pending_flows`` gespeichert und kann
        mit ``exchange_code`` abgeschlossen werden.

        Args:
            user_key: Schlüssel des Users (z.B. ``"taake"``).

        Returns:
            OAuth2-Autorisierungs-URL als String.

        Raises:
            FileNotFoundError: Wenn ``settings.GOOGLE_CREDENTIALS_PATH`` nicht existiert.
        """
        from google_auth_oauthlib.flow import Flow

        if not settings.GOOGLE_CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"Google Credentials nicht gefunden: {settings.GOOGLE_CREDENTIALS_PATH}\n"
                "Bitte credentials.json von der Google Cloud Console in config/ ablegen."
            )

        flow = Flow.from_client_secrets_file(
            str(settings.GOOGLE_CREDENTIALS_PATH),
            scopes=SCOPES,
            redirect_uri="urn:ietf:wg:oauth:2.0:oob",  # Desktop / OOB-Flow
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )

        self._pending_flows[user_key] = flow
        logger.debug("Drive Auth-URL für '%s' erstellt.", user_key)
        return auth_url

    async def exchange_code(self, user_key: str, code: str) -> bool:
        """
        Tauscht den vom User eingegebenen Auth-Code gegen einen Access-Token aus.

        Args:
            user_key: Schlüssel des Users.
            code: Autorisierungscode aus dem OAuth2-Flow.

        Returns:
            True bei Erfolg, False bei Fehler.
        """
        try:
            if user_key not in self._pending_flows:
                raise ValueError(
                    "Kein ausstehender Drive-Auth-Flow. "
                    "Bitte erneut /drive_connect ausführen."
                )

            flow = self._pending_flows[user_key]
            flow.fetch_token(code=code)

            creds = flow.credentials
            self._credentials[user_key] = creds
            self._save_token(user_key, creds)

            del self._pending_flows[user_key]
            logger.info("Google Drive für '%s' erfolgreich verbunden.", user_key)
            return True

        except Exception as e:
            logger.error("Drive Token-Exchange-Fehler für '%s': %s", user_key, e)
            return False

    def is_connected(self, user_key: str) -> bool:
        """Gibt True zurück, wenn für den User gültige Drive-Credentials vorliegen."""
        return user_key in self._credentials and self._credentials[user_key] is not None

    # ------------------------------------------------------------------
    # Drive-Operationen
    # ------------------------------------------------------------------

    async def list_files(
        self,
        user_key: str,
        query: str = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Listet Dateien im Google Drive des Users auf.

        Args:
            user_key: Schlüssel des Users.
            query: Optionaler Suchbegriff (Dateiname enthält diesen String).
            limit: Maximale Anzahl zurückgegebener Dateien (Standard: 10).

        Returns:
            Liste von Datei-Dicts mit den Feldern
            ``id``, ``name``, ``mimeType``, ``modifiedTime``, ``size``, ``webViewLink``.

        Raises:
            ValueError: Wenn Drive nicht verbunden ist.
        """
        try:
            service = self._get_service(user_key)

            list_kwargs: dict = {
                "pageSize": limit,
                "fields": "files(id,name,mimeType,modifiedTime,size,webViewLink)",
                "orderBy": "modifiedTime desc",
            }

            if query:
                list_kwargs["q"] = f"name contains '{query}'"

            result = service.files().list(**list_kwargs).execute()
            files = result.get("files", [])
            logger.debug(
                "Drive list_files für '%s': %d Dateien gefunden.", user_key, len(files)
            )
            return files

        except ValueError:
            raise  # Nicht-verbunden-Fehler weiterwerfen
        except Exception as e:
            logger.error("Drive list_files Fehler für '%s': %s", user_key, e)
            raise

    async def upload_file(
        self,
        user_key: str,
        file_path: Path,
        folder_id: str = None,
    ) -> Optional[dict]:
        """
        Lädt eine lokale Datei in Google Drive hoch.

        Der MIME-Typ wird anhand der Dateiendung ermittelt. Unbekannte
        Endungen erhalten den Fallback ``application/octet-stream``.

        Args:
            user_key: Schlüssel des Users.
            file_path: Absoluter Pfad zur hochzuladenden Datei.
            folder_id: Optionale Drive-Ordner-ID (``parents``-Feld).

        Returns:
            Dict mit ``id`` und ``webViewLink`` der erstellten Datei,
            oder None bei Fehler.

        Raises:
            ValueError: Wenn Drive nicht verbunden ist.
        """
        try:
            from googleapiclient.http import MediaFileUpload

            service = self._get_service(user_key)

            # MIME-Typ anhand Dateiendung bestimmen
            suffix = file_path.suffix.lower()
            mime_type = _MIME_TYPES.get(suffix, "application/octet-stream")

            # Datei-Metadaten
            file_metadata: dict = {"name": file_path.name}
            if folder_id:
                file_metadata["parents"] = [folder_id]

            media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)

            created = (
                service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id,name,webViewLink,mimeType",
                )
                .execute()
            )

            logger.info(
                "Drive upload für '%s': '%s' hochgeladen (id=%s).",
                user_key, file_path.name, created.get("id"),
            )
            return created

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "Drive upload_file Fehler für '%s' (%s): %s",
                user_key, file_path.name, e,
            )
            return None

    async def delete_file(self, user_key: str, file_id: str) -> bool:
        """
        Löscht eine Datei aus Google Drive.

        Args:
            user_key: Schlüssel des Users.
            file_id: Drive-Datei-ID der zu löschenden Datei.

        Returns:
            True bei Erfolg, False bei Fehler.
        """
        try:
            service = self._get_service(user_key)
            service.files().delete(fileId=file_id).execute()
            logger.info("Drive delete für '%s': Datei '%s' gelöscht.", user_key, file_id)
            return True
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "Drive delete_file Fehler für '%s' (id=%s): %s",
                user_key, file_id, e,
            )
            return False

    # ------------------------------------------------------------------
    # Formatierung
    # ------------------------------------------------------------------

    async def create_folder(
        self, user_key: str, name: str, parent_id: Optional[str] = None
    ) -> Optional[dict]:
        """
        Erstellt einen Ordner in Google Drive.

        Returns:
            Dict mit id und name, oder None bei Fehler.
        """
        try:
            service = self._get_service(user_key)
            metadata: dict = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                metadata["parents"] = [parent_id]
            folder = service.files().create(
                body=metadata, fields="id,name,webViewLink"
            ).execute()
            logger.info("Drive Ordner '%s' erstellt für '%s': %s", name, user_key, folder.get("id"))
            return folder
        except ValueError:
            raise
        except Exception as e:
            logger.error("Drive create_folder Fehler für '%s': %s", user_key, e)
            return None

    async def search_files(
        self, user_key: str, query: str, mime_type: Optional[str] = None, limit: int = 10
    ) -> list[dict]:
        """
        Sucht Dateien in Google Drive nach Name und/oder MIME-Typ.

        Args:
            query: Suchbegriff (Dateiname enthält diesen String)
            mime_type: Optionaler MIME-Type-Filter
            limit: Maximale Anzahl Ergebnisse

        Returns:
            Liste von Datei-Dicts.
        """
        try:
            service = self._get_service(user_key)
            q_parts = [f"name contains '{query}'", "trashed = false"]
            if mime_type:
                q_parts.append(f"mimeType = '{mime_type}'")
            result = service.files().list(
                q=" and ".join(q_parts),
                pageSize=limit,
                fields="files(id,name,mimeType,modifiedTime,size,webViewLink)",
                orderBy="modifiedTime desc",
            ).execute()
            return result.get("files", [])
        except ValueError:
            raise
        except Exception as e:
            logger.error("Drive search_files Fehler für '%s': %s", user_key, e)
            return []

    async def get_or_create_assistant_folder(self, user_key: str) -> Optional[str]:
        """
        Gibt die ID des 'Personal Assistant' Ordners zurück.
        Erstellt ihn wenn er noch nicht existiert.

        Returns:
            Ordner-ID oder None bei Fehler.
        """
        folder_name = "Personal Assistant"
        try:
            service = self._get_service(user_key)
            result = service.files().list(
                q=f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
                fields="files(id,name)",
                pageSize=1,
            ).execute()
            folders = result.get("files", [])
            if folders:
                return folders[0]["id"]
            # Ordner erstellen
            folder = await self.create_folder(user_key, folder_name)
            return folder["id"] if folder else None
        except ValueError:
            raise
        except Exception as e:
            logger.error("Drive get_or_create_assistant_folder Fehler für '%s': %s", user_key, e)
            return None

    async def download_file(self, user_key: str, file_id: str) -> Optional[bytes]:
        """
        Lädt den Inhalt einer Drive-Datei herunter.

        Returns:
            Dateiinhalt als bytes, oder None bei Fehler.
        """
        try:
            from googleapiclient.http import MediaIoBaseDownload
            import io

            service = self._get_service(user_key)
            request = service.files().get_media(fileId=file_id)
            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buf.getvalue()
        except ValueError:
            raise
        except Exception as e:
            logger.error("Drive download_file Fehler für '%s' (id=%s): %s", user_key, file_id, e)
            return None

    async def get_or_create_document_folder(
        self, user_key: str, doc_type: str
    ) -> Optional[str]:
        """
        Gibt die Ordner-ID für /Dokumente/<Typ>/ zurück, erstellt bei Bedarf.

        Hierarchie:
          DRIVE_DOCUMENTS_FOLDER_ID (oder Personal Assistant) → Typ-Unterordner

        Args:
            user_key: Schlüssel des Users.
            doc_type: Dokumenttyp (lowercase, z.B. "rechnung"). Wird via FOLDER_MAP aufgelöst.

        Returns:
            Ordner-ID oder None bei Fehler.
        """
        from src.workflows.document_scan_workflow import FOLDER_MAP

        subfolder_name = FOLDER_MAP.get(doc_type.lower(), "Sonstiges")

        try:
            service = self._get_service(user_key)

            # Basis-Ordner bestimmen
            base_folder_id = settings.DRIVE_DOCUMENTS_FOLDER_ID or None
            if not base_folder_id:
                base_folder_id = await self.get_or_create_assistant_folder(user_key)

            if not base_folder_id:
                return None

            # Unterordner suchen
            q = (
                f"name = '{subfolder_name}' "
                f"and mimeType = 'application/vnd.google-apps.folder' "
                f"and '{base_folder_id}' in parents "
                f"and trashed = false"
            )
            result = service.files().list(
                q=q, fields="files(id,name)", pageSize=1
            ).execute()
            folders = result.get("files", [])
            if folders:
                return folders[0]["id"]

            # Unterordner erstellen
            folder = await self.create_folder(user_key, subfolder_name, parent_id=base_folder_id)
            if folder:
                logger.info(
                    "Drive: Dokumenten-Ordner '%s' erstellt für '%s'.", subfolder_name, user_key
                )
                return folder["id"]
            return None
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "Drive get_or_create_document_folder Fehler für '%s': %s", user_key, e
            )
            return None

    @staticmethod
    def format_file_list(files: list[dict]) -> str:
        """
        Formatiert eine Liste von Drive-Datei-Dicts als Telegram-Nachricht.

        Je nach MIME-Typ wird ein passendes Icon vorangestellt:
        - 📄  Dokument / Präsentation / PDF
        - 📊  Tabelle / Spreadsheet
        - 📝  Textdatei / CSV
        - 🗂  Ordner
        - 📎  Sonstige Dateien

        Args:
            files: Liste von Datei-Dicts (wie von ``list_files`` zurückgegeben).

        Returns:
            Formatierter Markdown-String oder Hinweis bei leerer Liste.
        """
        if not files:
            return "Keine Dateien in Google Drive gefunden."

        lines = ["*Dateien in Google Drive:*", ""]

        for file in files:
            name = file.get("name", "Unbekannt")
            mime = file.get("mimeType", "")
            modified = file.get("modifiedTime", "")
            link = file.get("webViewLink", "")

            # Icon bestimmen
            icon = _MIME_ICONS.get(mime, "📎")

            # Datum kürzen (ISO 8601 → nur Datum)
            date_str = ""
            if modified:
                date_str = modified[:10]  # "2024-03-15T10:30:00.000Z" → "2024-03-15"

            # Zeile zusammenbauen
            if link:
                file_line = f"{icon} [{name}]({link})"
            else:
                file_line = f"{icon} {name}"

            if date_str:
                file_line += f"  _(geändert: {date_str})_"

            lines.append(file_line)

        return "\n".join(lines)
