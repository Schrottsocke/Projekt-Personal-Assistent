# CLAUDE.md – Arbeitskontext für Claude Code

## Projekt

DualMind Personal Assistant – zwei Telegram-Bots (TaakeBot + NinaBot) mit geteiltem Gedächtnis, REST API und Flutter App.

## Ziel dieses Dokuments

Dieses Dokument definiert, wie in diesem Repository gearbeitet wird.

Ziel ist:
- kleine, sichere, nachvollziehbare Schritte statt großer unkontrollierter Änderungen
- klare Priorisierung über GitHub Issues
- erst Stabilität und Debugging, dann Ausbau
- keine stillen Seiteneffekte über Bot, API, App und Deployment hinweg

Claude soll:
- erst verstehen, dann ändern,
- pro Durchlauf nur eine klar abgegrenzte Aufgabe bearbeiten,
- nach jeder Änderung kurz verifizieren,
- bei Risiko oder Unklarheit stoppen und den User fragen.

## Sessionstart

Wenn eine neue Session beginnt und der User keinen anderen klaren Auftrag gibt, starte automatisch im Modus **Issue abarbeiten**.

Pflichtablauf bei Sessionstart:
1. Prüfe die offenen GitHub Issues im Repository `Schrottsocke/Projekt-Personal-Assistent`.
2. Sortiere sie nach Priorität: `P0-critical` → `P1-high` → `P2-medium`.
3. Wähle genau **ein** nächstes sinnvolles Issue.
4. Antworte dem User sofort mit:
   - der gewählten Issue-Nummer und dem Titel,
   - dem Grund für die Auswahl,
   - den Dateien oder Bereichen, die du zuerst prüfen willst.
5. Beginne erst danach mit der Analyse.

Wichtig:
- Nicht mit freier Analyse starten, solange ein sinnvolles offenes Issue verfügbar ist.
- Nicht mehrere Issues gleichzeitig auswählen.
- Nicht ohne Begründung vom priorisierten nächsten Issue abweichen.

## Fallback bei fehlendem Issue-Zugriff

Wenn GitHub Issues nicht geladen werden können oder kein Tool-Zugriff darauf besteht:
- nicht raten,
- nicht eigenständig irgendein Feature auswählen,
- den User klar darauf hinweisen, dass der Issue-Zugriff fehlt.

Bitte den User dann um genau eine der folgenden Angaben:
1. die Issue-Nummer,
2. den kopierten Inhalt eines Issues,
3. einen direkten Arbeitsauftrag,
4. die ausdrückliche Freigabe für Modus „Analyse & Issues erstellen".

Wenn kein Issue-Zugriff möglich ist, bleibt **Issue abarbeiten** zwar der bevorzugte Modus, kann aber ohne User-Hilfe nicht automatisch gestartet werden.

## Architektur

- **Backend (Python):** `src/` – Services, Handler, Scheduler, Memory, Bots
- **REST API:** `api/` – FastAPI mit JWT-Auth
- **Mobile App:** `app/` – Flutter (Dart), Riverpod State-Management
- **Config:** `config/settings.py` – zentralisierte Settings aus `.env`
- **Deploy:** `deploy/` – Systemd-Services, Bootstrap, Webhook-Deployer

## Einstiegspunkte

| Datei | Zweck |
|---|---|
| `main.py` | Telegram-Bots (TaakeBot + NinaBot) |
| `api/main.py` | FastAPI App-Definition |
| `api/api_main.py` | Standalone-Startskript für die API |
| `app/lib/main.dart` | Flutter App Entry |
| `config/settings.py` | zentrale Konfiguration |
| `README.md` | Projektübersicht |

Regeln:
- keine Code-Aenderungen
- nur Analyse, Problemfindung, Strukturierung und Issue-Vorschlaege
- wenn GitHub-Issues erstellt werden sollen: pro Thema klarer Titel, Beschreibung, Prioritaet, DoD

- **Zwei memory_service.py:** `src/memory/memory_service.py` (Telegram Bot) und `src/services/memory_service.py` (API) sind unterschiedliche Implementierungen mit verschiedenen Schnittstellen. Beide werden aktiv genutzt.
- **Secrets:** `.env` enthält alle API-Keys und Tokens. Niemals committen. `.env.example` ist die Vorlage.

## Tech-Stack

- Python 3.11, python-telegram-bot, OpenAI SDK (OpenRouter), FastAPI, SQLAlchemy, mem0ai
- Flutter/Dart, Riverpod
- Docker, Systemd (Hostinger VPS)

## Praktische Prioritaeten fuer dieses Repo

Wenn unklar ist, womit begonnen werden soll, bevorzuge:

1. reproduzierbare Fehler
2. Startprobleme
3. Auth- und Konfigurationsfehler
4. klare Runtime-Exceptions
5. Integration zwischen API und App
6. Deployment-/Betriebsprobleme
7. erst danach Refactorings oder Komfortverbesserungen

## Erwartetes Verhalten am Ende eines Durchlaufs

Am Ende jeder Aufgabe kurz antworten mit:

- **Geaendert:** welche Datei(en)
- **Ergebnis:** was behoben / angepasst wurde
- **Verifikation:** was geprueft wurde
- **Offen:** was noch nicht geklaert ist
