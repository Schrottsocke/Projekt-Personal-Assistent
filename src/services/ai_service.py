"""
AI Service: OpenRouter-Integration mit Intent-Erkennung.
Entscheidet ob Kalender, Notiz, Erinnerung oder normaler Chat gemeint ist.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import pytz
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import settings

logger = logging.getLogger(__name__)

# Intent-Typen
INTENT_CALENDAR_READ = "calendar_read"
INTENT_CALENDAR_CREATE = "calendar_create"
INTENT_NOTE_CREATE = "note_create"
INTENT_REMINDER_CREATE = "reminder_create"
INTENT_CHAT = "chat"
INTENT_BRIEFING = "briefing"


class AIService:
    """
    Zentraler AI-Service für alle Bot-Interaktionen.
    Verwendet OpenRouter mit Fallback-Modell.
    """

    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )
        self._model = settings.AI_MODEL
        self._fallback_model = settings.AI_MODEL_FALLBACK
        self.tz = pytz.timezone(settings.TIMEZONE)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
    )
    async def _complete(self, messages: list[dict], model: str = None, json_mode: bool = False) -> str:
        """Führt einen API-Call durch mit automatischem Fallback."""
        model = model or self._model

        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            if model != self._fallback_model:
                logger.warning(f"Primär-Modell fehlgeschlagen ({e}), wechsle zu Fallback...")
                return await self._complete(messages, model=self._fallback_model, json_mode=json_mode)
            raise

    async def process_message(
        self,
        message: str,
        user_key: str,
        chat_id: int,
        bot,
    ) -> str:
        """
        Hauptfunktion: Verarbeitet eine Nutzernachricht.
        Erkennt Intent und delegiert an den passenden Service.
        """
        # 1. Intent erkennen
        intent, extracted = await self._detect_intent(message, user_key)
        logger.info(f"Intent für '{message[:40]}': {intent}")

        # 2. Je nach Intent handeln
        if intent == INTENT_CALENDAR_READ:
            return await self._handle_calendar_read(bot, user_key)

        elif intent == INTENT_CALENDAR_CREATE:
            return await self._handle_calendar_create(bot, user_key, extracted, chat_id)

        elif intent == INTENT_NOTE_CREATE:
            return await self._handle_note_create(bot, user_key, extracted, chat_id)

        elif intent == INTENT_REMINDER_CREATE:
            return await self._handle_reminder_create(bot, user_key, chat_id, extracted)

        else:
            # Normaler Chat mit Kontext-Gedächtnis
            return await self._handle_chat(message, user_key, bot)

    async def _detect_intent(self, message: str, user_key: str) -> tuple[str, dict]:
        """
        Erkennt den Intent einer Nachricht via KI.
        Gibt (intent_type, extracted_data) zurück.
        """
        now = datetime.now(self.tz)
        prompt = f"""Du bist ein Intent-Classifier. Analysiere die folgende Nachricht und bestimme den Intent.

Aktuelle Zeit: {now.strftime('%A, %d.%m.%Y %H:%M')} (Zeitzone: {settings.TIMEZONE})

Nachricht: "{message}"

Mögliche Intents:
- calendar_read: Nutzer fragt nach Terminen (z.B. "Was habe ich heute?", "Zeig meine Termine")
- calendar_create: Nutzer will Termin erstellen (z.B. "Zahnarzt am Montag um 10", "Meeting morgen 14 Uhr")
- note_create: Nutzer will eine Notiz speichern (z.B. "Notiz: ...", "Merkzettel für ...")
- reminder_create: Nutzer will erinnert werden (z.B. "Erinnere mich...", "In 2 Stunden...", "Morgen um 9...")
- chat: Alles andere (Fragen, Konversation, Hilfe)

