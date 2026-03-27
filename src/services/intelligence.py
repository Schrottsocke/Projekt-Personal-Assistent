"""
Intelligenz-Engine: Proaktive Mustererkennung, Stimmungsanalyse,
Smarte Gedächtnis-Extraktion, Cross-User Awareness.

Wird vom Scheduler periodisch aufgerufen und läuft im Hintergrund.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import pytz

from config.settings import settings

logger = logging.getLogger(__name__)


class IntelligenceEngine:
    """
    Die 'Intelligenz' des Assistenten. Analysiert Muster,
    erkennt Stimmungen und generiert proaktive Vorschläge.
    """

    def __init__(self, ai_service):
        self._ai = ai_service
        self.tz = pytz.timezone(settings.TIMEZONE)

    # =========================================================================
    # 1. SMARTE GEDÄCHTNIS-EXTRAKTION
    # =========================================================================

    async def extract_facts(self, user_key: str, user_message: str, bot_response: str) -> list[str]:
        """
        Extrahiert strukturierte Fakten aus einem Gesprächsaustausch.
        Statt rohen Chat in mem0 zu kippen, werden hier gezielt
        merkbare Informationen herausgefiltert.

        Returns: Liste von Fakten-Strings (leer wenn nichts Relevantes)
        """
        prompt = f"""Analysiere diesen Gesprächsaustausch und extrahiere WICHTIGE persönliche Fakten,
die sich ein persönlicher Assistent langfristig merken sollte.

Nutzer ({user_key}): "{user_message}"
Assistent: "{bot_response}"

Regeln:
- Nur Fakten extrahieren, die langfristig relevant sind
- Keine Banalitäten (z.B. "hat Hallo gesagt")
- Kategorien: Vorlieben, Abneigungen, Personen, Gewohnheiten, Ziele, Gesundheit, Job, Familie
- Kurz und prägnant formulieren (eine Zeile pro Fakt)
- Wenn der Nutzer etwas korrigiert, den korrigierten Fakt verwenden
- Wenn nichts Wichtiges → leere Liste

Antworte NUR mit diesem JSON:
{{
  "facts": ["Fakt 1", "Fakt 2"],
  "has_facts": true/false
}}"""

        try:
            response = await self._ai._complete(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
            )
            data = json.loads(response)
            if data.get("has_facts"):
                facts = data.get("facts", [])
                logger.debug(f"Fakten extrahiert für {user_key}: {facts}")
                return facts
            return []
        except Exception as e:
            logger.warning(f"Fakten-Extraktion fehlgeschlagen: {e}")
            return []

    # =========================================================================
    # 2. STIMMUNGSERKENNUNG
    # =========================================================================

    async def detect_mood(self, user_message: str) -> dict:
        """
        Analysiert die Stimmung einer Nachricht.
        Returns: {"mood": "stressed|happy|sad|neutral|excited|tired|frustrated",
                  "intensity": 0.0-1.0,
                  "tone_adjustment": "Anweisung für System-Prompt"}
        """
        prompt = f"""Analysiere die Stimmung dieser Nachricht (nur 1 Wort + Intensität).

Nachricht: "{user_message}"

Antworte NUR mit JSON:
{{
  "mood": "stressed|happy|sad|neutral|excited|tired|frustrated|angry",
  "intensity": 0.0-1.0,
  "tone_adjustment": "kurze Anweisung wie der Assistent reagieren soll"
}}

