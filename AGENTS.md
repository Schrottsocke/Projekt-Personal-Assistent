# AGENTS.md — DualMind Personal Assistant

> Fuer detaillierte Arbeitsregeln, Guardrails und Workflow-Pflichten: siehe `CLAUDE.md`.

## Projektuebersicht

- **Was:** Persoenlicher Assistent mit Telegram Bot + REST API + Web App + Flutter App
- **Stack:** Python 3.11+, FastAPI, SQLite, Flutter/Dart, Vanilla JS (kein Build-Step)
- **Hosting:** Hostinger VPS (systemd, nginx, SSL)
- **Zwei Bots:** TaakeBot + NinaBot – eigene Tokens, eigene Persoenlichkeit, gemeinsames Memory

## Architektur

| Pfad | Funktion |
|---|---|
| `main.py` | Telegram Bot Einstiegspunkt (python-telegram-bot, beide Bots parallel) |
| `api/api_main.py` | FastAPI REST API Starter (Port 8000, uvicorn) |
| `api/main.py` | FastAPI App-Definition, Routen, Middleware |
| `api/static/` | Web App (Vanilla JS, IIFE-Module, kein Build-Step) |
| `app/` | Flutter Mobile App (iOS/Android) |
| `src/bots/` | TaakeBot, NinaBot – Telegram Handler |
| `src/services/` | Shared Business Logic (AI, Calendar, Shopping, Tasks, …) |
| `src/memory/` | Memory Service (mem0 + ChromaDB) |
| `src/scheduler/` | Proaktive Jobs (Briefing, Reminder, Wochenrueckblick) |
| `config/settings.py` | Zentrale Konfiguration, alle Werte aus `.env` |
| `deploy/` | systemd-Units, nginx.conf, Setup-Skripte |

## Wichtige Architekturentscheidungen

- **Zwei-Modell-Split:** `AI_MODEL_INTENT` (schnell/klein, Regex-Pre-Filter vor LLM-Call) + `AI_MODEL_CHAT` (qualitativ, OpenRouter)
- **Memory-Architektur:** `BaseMemoryService` (gemeinsame mem0-Logik) → `BotMemoryService` (SQLite Facts, Onboarding) + `ApiMemoryService` (add_fact)
- **Memory-Cache:** TTL-Cache auf Memory-Search-Queries
- **Image-Proxy:** Proxy-Endpunkt fuer Chefkoch-CDN (CORS-Umgehung)
- **Auth:** JWT mit Auto-Refresh in `api/static/js/api.js`
- **Chat-Streaming:** SSE-Streaming fuer Chat-Responses
- **Web App:** IIFE-Module in `api/static/js/views/` — kein Bundler, Script-Reihenfolge in `app.html` ist kritisch

## Modul-Grenzen (kein Cross-Edit in parallelen Batches)

- `main.py` und `config/settings.py` sind zentrale Dateien → nur sequentiell aendern
- `src/memory/base_memory_service.py` ist Basis beider MemoryService-Varianten → nur sequentiell
- `api/static/` (Web App) und `app/` (Flutter) sind vollstaendig getrennte Schichten
- Bot-Services (`src/bots/`) und API-Routen (`api/`) nicht im selben Batch bearbeiten

## Technische Leitplanken

- `.env` enthaelt Secrets — niemals committen, niemals ungefragt aendern
- Stop-Pflicht bei: Auth/Security, Migrationen, Deploy-Aenderungen, Web-App-Architektur, Flutter `applicationId`, externe Service-Integrationen (vollstaendige Liste: `CLAUDE.md` → Abschnitt „Stop”)
- Keine stillen Refactorings — nur minimale, gezielte Aenderungen
- Externe Services: Groq (Voice/Whisper), OpenRouter (AI), Google (Calendar/Drive/Gmail), Spotify, Home Assistant

## UX-Roadmap (offene Bereiche)

DualMind ist ein produktiv genutzter Assistent, keine Demo-Oberflaeche. Bekannte offene Bereiche:

- **Dashboard:** Widgets aktivierbar/deaktivierbar/sortierbar, Fokus-/Heute-Ansicht als kompakte Variante
- **Chat:** Plattformuebergreifende Chat-Logik (Telegram, Web, App), Voice als Eingabekanal → Text
- **Inbox/Notifications:** Inbox fuer Vorschlaege, Notifications fuer Hinweise — fachlich getrennt halten
- **Dokumente:** Echter Nutzerfluss: neu → analysiert → Aktion vorgeschlagen → abgelegt
- **Kontakte:** Leichte Kontextschicht fuer E-Mail/Kalender/Erinnerungen, kein CRM
- **Preferences:** Plattformuebergreifendes Preferences-Modell (Theme, Navigation, Fokus, Quiet Hours, TTS)
- **Mobility/Wetter:** Proaktive Zusammenarbeit mit Kalenderkontext

UX-Grundregeln: Loading-, Empty- und Error-States in jeder Ansicht. Mobile immer mitdenken.

## Testing

- Framework: `pytest`
- Unit-Tests: `tests/unit/`
- Integration-Tests: `tests/integration/`
- Konfiguration: `tests/conftest.py`
- Kein Frontend-Test-Framework (manuelle Tests)

## Deployment

- **systemd Services:** `personal-assistant.service`, `personal-assistant-api.service`, `personal-assistant-webhook.service`
- **Konfigurationsdateien:** `deploy/`
- **nginx:** Reverse Proxy + SSL (Let's Encrypt)
- **Gefuehrtes Deployment:** `/deploy` Skill verwenden — nicht manuell deployen ohne Pruefung