Antworte NUR mit diesem JSON-Format:
{{
  "intent": "calendar_read|calendar_create|note_create|reminder_create|chat",
  "confidence": 0.0-1.0,
  "extracted": {{
    "content": "extrahierter Kerninhalt",
    "datetime_str": "falls Datum/Zeit erkannt, sonst null",
    "summary": "kurzer Titel falls Termin/Erinnerung"
  }}
}}"""

        try:
            response = await self._complete(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
            )
            data = json.loads(response)
            return data.get("intent", INTENT_CHAT), data.get("extracted", {})
        except Exception as e:
            logger.error(f"Intent-Detection-Fehler: {e}")
            return INTENT_CHAT, {}

    async def _handle_chat(self, message: str, user_key: str, bot) -> str:
        """Normaler Chat mit Kontext aus Gedächtnis."""
        # Relevante Erinnerungen suchen
        memories = await bot.memory_service.search_memories(user_key=user_key, query=message)
        memory_context = ""
        if memories:
            memory_lines = [m.get("memory", "") for m in memories if m.get("memory")]
            if memory_lines:
                memory_context = "Was du über den Nutzer weißt:\n" + "\n".join(f"- {m}" for m in memory_lines)

        # Gesprächsverlauf aus DB holen
        history = await self._get_conversation_history(user_key, limit=6)

        system_prompt = bot.get_system_prompt()
        if memory_context:
            system_prompt += f"\n\n{memory_context}"

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        response = await self._complete(messages)

        # Konversation im Gedächtnis speichern (im Hintergrund)
        try:
            await bot.memory_service.add_conversation_turn(user_key, message, response)
            await self._save_conversation_turn(user_key, "user", message)
            await self._save_conversation_turn(user_key, "assistant", response)
        except Exception as e:
            logger.warning(f"Konversation konnte nicht gespeichert werden: {e}")

        return response

    async def _handle_calendar_read(self, bot, user_key: str) -> str:
        try:
            events = await bot.calendar_service.get_upcoming_events(user_key=user_key, days=7)
            if not events:
                return "📅 Du hast keine Termine in den nächsten 7 Tagen."

            now = datetime.now(self.tz)
            lines = ["📅 *Deine kommenden Termine:*\n"]
            for event in events:
                start = event.get("start", {})
                dt_str = start.get("dateTime", start.get("date", ""))
                summary = event.get("summary", "(kein Titel)")

                if "T" in dt_str:
                    dt = datetime.fromisoformat(dt_str).astimezone(self.tz)
                    date_fmt = dt.strftime("%a, %d.%m. um %H:%M Uhr")
                else:
                    dt = datetime.fromisoformat(dt_str)
                    date_fmt = dt.strftime("%a, %d.%m. (ganztägig)")

                lines.append(f"• {date_fmt}: *{summary}*")

            return "\n".join(lines)
        except Exception as e:
            return "❌ Kalender konnte nicht geladen werden. Google Calendar verbunden?"

    async def _handle_calendar_create(self, bot, user_key: str, extracted: dict, chat_id: int = None) -> str:
        try:
            result = await self.parse_calendar_event(
                text=extracted.get("content", ""),
                user_key=user_key,
                extracted_hint=extracted,
            )
            if not result:
                return "❓ Konnte den Termin nicht erkennen. Bitte genauer angeben."

            from src.services.proposal_service import TYPE_CALENDAR_CREATE
            await bot.proposal_service.create_proposal(
                user_key=user_key,
                proposal_type=TYPE_CALENDAR_CREATE,
                title=result["summary"],
                payload={
                    "summary": result["summary"],
                    "start": result["start"].isoformat(),
                    "end": result["end"].isoformat(),
                    "description": result.get("description", ""),
                },
                created_by="ai",
                chat_id=str(chat_id),
            )
            return ""  # Proposal-Nachricht wurde bereits direkt gesendet
        except Exception as e:
            logger.error(f"Calendar-Create-Fehler: {e}")
            return "❌ Vorschlag konnte nicht erstellt werden."

    async def _handle_note_create(self, bot, user_key: str, extracted: dict, chat_id: int = None) -> str:
        try:
            content = extracted.get("content", "")
            if not content:
                return "❓ Was soll ich notieren?"

            from src.services.proposal_service import TYPE_NOTE_CREATE
            await bot.proposal_service.create_proposal(
                user_key=user_key,
                proposal_type=TYPE_NOTE_CREATE,
                title=f"Notiz: {content[:60]}{'...' if len(content) > 60 else ''}",
                payload={"content": content, "is_shared": False},
                created_by="ai",
                chat_id=str(chat_id),
            )
            return ""
        except Exception as e:
            logger.error(f"Note-Create-Fehler: {e}")
            return "❌ Vorschlag konnte nicht erstellt werden."

    async def _handle_reminder_create(
        self, bot, user_key: str, chat_id: int, extracted: dict
    ) -> str:
        try:
            result = await self.parse_reminder(
                text=extracted.get("content", ""),
                user_key=user_key,
                extracted_hint=extracted,
            )
            if not result:
                return "❓ Konnte Datum/Uhrzeit nicht erkennen. Beispiel: _'Morgen um 10: Zahnarzt'_"

            from src.services.proposal_service import TYPE_REMINDER_CREATE
            time_str = result["remind_at"].strftime("%d.%m.%Y %H:%M Uhr")
            await bot.proposal_service.create_proposal(
                user_key=user_key,
                proposal_type=TYPE_REMINDER_CREATE,
                title=result["content"],
                description=f"Fällig: {time_str}",
                payload={
                    "content": result["content"],
                    "remind_at": result["remind_at"].isoformat(),
                },
                created_by="ai",
                chat_id=str(chat_id),
            )
            return ""
        except Exception as e:
            logger.error(f"Reminder-Create-Fehler: {e}")
            return "❌ Vorschlag konnte nicht erstellt werden."

    async def parse_reminder(
        self, text: str, user_key: str, extracted_hint: dict = None
    ) -> Optional[dict]:
        """Parst eine Erinnerungsangabe in strukturierte Daten."""
        now = datetime.now(self.tz)
        prompt = f"""Analysiere diese Erinnerungs-Anfrage und extrahiere die Daten.

