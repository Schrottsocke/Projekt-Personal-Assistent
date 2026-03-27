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
5. **Keine Arbeit ohne Issue.** Neue Features, Bugs und Refactorings immer zuerst als GitHub Issue anlegen. Priorisierung ueber Labels (P0/P1/P2).

## Arbeitsmodi

### Modus 1: Issue abarbeiten (Standard)
- Offene Issues nach Prioritaet abarbeiten: P0-critical → P1-high → P2-medium
- Kein neues Issue erstellen waehrend der Arbeit
- Neue Probleme notieren, aber NICHT sofort als Issue anlegen
- Am Ende der Session: gesammelte Probleme dem User melden

### Modus 2: Analyse & Issues erstellen
- Nur wenn User explizit sagt: "Analysiere...", "Erstelle Issues...", "Finde Probleme..."
- Keine Code-Aenderungen in diesem Modus
- Issues erstellen, labeln, fertig

### Modus 3: Freie Arbeit
- User gibt direkten Auftrag der kein Issue betrifft
- Normal ausfuehren, kein Issue-Zwang

## Issue-Workflow

**Alle Arbeit wird ueber GitHub Issues gesteuert (Repo: schrottsocke/projekt-personal-assistent).**

### Bei Sessionstart
1. Offene Issues laden (State: OPEN)
2. Nach Prioritaet sortieren: P0-critical → P1-high → P2-medium
3. Naechstes Issue mit hoechster Prioritaet waehlen
4. User informieren welches Issue bearbeitet wird

### Waehrend der Arbeit
1. Issue-Nummer in allen Commits referenzieren: `fix(scope): Beschreibung (#Issue)`
2. Pro Issue ein Branch: `fix/#<nummer>-kurzbeschreibung`
3. Nur Dateien aendern die im Issue gelistet sind (oder begruendet ergaenzen)
4. Definition of Done aus dem Issue als Checkliste abarbeiten

### Nach Abschluss
1. Alle DoD-Checkboxen im Issue abhaken (Issue updaten)
2. Issue schliessen mit state: closed, state_reason: completed
3. Naechstes Issue vorschlagen

### Neue Probleme entdeckt
- Nicht sofort fixen, sondern am Ende der Session dem User melden
- User entscheidet ob neues Issue erstellt wird (→ Modus 2)

## Tech-Stack

- Python 3.11, python-telegram-bot, OpenAI SDK (OpenRouter), FastAPI, SQLAlchemy, mem0ai
- Flutter/Dart, Riverpod
- Docker, Systemd (Hostinger VPS)
