# CLAUDE.md – Arbeitskontext fuer Claude Code

## Projekt

DualMind Personal Assistant – Zwei Telegram-Bots (TaakeBot + NinaBot) mit geteiltem Gedaechtnis, REST API und Flutter App.

## Architektur

- **Backend (Python):** `src/` – Services, Handler, Scheduler, Memory, Bots
- **REST API:** `api/` – FastAPI mit JWT-Auth (Port 8000)
- **Mobile App:** `app/` – Flutter (Dart), Riverpod State-Management
- **Config:** `config/settings.py` – Zentralisierte Settings aus `.env`
- **Deploy:** `deploy/` – Systemd-Services, Bootstrap, Webhook-Deployer

## Einstiegspunkte

| Datei | Zweck |
|---|---|
| `main.py` | Telegram Bot (TaakeBot + NinaBot) |
| `api/main.py` | FastAPI App-Definition |
| `api/api_main.py` | Standalone-Startskript fuer die API |
| `app/lib/main.dart` | Flutter App Entry |

## Bekannte Hinweise

- **Zwei memory_service.py:** `src/memory/memory_service.py` (Telegram Bot) und `src/services/memory_service.py` (API) sind unterschiedliche Implementierungen mit verschiedenen Schnittstellen. Beide werden aktiv genutzt. Konsolidierung ist ein moegliches Refactoring-Ziel.
- **Secrets:** `.env` enthaelt alle API-Keys und Tokens. Niemals committen. `.env.example` ist die Vorlage.

## Arbeitsregeln

1. **Erst analysieren, dann minimal aendern.** Code lesen und verstehen, bevor Aenderungen gemacht werden.
2. **Kleine Schritte, keine Endlosschleifen.** Jede Aenderung einzeln durchfuehren und verifizieren.
3. **Maximal 1 zusammenhaengende Aufgabe pro Durchlauf.** Fokus halten, nicht abschweifen.
4. **Nach Aenderungen immer kurz pruefen, dann stoppen.** Ergebnis verifizieren, nicht blind weitermachen.
5. **Keine neuen Features, keine grossen Refactorings ohne expliziten Auftrag.** Nur das tun, was angefragt wurde.

## Tech-Stack

- Python 3.11, python-telegram-bot, OpenAI SDK (OpenRouter), FastAPI, SQLAlchemy, mem0ai
- Flutter/Dart, Riverpod
- Docker, Systemd (Hostinger VPS)