Aktuelle Zeit: {now.strftime('%A, %d.%m.%Y %H:%M Uhr')} ({settings.TIMEZONE})
Anfrage: "{text}"

Antworte NUR mit diesem JSON:
{{
  "content": "Was ist die Erinnerung (kurz & klar)",
  "remind_at": "ISO 8601 datetime mit Zeitzone, z.B. 2025-03-15T10:00:00+01:00",
  "success": true/false
}}

Bei "morgen" = {(now + timedelta(days=1)).strftime('%Y-%m-%d')}
Bei "übermorgen" = {(now + timedelta(days=2)).strftime('%Y-%m-%d')}
Wenn keine Uhrzeit angegeben, nutze 09:00 Uhr."""

        try:
            response = await self._complete(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
            )
            data = json.loads(response)
            if not data.get("success", False):
                return None

            remind_at = datetime.fromisoformat(data["remind_at"])
            if remind_at.tzinfo is None:
                remind_at = self.tz.localize(remind_at)

            return {"content": data["content"], "remind_at": remind_at}
        except Exception as e:
            logger.error(f"Reminder-Parse-Fehler: {e}")
            return None

    async def parse_calendar_event(
        self, text: str, user_key: str, extracted_hint: dict = None
    ) -> Optional[dict]:
        """Parst einen Termin in strukturierte Daten."""
        now = datetime.now(self.tz)
        prompt = f"""Extrahiere Termin-Daten aus diesem Text.

Aktuelle Zeit: {now.strftime('%A, %d.%m.%Y %H:%M Uhr')} ({settings.TIMEZONE})
Text: "{text}"

Antworte NUR mit diesem JSON:
{{
  "summary": "Terminbeschreibung",
  "start": "ISO 8601 datetime, z.B. 2025-03-15T10:00:00+01:00",
  "end": "ISO 8601 datetime (wenn nicht angegeben: start + 1 Stunde)",
  "description": "optionale Beschreibung",
  "success": true/false
}}"""

        try:
            response = await self._complete(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
            )
            data = json.loads(response)
            if not data.get("success", False):
                return None

            start = datetime.fromisoformat(data["start"])
            end = datetime.fromisoformat(data["end"])

            if start.tzinfo is None:
                start = self.tz.localize(start)
            if end.tzinfo is None:
                end = self.tz.localize(end)

            return {
                "summary": data["summary"],
                "start": start,
                "end": end,
                "description": data.get("description", ""),
            }
        except Exception as e:
            logger.error(f"Calendar-Parse-Fehler: {e}")
            return None

    async def generate_morning_briefing(
        self, user_key: str, name: str, events: list, reminders: list, memories: list
    ) -> str:
        """Generiert ein personalisiertes Morgen-Briefing."""
        now = datetime.now(self.tz)
        weekday = now.strftime("%A")

        events_text = "Keine Termine heute." if not events else "\n".join(
            f"- {e.get('summary', '(kein Titel)')}" for e in events
        )
        reminders_text = "Keine Erinnerungen heute." if not reminders else "\n".join(
            f"- {r['content']}" for r in reminders
        )
        memories_text = "\n".join(f"- {m.get('memory', '')}" for m in memories[:3]) or "Keine"

        prompt = f"""Du bist {name}s persönlicher Assistent.
Schreibe ein freundliches, kurzes Morgen-Briefing.

Heute: {weekday}, {now.strftime('%d.%m.%Y')}

Heutige Termine:
{events_text}

Heutige Erinnerungen:
{reminders_text}

Was du über {name} weißt:
{memories_text}

Das Briefing soll:
- Kurz und positiv sein (max 8 Sätze)
- Die wichtigsten Punkte des Tages hervorheben
- Einen motivierenden Ton haben
- Auf Deutsch sein
- Mit "Guten Morgen, {name}! ☀️" beginnen"""

        return await self._complete(
            messages=[{"role": "user", "content": prompt}]
        )

    async def _get_conversation_history(
        self, user_key: str, limit: int = 6
    ) -> list[dict]:
        """Holt den letzten Gesprächsverlauf aus der DB."""
        try:
            from src.services.database import ConversationHistory, get_db
            with get_db()() as session:
                rows = (
                    session.query(ConversationHistory)
                    .filter_by(user_key=user_key)
                    .order_by(ConversationHistory.created_at.desc())
                    .limit(limit)
                    .all()
                )
                # Umgekehrte Reihenfolge (älteste zuerst)
                return [{"role": r.role, "content": r.content} for r in reversed(rows)]
        except Exception as e:
            logger.warning(f"History-Fehler: {e}")
            return []

    async def _save_conversation_turn(self, user_key: str, role: str, content: str):
        """Speichert einen Gesprächsbeitrag in der DB."""
        try:
            from src.services.database import ConversationHistory, get_db
            with get_db()() as session:
                entry = ConversationHistory(
                    user_key=user_key, role=role, content=content
                )
                session.add(entry)
        except Exception as e:
            logger.warning(f"History-Save-Fehler: {e}")
