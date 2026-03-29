"""
Email Service: Gmail-Integration via Google OAuth2.
Nutzt dieselben Google Credentials wie CalendarService und DriveService.
Scopes: gmail.readonly + gmail.compose (kein Vollzugriff).
Token-Dateien: data/gmail_token_{user_key}.json
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
import base64
from email.utils import parseaddr
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from google.auth.exceptions import TransportError
from config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


class EmailService:
    """
    Gmail-Integration mit per-User OAuth2.

    Tokens werden in ``data/gmail_token_{user_key}.json`` gespeichert.
    Nutzt dieselbe google_credentials.json wie Calendar und Drive.

    Verwendung::

        email_service = EmailService()
        await email_service.initialize()

        url = email_service.get_auth_url("taake")
        ok = await email_service.exchange_code("taake", code)
        emails = await email_service.get_inbox("taake")
    """

    def __init__(self):
        self._credentials: dict = {}  # user_key → google.oauth2.credentials.Credentials
        self._pending_flows: dict = {}  # user_key → Flow

    # ------------------------------------------------------------------
    # Initialisierung
    # ------------------------------------------------------------------

    async def initialize(self):
        """Lädt gespeicherte Gmail-Tokens für alle konfigurierten User."""
        for user_key in settings.get_bot_configs():
            token_path = self._get_token_path(user_key)
            if token_path.exists():
                try:
                    self._load_credentials(user_key, token_path)
                    logger.info(f"Gmail-Token geladen für: {user_key}")
                except Exception as e:
                    logger.warning(f"Gmail-Token für {user_key} ungültig: {e}")

    def _get_token_path(self, user_key: str) -> Path:
        return Path(settings.BASE_DIR / "data" / f"gmail_token_{user_key}.json")

    def _load_credentials(self, user_key: str, token_path: Path):
        from google.oauth2.credentials import Credentials

        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        self._credentials[user_key] = creds

    def _save_token(self, user_key: str):
        token_path = self._get_token_path(user_key)
        creds = self._credentials[user_key]
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    def _get_service(self, user_key: str):
        """Gibt einen autentifizierten Gmail API-Client zurück."""
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = self._credentials.get(user_key)
        if not creds:
            raise ValueError(f"Gmail nicht verbunden für: {user_key}")

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self._save_token(user_key)

        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    # ------------------------------------------------------------------
    # OAuth2-Flow
    # ------------------------------------------------------------------

    def get_auth_url(self, user_key: str) -> str:
        """
        Startet den OAuth2-Flow und gibt die Autorisierungs-URL zurück.
        User muss URL öffnen, Code eingeben und via exchange_code() übermitteln.
        """
        from google_auth_oauthlib.flow import Flow

        if not settings.GOOGLE_CREDENTIALS_PATH.exists():
            raise FileNotFoundError(f"Google Credentials nicht gefunden: {settings.GOOGLE_CREDENTIALS_PATH}")

        flow = Flow.from_client_secrets_file(
            str(settings.GOOGLE_CREDENTIALS_PATH),
            scopes=SCOPES,
            redirect_uri="urn:ietf:wg:oauth:2.0:oob",
        )
        auth_url, _ = flow.authorization_url(prompt="consent")
        if user_key in self._pending_flows:
            logger.warning("Bestehender OAuth-Flow für %s wird ersetzt.", user_key)
        self._pending_flows[user_key] = flow
        logger.info(f"Gmail OAuth-Flow gestartet für: {user_key}")
        return auth_url

    async def exchange_code(self, user_key: str, code: str) -> bool:
        """Tauscht den OAuth-Code gegen ein Token aus und speichert es."""
        flow = self._pending_flows.get(user_key)
        if not flow:
            logger.error(f"Kein aktiver Gmail OAuth-Flow für: {user_key}")
            return False
        try:
            flow.fetch_token(code=code)
            self._credentials[user_key] = flow.credentials
            self._save_token(user_key)
            del self._pending_flows[user_key]
            logger.info(f"Gmail erfolgreich verbunden für: {user_key}")
            return True
        except Exception as e:
            logger.error(f"Gmail Code-Exchange fehlgeschlagen für {user_key}: {e}")
            return False

    def is_connected(self, user_key: str) -> bool:
        """Gibt zurück ob Gmail für diesen User verbunden ist."""
        creds = self._credentials.get(user_key)
        return creds is not None and (not creds.expired or bool(creds.refresh_token))

    # ------------------------------------------------------------------
    # Inbox & Nachrichten
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TransportError, OSError, ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def get_inbox(self, user_key: str, limit: int = 10, unread_only: bool = True) -> list[dict]:
        """
        Gibt die letzten E-Mails aus dem Posteingang zurück.

        Returns:
            Liste von Dicts mit: id, subject, from, date, snippet, is_unread
        """
        try:
            service = self._get_service(user_key)
            query = "in:inbox"
            if unread_only:
                query += " is:unread"

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, lambda: service.users().messages().list(userId="me", q=query, maxResults=limit).execute()
            )

            messages = result.get("messages", [])
            emails = []
            for msg_ref in messages:
                try:
                    msg = await loop.run_in_executor(
                        None,
                        lambda mid=msg_ref["id"]: (
                            service.users()
                            .messages()
                            .get(
                                userId="me",
                                id=mid,
                                format="metadata",
                                metadataHeaders=["Subject", "From", "Date"],
                            )
                            .execute()
                        ),
                    )
                    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                    emails.append(
                        {
                            "id": msg["id"],
                            "subject": headers.get("Subject", "(Kein Betreff)"),
                            "from": headers.get("From", "Unbekannt"),
                            "date": headers.get("Date", ""),
                            "snippet": msg.get("snippet", ""),
                            "is_unread": "UNREAD" in msg.get("labelIds", []),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Mail-Details konnten nicht geladen werden: {e}")
            return emails
        except ValueError:
            return []
        except Exception as e:
            logger.error(f"Gmail get_inbox Fehler für {user_key}: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TransportError, OSError, ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def get_email(self, user_key: str, email_id: str) -> Optional[dict]:
        """
        Ruft eine einzelne E-Mail vollständig ab (inkl. Body).

        Returns:
            Dict mit id, subject, from, date, body (Plaintext) oder None bei Fehler.
        """
        try:
            service = self._get_service(user_key)
            loop = asyncio.get_running_loop()
            msg = await loop.run_in_executor(
                None, lambda: service.users().messages().get(userId="me", id=email_id, format="full").execute()
            )

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

            body = self._extract_body(msg.get("payload", {}))

            return {
                "id": msg["id"],
                "subject": headers.get("Subject", "(Kein Betreff)"),
                "from": headers.get("From", "Unbekannt"),
                "to": headers.get("To", ""),
                "date": headers.get("Date", ""),
                "body": body,
                "snippet": msg.get("snippet", ""),
            }
        except ValueError:
            return None
        except Exception as e:
            logger.error(f"Gmail get_email Fehler: {e}")
            return None

    def _extract_body(self, payload: dict) -> str:
        """Extrahiert den Plaintext-Body aus einer Gmail-Nachricht."""
        mime_type = payload.get("mimeType", "")
        body_data = payload.get("body", {}).get("data", "")

        if body_data and "text/plain" in mime_type:
            return base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")

        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

        # Fallback: HTML-Parts durchsuchen
        for part in payload.get("parts", []):
            result = self._extract_body(part)
            if result:
                return result

        return ""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TransportError, OSError, ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def get_unread_count(self, user_key: str) -> int:
        """Gibt die Anzahl ungelesener Mails im Posteingang zurück."""
        if not self.is_connected(user_key):
            return 0
        try:
            service = self._get_service(user_key)
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: service.users().messages().list(userId="me", q="in:inbox is:unread", maxResults=1).execute(),
            )
            return result.get("resultSizeEstimate", 0)
        except Exception as e:
            logger.error(f"Gmail unread_count Fehler für {user_key}: {e}")
            return 0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TransportError, OSError, ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def mark_read(self, user_key: str, email_id: str) -> bool:
        """Markiert eine E-Mail als gelesen."""
        try:
            service = self._get_service(user_key)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: (
                    service.users()
                    .messages()
                    .modify(
                        userId="me",
                        id=email_id,
                        body={"removeLabelIds": ["UNREAD"]},
                    )
                    .execute()
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Gmail mark_read Fehler: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TransportError, OSError, ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def send_draft(self, user_key: str, to: str, subject: str, body: str) -> Optional[dict]:
        """
        Erstellt einen E-Mail-Entwurf (kein direktes Senden — bleibt in Drafts).

        Returns:
            Dict mit draft_id und link, oder None bei Fehler.
        """
        try:
            service = self._get_service(user_key)
            from email.mime.text import MIMEText

            message = MIMEText(body, "plain", "utf-8")
            message["to"] = to
            message["subject"] = subject

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            loop = asyncio.get_running_loop()
            draft = await loop.run_in_executor(
                None,
                lambda: (
                    service.users()
                    .drafts()
                    .create(
                        userId="me",
                        body={"message": {"raw": raw}},
                    )
                    .execute()
                ),
            )

            draft_id = draft.get("id", "")
            logger.info(f"Gmail-Entwurf erstellt für {user_key}: {draft_id}")
            return {
                "draft_id": draft_id,
                "to": to,
                "subject": subject,
            }
        except ValueError:
            return None
        except Exception as e:
            logger.error(f"Gmail send_draft Fehler: {e}")
            return None

    # ------------------------------------------------------------------
    # KI-gestützte Aktions-Extraktion
    # ------------------------------------------------------------------

    async def extract_actions(self, email_data: dict, ai_service) -> dict:
        """
        Analysiert eine E-Mail mit KI und extrahiert Aufgaben, Termine und Fristen.

        Args:
            email_data: Vollständige Mail (von get_email())
            ai_service: AIService-Instanz

        Returns:
            Dict mit: tasks (list[str]), events (list[str]), reminders (list[str])
        """
        subject = email_data.get("subject", "")
        sender = email_data.get("from", "")
        body = email_data.get("body", "")[:2000]  # Max 2000 Zeichen

        prompt = f"""Analysiere diese E-Mail und extrahiere Aufgaben, Termine und Fristen.