Beispiele für tone_adjustment:
- stressed (0.8): "Antworte kurz, klar und beruhigend. Keine Witze."
- happy (0.7): "Sei locker, teile die Freude kurz mit."
- sad (0.6): "Sei einfühlsam und verständnisvoll."
- tired (0.5): "Fasse dich kurz. Keine langen Erklärungen."
- neutral (0.3): "Normaler Ton."
- frustrated (0.8): "Sei lösungsorientiert und direkt. Kein Small-Talk."
"""

        try:
            response = await self._ai._complete(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
            )
            return json.loads(response)
        except Exception as e:
            logger.warning(f"Stimmungserkennung fehlgeschlagen: {e}")
            return {"mood": "neutral", "intensity": 0.3, "tone_adjustment": "Normaler Ton."}

    # =========================================================================
    # 3. PROAKTIVE MUSTERERKENNUNG (Scheduler-Job)
    # =========================================================================

    async def analyze_patterns(self, user_key: str, bot) -> list[dict]:
        """
        Analysiert Gesprächshistorie + Kalender + Erinnerungen
        und generiert proaktive Vorschläge als Proposals.

        Wird alle 2 Tage vom Scheduler aufgerufen.
        Returns: Liste von generierten Proposal-Dicts
        """
        now = datetime.now(self.tz)

        # Daten sammeln
        memories = await bot.memory_service.get_all_memories(user_key=user_key)
        memories_text = "\n".join(
            f"- {m.get('memory', '')}" for m in memories[:20]
        ) or "Keine gespeicherten Infos."

        # Letzte Konversationen
        try:
            from src.services.database import ConversationHistory, get_db
            with get_db()() as session:
                recent = (
                    session.query(ConversationHistory)
                    .filter_by(user_key=user_key)
                    .order_by(ConversationHistory.created_at.desc())
                    .limit(30)
                    .all()
                )
                chat_text = "\n".join(
                    f"[{r.role}]: {r.content[:100]}" for r in reversed(recent)
                ) or "Keine Gespräche."
        except Exception:
            chat_text = "Keine Gespräche."

        # Kalender der nächsten 14 Tage
        try:
            events = await bot.calendar_service.get_upcoming_events(
                user_key=user_key, days=14
            )
            events_text = "\n".join(
                f"- {e.get('summary', '?')} ({e.get('start', {}).get('dateTime', e.get('start', {}).get('date', '?'))})"
                for e in events
            ) or "Keine Termine."
        except Exception:
            events_text = "Kalender nicht verfügbar."

        # Aktive Erinnerungen
        try:
            reminders = await bot.reminder_service.get_active_reminders(user_key=user_key)
            reminders_text = "\n".join(
                f"- {r['content']} ({r['remind_at'].strftime('%d.%m. %H:%M')})"
                for r in reminders
            ) or "Keine aktiven Erinnerungen."
        except Exception:
            reminders_text = "Keine Erinnerungen."

        prompt = f"""Du bist ein intelligenter persönlicher Assistent.
Analysiere die folgenden Daten und generiere PROAKTIVE, nützliche Vorschläge.

Aktuelles Datum: {now.strftime('%A, %d.%m.%Y %H:%M')}
Nutzer: {user_key}

=== GEDÄCHTNIS (was du über den Nutzer weißt) ===
{memories_text}

=== LETZTE GESPRÄCHE ===
{chat_text}

=== KOMMENDE TERMINE (14 Tage) ===
{events_text}

=== AKTIVE ERINNERUNGEN ===
{reminders_text}

Generiere Vorschläge basierend auf Mustern. Beispiele:
- Wiederkehrende Termine erkennen → "Du hattest die letzten 3 Wochen Montags ein Meeting. Serientermin einrichten?"
- Verfallene Routinen → "Du hast Fitness als Interesse genannt, aber keine Sport-Termine. Trainingszeit einplanen?"
- Lücken erkennen → "Nächste Woche ist leer – freie Woche oder etwas planen?"
- Erwähnte Vorhaben → "Du hast letzte Woche 'Steuer machen' erwähnt. Erinnerung setzen?"
- Stimmungsmuster → "Du hast diese Woche mehrmals 'müde' erwähnt. Schlafenszeit-Erinnerung?"
- Soziale Kontakte → "Du hast lange nicht über [Person] gesprochen – melden?"

Regeln:
- Maximal 3 Vorschläge (nur wirklich nützliche)
- Jeder Vorschlag muss einen konkreten Proposal-Typ haben
- Keine generischen Tipps, nur datenbasierte Vorschläge
- Wenn keine sinnvollen Muster → leere Liste

Antworte NUR mit JSON:
{{
  "suggestions": [
    {{
      "type": "calendar_create|reminder_create|note_create|ai_suggestion",
      "title": "Kurzer Titel",
      "description": "Begründung warum dieser Vorschlag nützlich ist",
      "payload": {{}}
    }}
  ]
}}

Payload je nach Typ:
- calendar_create: {{"summary": "...", "start": "ISO datetime", "end": "ISO datetime"}}
- reminder_create: {{"content": "...", "remind_at": "ISO datetime"}}
- note_create: {{"content": "..."}}
- ai_suggestion: {{"suggestion": "Freitext-Vorschlag"}}
"""

        try:
            response = await self._ai._complete(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
            )
            data = json.loads(response)
            suggestions = data.get("suggestions", [])
            logger.info(f"Pattern-Analyse für {user_key}: {len(suggestions)} Vorschläge")
            return suggestions
        except Exception as e:
            logger.error(f"Pattern-Analyse fehlgeschlagen: {e}")
            return []

    # =========================================================================
    # 4. CROSS-USER AWARENESS
    # =========================================================================

    async def detect_cross_user_mention(
        self, user_key: str, message: str, partner_key: str
    ) -> Optional[dict]:
        """
        Prüft ob eine Nachricht den Partner erwähnt und extrahiert
        relevanten Kontext, der an den Partner-Bot weitergegeben werden soll.

        Returns: {"mentioned": True, "context": "Was der Partner wissen sollte"}
                 oder None wenn keine Erwähnung
        """
        # Quick-Check: enthält die Nachricht den Partnernamen?
        partner_name = partner_key.capitalize()
        if partner_name.lower() not in message.lower():
            return None

        prompt = f"""Analysiere ob diese Nachricht eine andere Person ({partner_name}) erwähnt
