"""
AI Service: OpenRouter-Integration mit Intent-Erkennung.
Entscheidet ob Kalender, Notiz, Erinnerung oder normaler Chat gemeint ist.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import pytz
import httpx
from openai import AsyncOpenAI, RateLimitError, APITimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_not_exception_type, before_sleep_log

from config.settings import settings
from src.features.feature_service import get_enabled_intents, is_enabled

logger = logging.getLogger(__name__)

# Intent-Typen
INTENT_CALENDAR_READ = "calendar_read"
INTENT_CALENDAR_CREATE = "calendar_create"
INTENT_NOTE_CREATE = "note_create"
INTENT_REMINDER_CREATE = "reminder_create"
INTENT_WEB_SEARCH = "web_search"
INTENT_TASK_CREATE = "task_create"
INTENT_TASK_READ = "task_read"
INTENT_TASK_COMPLETE = "task_complete"
INTENT_TIMER_CREATE = "timer_create"
INTENT_TABLE_CREATE = "table_create"
INTENT_PRESENTATION_CREATE = "presentation_create"
INTENT_CHAT = "chat"
INTENT_BRIEFING = "briefing"
INTENT_SPOTIFY = "spotify"
INTENT_SMARTHOME = "smarthome"
INTENT_RECIPE_SEARCH = "recipe_search"
INTENT_DRIVE = "drive"
INTENT_SHOPPING_ADD = "shopping_add"
INTENT_SHOPPING_VIEW = "shopping_view"
INTENT_SHOPPING_RECIPE = "shopping_recipe"
INTENT_EMAIL_READ = "email_read"
INTENT_EMAIL_COMPOSE = "email_compose"
INTENT_MOBILITY = "mobility"
INTENT_WEATHER = "weather"


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
        self._intelligence = None  # Lazy init
        self._web_search = None   # Lazy init
        # Groq Client für Whisper (nur wenn API Key vorhanden)
        self._groq_client = (
            AsyncOpenAI(api_key=settings.GROQ_API_KEY, base_url=settings.GROQ_BASE_URL)
            if settings.GROQ_API_KEY
            else None
        )
        # NVIDIA NIM Client (Fallback – optional)
        self._nvidia_client = (
            AsyncOpenAI(
                api_key=settings.NVIDIA_API_KEY,
                base_url=settings.NVIDIA_BASE_URL,
                http_client=httpx.AsyncClient(timeout=httpx.Timeout(20.0)),
                max_retries=0,
            )
            if settings.NVIDIA_API_KEY
            else None
        )
        self._nvidia_model = settings.NVIDIA_MODEL

    async def transcribe_voice(self, audio_bytes: bytes, filename: str = "voice.ogg") -> Optional[str]:
        """
        Transkribiert eine Sprachnachricht via Groq Whisper Large v3.
        Gibt den transkribierten Text zurück, oder None bei Fehler.
        """
        if not self._groq_client:
            logger.warning("Kein GROQ_API_KEY konfiguriert – Voice-Transkription nicht verfügbar.")
            return None
        try:
            import io
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename
            response = await self._groq_client.audio.transcriptions.create(
                model=settings.WHISPER_MODEL,
                file=audio_file,
                language="de",
            )
            return response.text.strip() or None
        except Exception as e:
            logger.error(f"Whisper-Transkriptions-Fehler: {e}")
            return None

    def _get_system_prompt(self, user_key: str = None) -> str:
        """Gibt den System-Prompt zurück (personalisiert wenn user_key gesetzt)."""
        from config.settings import settings
        base_prompt = settings.get_system_prompt(user_key)
        now = datetime.now(self.tz)
        time_context = f"\n\nAktuelles Datum und Uhrzeit: {now.strftime('%A, %d. %B %Y, %H:%M Uhr')} ({settings.TIMEZONE})"
        return base_prompt + time_context

    def _get_intelligence_service(self):
        """Lazy-init des Intelligence Service."""
        if self._intelligence is None:
            from services.intelligence_service import IntelligenceService
            self._intelligence = IntelligenceService(self)
        return self._intelligence

    def _get_web_search_service(self):
        """Lazy-init des Web Search Service."""
        if self._web_search is None:
            from services.web_search_service import WebSearchService
            self._web_search = WebSearchService(self)
        return self._web_search

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        retry=retry_if_not_exception_type((RateLimitError, APITimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _complete(self, messages: list[dict], model: str = None, json_mode: bool = False, _start: int = 0) -> str:
        """Führt einen API-Call durch mit linearem Fallback (kein rekursiver Aufruf)."""
        models = [self._model, self._fallback_model]
        kwargs_base = {
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
        }
        if json_mode:
            kwargs_base["response_format"] = {"type": "json_object"}

        last_exc: Exception = RuntimeError("Alle AI-Modelle fehlgeschlagen")
        for m in models[_start:]:
            try:
                if m == "nvidia_fallback" and self._nvidia_client:
                    kw = {k: v for k, v in kwargs_base.items() if k != "response_format"}
                    kw["model"] = self._nvidia_model
                    response = await self._nvidia_client.chat.completions.create(**kw)
                else:
                    response = await self._client.chat.completions.create(model=m, **kwargs_base)
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"Modell {m} fehlgeschlagen: {e}")
                last_exc = e
        raise last_exc

    def _feature_enabled(self, intent: str, user_key: str) -> bool:
        """Prüft ob das Feature für diesen Intent aktiv ist."""
        from src.features.catalog import INTENT_TO_FEATURES
        feature_ids = INTENT_TO_FEATURES.get(intent, [])
        if not feature_ids:
            return True  # Kein Feature-Gate für diesen Intent
        return any(is_enabled(user_key, fid) for fid in feature_ids)

    async def process_message(
        self,
        message: str,
        user_key: str,
        chat_id: int,
        bot,
    ) -> str:
        """
        Hauptfunktion: Verarbeitet eine Nutzernachricht.
        Erkennt Intent und delegiert an passenden Handler.
        """
        intent_data = await self._detect_intent(message, user_key)
        intent = intent_data.get("intent", INTENT_CHAT)
        logger.info(f"Intent erkannt: {intent} für Nachricht: {message[:50]}")

        # Feature-Gate: Deaktivierte Features fallen auf Chat zurück
        if not self._feature_enabled(intent, user_key):
            logger.info(f"Feature für Intent '{intent}' deaktiviert für {user_key}, Fallback auf Chat")
            return await self._handle_chat(message, user_key, bot)

        handlers = {
            INTENT_CALENDAR_READ: self._handle_calendar_read,
            INTENT_CALENDAR_CREATE: self._handle_calendar_create,
            INTENT_NOTE_CREATE: self._handle_note_create,
            INTENT_REMINDER_CREATE: self._handle_reminder_create,
            INTENT_WEB_SEARCH: self._handle_web_search,
            INTENT_TASK_CREATE: self._handle_task_create,
            INTENT_TASK_READ: self._handle_task_read,
            INTENT_TASK_COMPLETE: self._handle_task_complete,
            INTENT_TIMER_CREATE: self._handle_timer_create,
            INTENT_TABLE_CREATE: self._handle_table_create,
            INTENT_PRESENTATION_CREATE: self._handle_presentation_create,
            INTENT_BRIEFING: self._handle_briefing,
            INTENT_SPOTIFY: self._handle_spotify,
            INTENT_SMARTHOME: self._handle_smarthome,
            INTENT_RECIPE_SEARCH: self._handle_recipe_search,
            INTENT_DRIVE: self._handle_drive,
            INTENT_SHOPPING_ADD: self._handle_shopping_add,
            INTENT_SHOPPING_VIEW: self._handle_shopping_view,
            INTENT_SHOPPING_RECIPE: self._handle_shopping_recipe,
            INTENT_EMAIL_READ: self._handle_email_read,
            INTENT_EMAIL_COMPOSE: self._handle_email_compose,
            INTENT_MOBILITY: self._handle_mobility,
            INTENT_WEATHER: self._handle_weather,
        }

        handler = handlers.get(intent, self._handle_chat)
        return await handler(message, intent_data, user_key, chat_id, bot)

    async def _detect_intent(self, message: str, user_key: str) -> tuple[str, dict]:
        """
        Erkennt den Intent einer Nachricht via KI.
        Gibt (intent_type, extracted_data) zurück.
        """
        active_intents = set(get_enabled_intents(user_key))
        now = datetime.now(self.tz)

        all_intent_lines = [
            ('calendar_read', '- calendar_read: Nutzer fragt nach Terminen (z.B. "Was habe ich heute?", "Zeig meine Termine")'),
            ('calendar_create', '- calendar_create: Nutzer will Termin erstellen (z.B. "Zahnarzt am Montag um 10", "Meeting morgen 14 Uhr")'),
            ('note_create', '- note_create: Nutzer will eine Notiz speichern (z.B. "Notiz: ...", "Merkzettel für ...")'),
            ('reminder_create', '- reminder_create: Nutzer will erinnert werden (z.B. "Erinnere mich...", "In 2 Stunden...", "Morgen um 9...")'),
            ('task_create', '- task_create: Nutzer will eine Aufgabe/Todo erstellen (z.B. "Muss noch Steuer machen", "Aufgabe: Einkaufen", "To-Do: Arzt anrufen", "[Name] soll etwas tun")'),
            ('task_read', '- task_read: Nutzer fragt nach offenen Aufgaben (z.B. "Was steht noch an?", "Zeig meine Todos", "Was muss ich noch tun?")'),
            ('task_complete', '- task_complete: Nutzer will eine Aufgabe abhaken (z.B. "Aufgabe 3 erledigt", "Habe eingekauft", "Nummer 2 ist fertig")'),
            ('timer_create', '- timer_create: Nutzer will einen kurzen Countdown/Timer (z.B. "Timer 25 Minuten", "In 30 Min klingeln", "Pomodoro", "Stoppuhr 45 Min"). NUR bei Zeitangaben < 4 Stunden ohne festen Zeitpunkt.'),
            ('table_create', '- table_create: Nutzer will eine Tabelle oder Excel-Datei erstellen (z.B. "Erstelle eine Tabelle meiner Aufgaben", "Mach mir eine Excel-Tabelle", "Tabelle mit meinen Terminen", "Zeig meine Tasks als Tabelle")'),
            ('presentation_create', '- presentation_create: Nutzer will eine Präsentation oder PowerPoint erstellen (z.B. "Erstelle eine Präsentation über X", "PowerPoint zu Thema Y", "Erstell mir Slides für Z")'),
            ('web_search', '- web_search: BEVORZUGE wenn aktuelle/externe Daten gebraucht werden. PFLICHT bei: Wetter (auch "Wetter heute/morgen/diese Woche" → IMMER web_search!), Nachrichten, Preise, Sportergebnisse, Aktienkurse, Börsenkurse, Öffnungszeiten, Rezepte, Definitionen, aktuelle Ereignisse. REGEL: Wenn die Antwort sich täglich ändern kann oder live-Daten benötigt → web_search. Niemals für zeitkritische Fragen chat wählen!'),
            ('spotify', '- spotify: Musik-Steuerung (z.B. "Spiel Musik", "Pause", "Nächster Song", "Spiel Jazz", "Lauter", "Was läuft gerade?")'),
            ('smarthome', '- smarthome: Smart Home / Haus-Steuerung (z.B. "Licht aus", "Heizung auf 22 Grad", "Rollos schließen", "Steckdose Küche an")'),
            ('recipe_search', '- recipe_search: Nutzer sucht ein Rezept oder fragt was er kochen kann (z.B. "Rezept für Pasta Carbonara", "Was kann ich mit Brokkoli kochen?", "Zeig mir ein Kuchenrezept", "Wie macht man Schnitzel?")'),
            ('drive', '- drive: Google Drive Aktionen (z.B. "Zeig meine Drive-Dateien", "Suche Datei X in Drive", "Was liegt in meinem Drive?")'),
            ('shopping_add', '- shopping_add: Nutzer will Artikel auf die Einkaufsliste (z.B. "Kauf noch Milch", "Auf die Einkaufsliste: Brot und Butter", "Ich brauche noch Tomaten")'),
            ('shopping_view', '- shopping_view: Nutzer will die Einkaufsliste sehen (z.B. "Was muss ich einkaufen?", "Einkaufsliste zeigen", "Was steht auf der Liste?")'),
            ('shopping_recipe', '- shopping_recipe: Nutzer will Rezept-Zutaten auf die Einkaufsliste (z.B. "Zutaten für Carbonara auf die Liste", "Füge Zutaten von Rezept X hinzu")'),
            ('email_read', '- email_read: Nutzer fragt nach E-Mails (z.B. "Zeig meine Mails", "Neue E-Mails?", "Was steht in meinem Posteingang?")'),
            ('email_compose', '- email_compose: Nutzer will eine E-Mail schreiben (z.B. "Schreib eine Mail an X", "E-Mail an Chef über Y", "Antworte auf die Mail")'),
            ('mobility', '- mobility: Nutzer fragt nach Fahrzeiten oder Abfahrt (z.B. "Wie lang brauche ich zur Arbeit?", "Wann muss ich losfahren?", "Fahrzeit nach München", "Route zu X berechnen")'),
            ('chat', '- chat: Alles andere (persönliche Fragen, Konversation, Meinungen, Erinnerungen aus Gesprächen)'),
        ]
        intent_lines = "\n".join(line for intent_name, line in all_intent_lines if intent_name in active_intents)

        system_prompt = f"""Du bist ein Intent-Classifier. Analysiere die folgende Nachricht und bestimme den Intent.