Antworte NUR mit JSON.

Von: {sender}
Betreff: {subject}
Inhalt:
{body}

Antworte mit diesem Format:
{{
  "tasks": ["Aufgabe 1", "Aufgabe 2"],
  "events": ["Termin mit Datum: ...", "Meeting am ..."],
  "reminders": ["Frist: Bericht bis ...", "Deadline: ..."],
  "summary": "Kurze Zusammenfassung der Mail in 1-2 Sätzen"
}}

Wenn keine Aufgaben/Termine/Fristen gefunden, leere Listen verwenden."""

        try:
            import json

            response = await ai_service._complete(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"Email action extraction Fehler: {e}")
            return {"tasks": [], "events": [], "reminders": [], "summary": ""}

    # ------------------------------------------------------------------
    # Formatierung
    # ------------------------------------------------------------------

    @staticmethod
    def format_inbox(emails: list[dict]) -> str:
        """Formatiert die Inbox als Telegram-Markdown."""
        if not emails:
            return "📭 Keine ungelesenen E-Mails."

        lines = [f"📬 *Posteingang* ({len(emails)} Nachrichten)\n"]
        for i, mail in enumerate(emails, 1):
            icon = "📧" if mail.get("is_unread") else "📨"
            subject = mail.get("subject", "(kein Betreff)")[:60]
            raw_from = mail.get("from", "")
            name, addr = parseaddr(raw_from)
            sender = (name or addr or "Unbekannt")[:30]
            snippet = mail.get("snippet", "")[:80]
            lines.append(f"{icon} *{i}. {subject}*\n   Von: {sender}\n   _{snippet}_\n")

        return "\n".join(lines)

    @staticmethod
    def format_email(email_data: dict) -> str:
        """Formatiert eine einzelne E-Mail als Telegram-Markdown."""
        subject = email_data.get("subject", "(kein Betreff)")
        sender = email_data.get("from", "Unbekannt")
        date = email_data.get("date", "")
        body = email_data.get("body", email_data.get("snippet", ""))[:1500]

        return f"📧 *{subject}*\nVon: {sender}\nDatum: {date}\n\n{body}"