und ob der Kontext für {partner_name} relevant wäre.

Nachricht von {user_key}: "{message}"

Antworte NUR mit JSON:
{{
  "mentioned": true/false,
  "relevant_for_partner": true/false,
  "context": "Kurze Zusammenfassung was {partner_name} wissen sollte",
  "shared_event": true/false
}}

Beispiele:
- "Nina und ich essen heute Pizza" → relevant, context: "{user_key.capitalize()} plant heute Abend Pizza essen."
- "Nina hat angerufen" → relevant, context: "{user_key.capitalize()} erwähnt dass {partner_name} angerufen hat."
- "Wie funktioniert das Nina-Plugin?" → nicht relevant (anderer Kontext)
"""

        try:
            response = await self._ai._complete(
                messages=[{"role": "user", "content": prompt}],
                json_mode=True,
            )
            data = json.loads(response)
            if data.get("mentioned") and data.get("relevant_for_partner"):
                return {
                    "mentioned": True,
                    "context": data.get("context", ""),
                    "shared_event": data.get("shared_event", False),
                }
            return None
        except Exception as e:
            logger.warning(f"Cross-User-Erkennung fehlgeschlagen: {e}")
            return None

    # =========================================================================
    # 5. WOCHENRÜCKBLICK
    # =========================================================================

    async def generate_weekly_review(self, user_key: str, name: str, bot) -> str:
        """
        Generiert den sonntäglichen Wochenrückblick.
        Fasst die Woche zusammen und gibt Empfehlungen für die nächste.
        """
        now = datetime.now(self.tz)
        week_start = now - timedelta(days=7)

        # Konversations-History der letzten Woche
        try:
            from src.services.database import ConversationHistory, Proposal, get_db
            with get_db()() as session:
                chats = (
                    session.query(ConversationHistory)
                    .filter(
                        ConversationHistory.user_key == user_key,
                        ConversationHistory.created_at >= week_start,
                    )
                    .order_by(ConversationHistory.created_at.asc())
                    .all()
                )
                chat_summary = "\n".join(
                    f"[{c.role}]: {c.content[:80]}" for c in chats[-30:]
                ) or "Keine Gespräche diese Woche."

                # Proposals der Woche
                proposals = (
                    session.query(Proposal)
                    .filter(
                        Proposal.user_key == user_key,
                        Proposal.created_at >= week_start,
                    )
                    .all()
                )
                approved = sum(1 for p in proposals if p.status == "approved")
                rejected = sum(1 for p in proposals if p.status == "rejected")
                pending = sum(1 for p in proposals if p.status == "pending")
                proposal_summary = (
                    f"Vorschläge: {len(proposals)} erstellt, "
                    f"{approved} genehmigt, {rejected} abgelehnt, {pending} offen."
                )
        except Exception:
            chat_summary = "Keine Daten."
            proposal_summary = "Keine Daten."

        # Memories
        memories = await bot.memory_service.get_all_memories(user_key=user_key)
        memories_text = "\n".join(
            f"- {m.get('memory', '')}" for m in memories[:10]
        ) or "Keine."

        # Kalender nächste Woche
        try:
            events = await bot.calendar_service.get_upcoming_events(
                user_key=user_key, days=7
            )
            next_week = "\n".join(
                f"- {e.get('summary', '?')}" for e in events
            ) or "Keine Termine."
        except Exception:
            next_week = "Kalender nicht verfügbar."

        prompt = f"""Du bist {name}s persönlicher Assistent.
Erstelle einen kurzen, persönlichen Wochenrückblick.

Heute: {now.strftime('%A, %d.%m.%Y')}

=== GESPRÄCHE DIESE WOCHE ===
{chat_summary}

=== VORSCHLÄGE DIESE WOCHE ===
{proposal_summary}

=== WAS DU ÜBER {name.upper()} WEISST ===
{memories_text}

=== TERMINE NÄCHSTE WOCHE ===
{next_week}

Das Review soll:
- Mit "📊 *Wochenrückblick* – KW{now.isocalendar()[1]}" beginnen
- Zusammenfassen was diese Woche los war (2-3 Sätze)
- Highlight der Woche nennen (wenn möglich)
- Vorschau nächste Woche geben
- 1-2 konkrete Empfehlungen machen
- Motivierend enden
- Max 12 Sätze, auf Deutsch
- Markdown-Formatierung nutzen"""

        return await self._ai._complete(
            messages=[{"role": "user", "content": prompt}]
        )