Aktuelle Zeit: {now.strftime('%A, %d.%m.%Y %H:%M')} (Zeitzone: {settings.TIMEZONE})

Nachricht: "{message}"

Mögliche Intents:
{intent_lines}

Antworte NUR mit JSON:
{"intent": "...", "details": {...}}

Details je nach Intent:
- calendar_create: {"title": "...", "date": "YYYY-MM-DD oder morgen/heute", "time": "HH:MM", "duration_minutes": 60, "description": "..."}
- note_create: {"title": "...", "content": "..."}
- reminder_create: {"text": "...", "datetime": "YYYY-MM-DD HH:MM oder relative Zeit"}
- task_create: {"title": "...", "due_date": "YYYY-MM-DD oder null", "priority": "low/medium/high"}
- task_complete: {"task_identifier": "..."}
- timer_create: {"minutes": X, "label": "..."}
- table_create: {"title": "...", "description": "Beschreibung was die Tabelle enthalten soll"}
- presentation_create: {"title": "...", "topic": "...", "slides_count": 5}
- spotify: {"action": "play/pause/next/prev/volume", "query": "...", "volume": 0-100}
- smarthome: {"action": "on/off/set", "device": "...", "value": "..."}
- recipe_search: {"query": "...", "dietary": "vegetarisch/vegan/null"}
- drive: {"action": "list/search", "query": "..."}
- shopping_add: {"items": ["item1", "item2"]}
- shopping_recipe: {"recipe_name": "..."}
- email_read: {"filter": "unread/all/from:name"}
- email_compose: {"to": "...", "subject": "...", "body": "..."}
- mobility: {"destination": "...", "origin": "aktueller Standort oder Adresse", "mode": "driving/transit/walking"}
- weather: {"location": "Stadtname oder Adresse", "type": "current/forecast", "days": 3}
"""
        now = datetime.now(self.tz)
        user_prompt = f"Datum: {now.strftime('%Y-%m-%d %H:%M')}\nNachricht: {message}"

        response = await self._complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_mode=True,
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"intent": INTENT_CHAT, "details": {}}

    async def _handle_chat(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Normaler Chat ohne spezielle Funktion."""
        intelligence = self._get_intelligence_service()
        return await intelligence.process_with_memory(message, user_key, chat_id)

    async def _handle_calendar_read(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Liest Kalendereinträge."""
        if not bot.calendar_service:
            return "❌ Kalender-Service nicht verfügbar."

        try:
            now = datetime.now(self.tz)
            events = await bot.calendar_service.get_events(
                start=now,
                end=now + timedelta(days=7)
            )

            if not events:
                return "📅 Keine Termine in den nächsten 7 Tagen."

            lines = ["📅 *Deine nächsten Termine:*\n"]
            for event in events[:10]:
                start = event.get("start", {})
                dt = start.get("dateTime", start.get("date", ""))
                if "T" in dt:
                    dt_obj = datetime.fromisoformat(dt.replace("Z", "+00:00")).astimezone(self.tz)
                    dt_str = dt_obj.strftime("%a, %d.%m. um %H:%M Uhr")
                else:
                    dt_str = dt
                title = event.get("summary", "Kein Titel")
                lines.append(f"• *{title}* – {dt_str}")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Kalender-Fehler: {e}")
            return "❌ Fehler beim Abrufen des Kalenders."

    async def _handle_calendar_create(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Erstellt einen Kalendereintrag."""
        if not bot.calendar_service:
            return "❌ Kalender-Service nicht verfügbar."

        details = intent_data.get("details", {})
        title = details.get("title", "Neuer Termin")
        date_str = details.get("date", "")
        time_str = details.get("time", "09:00")
        duration = details.get("duration_minutes", 60)
        description = details.get("description", "")

        try:
            now = datetime.now(self.tz)

            if date_str in ("heute", "today"):
                date_obj = now.date()
            elif date_str in ("morgen", "tomorrow"):
                date_obj = (now + timedelta(days=1)).date()
            else:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    date_obj = (now + timedelta(days=1)).date()

            try:
                time_obj = datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                time_obj = datetime.strptime("09:00", "%H:%M").time()

            start_dt = self.tz.localize(datetime.combine(date_obj, time_obj))
            end_dt = start_dt + timedelta(minutes=duration)

            event = await bot.calendar_service.create_event(
                title=title,
                start=start_dt,
                end=end_dt,
                description=description,
            )

            if event:
                return f"✅ Termin erstellt: *{title}*\n📅 {start_dt.strftime('%a, %d.%m.%Y um %H:%M Uhr')}"
            return "❌ Termin konnte nicht erstellt werden."
        except Exception as e:
            logger.error(f"Kalender-Erstell-Fehler: {e}")
            return "❌ Fehler beim Erstellen des Termins."

    async def _handle_note_create(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Erstellt eine Notiz."""
        if not bot.notes_service:
            return "❌ Notiz-Service nicht verfügbar."

        details = intent_data.get("details", {})
        title = details.get("title", "Neue Notiz")
        content = details.get("content", message)

        try:
            note = await bot.notes_service.create_note(title=title, content=content)
            if note:
                return f"📝 Notiz erstellt: *{title}*"
            return "❌ Notiz konnte nicht erstellt werden."
        except Exception as e:
            logger.error(f"Notiz-Fehler: {e}")
            return "❌ Fehler beim Erstellen der Notiz."

    async def _handle_reminder_create(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Erstellt eine Erinnerung."""
        if not bot.reminder_service:
            return "❌ Erinnerungs-Service nicht verfügbar."

        details = intent_data.get("details", {})
        text = details.get("text", message)
        dt_str = details.get("datetime", "")

        try:
            now = datetime.now(self.tz)
            remind_dt = None

            if dt_str:
                try:
                    remind_dt = self.tz.localize(datetime.strptime(dt_str, "%Y-%m-%d %H:%M"))
                except ValueError:
                    pass

            if not remind_dt:
                remind_dt = now + timedelta(hours=1)

            reminder = await bot.reminder_service.create_reminder(
                text=text,
                remind_at=remind_dt,
                chat_id=chat_id,
            )

            if reminder:
                return f"⏰ Erinnerung gesetzt: *{text}*\n🕐 {remind_dt.strftime('%d.%m.%Y um %H:%M Uhr')}"
            return "❌ Erinnerung konnte nicht gesetzt werden."
        except Exception as e:
            logger.error(f"Erinnerungs-Fehler: {e}")
            return "❌ Fehler beim Setzen der Erinnerung."

    async def _handle_web_search(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Führt eine Web-Suche durch."""
        web_search = self._get_web_search_service()
        return await web_search.search_and_answer(message, user_key)

    async def _handle_task_create(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Erstellt eine Aufgabe."""
        if not bot.tasks_service:
            return "❌ Aufgaben-Service nicht verfügbar."

        details = intent_data.get("details", {})
        title = details.get("title", message)
        due_date = details.get("due_date")
        priority = details.get("priority", "medium")

        try:
            task = await bot.tasks_service.create_task(
                title=title,
                due_date=due_date,
                priority=priority,
            )
            if task:
                due_str = f"\n📅 Fällig: {due_date}" if due_date else ""
                return f"✅ Aufgabe erstellt: *{title}*{due_str}"
            return "❌ Aufgabe konnte nicht erstellt werden."
        except Exception as e:
            logger.error(f"Aufgaben-Erstell-Fehler: {e}")
            return "❌ Fehler beim Erstellen der Aufgabe."

    async def _handle_task_read(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Zeigt offene Aufgaben an."""
        if not bot.tasks_service:
            return "❌ Aufgaben-Service nicht verfügbar."

        try:
            tasks = await bot.tasks_service.get_tasks()

            if not tasks:
                return "✅ Keine offenen Aufgaben!"

            lines = ["📋 *Deine offenen Aufgaben:*\n"]
            for task in tasks[:15]:
                title = task.get("title", "Unbekannt")
                due = task.get("due_date", "")
                priority = task.get("priority", "medium")
                emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
                due_str = f" (bis {due})" if due else ""
                lines.append(f"{emoji} {title}{due_str}")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Aufgaben-Lese-Fehler: {e}")
            return "❌ Fehler beim Abrufen der Aufgaben."

    async def _handle_task_complete(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Schließt eine Aufgabe ab."""
        if not bot.tasks_service:
            return "❌ Aufgaben-Service nicht verfügbar."

        details = intent_data.get("details", {})
        task_id = details.get("task_identifier", "")

        try:
            success = await bot.tasks_service.complete_task(task_id)
            if success:
                return f"✅ Aufgabe als erledigt markiert!"
            return "❌ Aufgabe konnte nicht abgeschlossen werden."
        except Exception as e:
            logger.error(f"Aufgaben-Complete-Fehler: {e}")
            return "❌ Fehler beim Abschließen der Aufgabe."

    async def _handle_timer_create(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Erstellt einen Timer."""
        if not bot.timer_service:
            return "❌ Timer-Service nicht verfügbar."

        details = intent_data.get("details", {})
        minutes = details.get("minutes", 5)
        label = details.get("label", "Timer")

        try:
            timer = await bot.timer_service.create_timer(
                minutes=minutes,
                label=label,
                chat_id=chat_id,
            )
            if timer:
                return f"⏱️ Timer gestellt: *{label}*\n⏰ Läuft ab in {minutes} Minute(n)"
            return "❌ Timer konnte nicht erstellt werden."
        except Exception as e:
            logger.error(f"Timer-Fehler: {e}")
            return "❌ Fehler beim Erstellen des Timers."

    async def _handle_table_create(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Erstellt eine Tabelle."""
        details = intent_data.get("details", {})
        title = details.get("title", "Tabelle")
        description = details.get("description", message)

        prompt = f"""Erstelle eine übersichtliche Markdown-Tabelle basierend auf dieser Anfrage:

Titel: {title}
Beschreibung: {description}

Erstelle eine sinnvolle, gut strukturierte Tabelle mit relevanten Spalten und Beispieldaten.
Formatiere die Ausgabe als Markdown-Tabelle."""

        response = await self._complete(
            messages=[{"role": "user", "content": prompt}]
        )
        return response

    async def _handle_presentation_create(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Erstellt eine Präsentationsstruktur."""
        details = intent_data.get("details", {})
        title = details.get("title", "Präsentation")
        topic = details.get("topic", message)
        slides_count = details.get("slides_count", 5)

        prompt = f"""Erstelle eine strukturierte Präsentation zum Thema: {topic}

Titel: {title}
Anzahl Folien: {slides_count}

Erstelle für jede Folie:
- Folientitel
- 3-5 Stichpunkte
- Optional: Empfehlung für visuelle Elemente

Formatiere strukturiert und übersichtlich."""

        response = await self._complete(
            messages=[{"role": "user", "content": prompt}]
        )
        return response

    async def _handle_briefing(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Erstellt ein Tagesbriefing."""
        intelligence = self._get_intelligence_service()
        return await intelligence.create_briefing(user_key, chat_id, bot)

    async def _handle_spotify(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Steuert Spotify."""
        if not bot.spotify_service:
            return "❌ Spotify-Service nicht verfügbar."

        details = intent_data.get("details", {})
        action = details.get("action", "play")
        query = details.get("query", "")
        volume = details.get("volume")

        try:
            if action == "play" and query:
                result = await bot.spotify_service.play(query)
            elif action == "pause":
                result = await bot.spotify_service.pause()
            elif action == "next":
                result = await bot.spotify_service.next_track()
            elif action == "prev":
                result = await bot.spotify_service.prev_track()
            elif action == "volume" and volume is not None:
                result = await bot.spotify_service.set_volume(int(volume))
            else:
                result = await bot.spotify_service.get_current()

            return result or "🎵 Spotify-Aktion ausgeführt."
        except Exception as e:
            logger.error(f"Spotify-Fehler: {e}")
            return "❌ Fehler bei der Spotify-Steuerung."

    async def _handle_smarthome(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Steuert Smart Home Geräte."""
        if not bot.smarthome_service:
            return "❌ Smart Home Service nicht verfügbar."

        details = intent_data.get("details", {})
        action = details.get("action", "")
        device = details.get("device", "")
        value = details.get("value", "")

        try:
            result = await bot.smarthome_service.control(
                action=action,
                device=device,
                value=value,
            )
            return result or "🏠 Smart Home Aktion ausgeführt."
        except Exception as e:
            logger.error(f"SmartHome-Fehler: {e}")
            return "❌ Fehler bei der Smart Home Steuerung."

    async def _handle_recipe_search(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Sucht Rezepte."""
        if not bot.recipe_service:
            return "❌ Rezept-Service nicht verfügbar."

        details = intent_data.get("details", {})
        query = details.get("query", message)
        dietary = details.get("dietary")

        try:
            recipes = await bot.recipe_service.search(query=query, dietary=dietary)

            if not recipes:
                return f"🍽️ Keine Rezepte für '{query}' gefunden."

            lines = [f"🍽️ *Rezepte für '{query}':*\n"]
            for recipe in recipes[:5]:
                name = recipe.get("name", "Unbekannt")
                time_mins = recipe.get("time_minutes", "")
                time_str = f" ⏱️ {time_mins} Min." if time_mins else ""
                lines.append(f"• *{name}*{time_str}")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Rezept-Fehler: {e}")
            return "❌ Fehler bei der Rezeptsuche."

    async def _handle_drive(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Verwaltet Google Drive Dateien."""
        if not bot.drive_service:
            return "❌ Drive-Service nicht verfügbar."

        details = intent_data.get("details", {})
        action = details.get("action", "list")
        query = details.get("query", "")

        try:
            if action == "search":
                files = await bot.drive_service.search(query)
            else:
                files = await bot.drive_service.list_recent()

            if not files:
                return "📁 Keine Dateien gefunden."

            lines = ["📁 *Google Drive Dateien:*\n"]
            for f in files[:10]:
                name = f.get("name", "Unbekannt")
                mime = f.get("mimeType", "")
                emoji = "📄" if "document" in mime else "📊" if "spreadsheet" in mime else "📁"
                lines.append(f"{emoji} {name}")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Drive-Fehler: {e}")
            return "❌ Fehler beim Zugriff auf Google Drive."

    async def _handle_shopping_add(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Fügt Artikel zur Einkaufsliste hinzu."""
        if not bot.shopping_service:
            return "❌ Einkaufslisten-Service nicht verfügbar."

        details = intent_data.get("details", {})
        items = details.get("items", [message])

        try:
            added = await bot.shopping_service.add_items(items)
            if added:
                item_list = "\n".join(f"• {item}" for item in items)
                return f"🛒 Zur Einkaufsliste hinzugefügt:\n{item_list}"
            return "❌ Artikel konnten nicht hinzugefügt werden."
        except Exception as e:
            logger.error(f"Shopping-Fehler: {e}")
            return "❌ Fehler beim Hinzufügen zur Einkaufsliste."

    async def _handle_shopping_view(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Zeigt die Einkaufsliste an."""
        if not bot.shopping_service:
            return "❌ Einkaufslisten-Service nicht verfügbar."

        try:
            items = await bot.shopping_service.get_items()

            if not items:
                return "🛒 Einkaufsliste ist leer."

            lines = ["🛒 *Einkaufsliste:*\n"]
            for item in items:
                name = item.get("name", item) if isinstance(item, dict) else item
                lines.append(f"• {name}")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Shopping-View-Fehler: {e}")
            return "❌ Fehler beim Abrufen der Einkaufsliste."

    async def _handle_shopping_recipe(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Fügt Rezeptzutaten zur Einkaufsliste hinzu."""
        if not bot.shopping_service or not bot.recipe_service:
            return "❌ Service nicht verfügbar."

        details = intent_data.get("details", {})
        recipe_name = details.get("recipe_name", message)

        try:
            ingredients = await bot.recipe_service.get_ingredients(recipe_name)
            if not ingredients:
                return f"❌ Keine Zutaten für '{recipe_name}' gefunden."

            added = await bot.shopping_service.add_items(ingredients)
            if added:
                ingredient_list = "\n".join(f"• {i}" for i in ingredients[:10])
                return f"🛒 Zutaten für *{recipe_name}* hinzugefügt:\n{ingredient_list}"
            return "❌ Zutaten konnten nicht hinzugefügt werden."
        except Exception as e:
            logger.error(f"Shopping-Recipe-Fehler: {e}")
            return "❌ Fehler beim Hinzufügen der Rezeptzutaten."

    async def _handle_email_read(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Liest E-Mails."""
        if not bot.email_service:
            return "❌ E-Mail-Service nicht verfügbar."

        details = intent_data.get("details", {})
        email_filter = details.get("filter", "unread")

        try:
            emails = await bot.email_service.get_emails(filter=email_filter)

            if not emails:
                return "📧 Keine neuen E-Mails."

            lines = [f"📧 *E-Mails ({email_filter}):*\n"]
            for email in emails[:5]:
                sender = email.get("from", "Unbekannt")
                subject = email.get("subject", "Kein Betreff")
                date = email.get("date", "")
                lines.append(f"• *{subject}*\n  Von: {sender} | {date}")

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"E-Mail-Lese-Fehler: {e}")
            return "❌ Fehler beim Abrufen der E-Mails."

    async def _handle_email_compose(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Verfasst und sendet eine E-Mail."""
        if not bot.email_service:
            return "❌ E-Mail-Service nicht verfügbar."

        details = intent_data.get("details", {})
        to = details.get("to", "")
        subject = details.get("subject", "")
        body = details.get("body", message)

        if not to:
            return "❌ Kein Empfänger angegeben."

        try:
            success = await bot.email_service.send_email(
                to=to,
                subject=subject,
                body=body,
            )
            if success:
                return f"📧 E-Mail gesendet an *{to}*\nBetreff: {subject}"
            return "❌ E-Mail konnte nicht gesendet werden."
        except Exception as e:
            logger.error(f"E-Mail-Sende-Fehler: {e}")
            return "❌ Fehler beim Senden der E-Mail."

    async def generate_response(self, prompt: str, system_prompt: str = None, user_key: str = None) -> str:
        """Generiert eine einfache AI-Antwort."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        elif user_key:
            messages.append({"role": "system", "content": self._get_system_prompt(user_key)})
        messages.append({"role": "user", "content": prompt})

        return await self._complete(messages)

    async def generate_json(self, prompt: str, system_prompt: str = None) -> dict:
        """Generiert eine strukturierte JSON-Antwort."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._complete(messages, json_mode=True)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {}

    async def _handle_mobility(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Berechnet Fahrzeiten und Routen."""
        if not bot.mobility_service:
            return "❌ Mobilitäts-Service nicht verfügbar."

        details = intent_data.get("details", {})
        destination = details.get("destination", "")
        origin = details.get("origin", "")
        mode = details.get("mode", "driving")

        if not destination:
            return "❌ Kein Ziel angegeben."

        try:
            if origin:
                route = await bot.mobility_service.get_route(
                    origin=origin,
                    destination=destination,
                    mode=mode,
                )
            else:
                route = await bot.mobility_service.get_route(
                    destination=destination,
                    mode=mode,
                )
            if not route:
                return f"❌ Fahrzeit nach _{destination}_ konnte nicht berechnet werden."
            return bot.mobility_service.format_route(route)
        except Exception as e:
            logger.error(f"Mobility-Handler-Fehler: {e}")
            return "❌ Fahrzeit konnte nicht berechnet werden."


    async def _handle_weather(self, message: str, intent_data: dict, user_key: str, chat_id: int, bot) -> str:
        """Ruft Echtzeit-Wetterdaten via WeatherService ab (Open-Meteo, kein API-Key noetig)."""
        from src.services.weather_service import WeatherService
        details = intent_data.get("details", {})
        location = details.get("location", "")
        weather_type = details.get("type", "current")
        days = int(details.get("days", 3))

        if not location:
            home = getattr(settings, "HOME_ADDRESS", "")
            location = home.split(",")[0].strip() if home else "Berlin"

        try:
            weather_svc = WeatherService()
            if weather_type == "forecast":
                data = await weather_svc.get_forecast(location, days=days)
                if not data:
                    return f"Wettervorhersage fuer {location} konnte nicht abgerufen werden."
                return weather_svc.format_forecast(data)
            else:
                data = await weather_svc.get_current(location)
                if not data:
                    return f"Wetter fuer {location} konnte nicht abgerufen werden."
                return weather_svc.format_current(data)
        except Exception as e:
            logger.error(f"Wetter-Handler-Fehler: {e}")
            return "Wetterdaten konnten nicht abgerufen werden."
