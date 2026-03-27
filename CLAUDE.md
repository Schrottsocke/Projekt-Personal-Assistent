# CLAUDE.md

DualMind Personal Assistant:
- Bots: `main.py`
- Backend: `src/`
- API: `api/`
- App: `app/`
- Config: `config/settings.py`
- Deploy: `deploy/`

## Stack
Python 3.11, python-telegram-bot, OpenAI SDK (OpenRouter), FastAPI, SQLAlchemy, mem0ai, Flutter/Dart, Riverpod, Docker, Systemd

Wichtig:
- Zwei verschiedene `memory_service.py` existieren und bleiben getrennt:
  - `src/memory/memory_service.py`
  - `src/services/memory_service.py`
- `.env` enthält Secrets. Niemals committen oder ungefragt ändern.

## Default

Wenn die Session startet und kein klarer User-Auftrag vorliegt:
1. offene GitHub Issues prüfen
2. nach `P0-critical` → `P1-high` → `P2-medium` sortieren
3. genau ein Issue auswählen
4. kurz sagen, welches Issue bearbeitet wird
5. direkt den ersten Schritt ausführen

Wenn offene Issues existieren, keine freie Analyse starten.

## Kein Issue-Zugriff

Wenn Issues nicht geladen werden können:
- nicht raten
- nicht frei losarbeiten
- den User um genau eines bitten:
  - Issue-Nummer
  - kopierten Issue-Text
  - direkten Arbeitsauftrag

## Vor dem ersten Schritt

Genau einmal kurz antworten mit:
- **Aufgabe**
- **Dateien**
- **Erster Schritt**
- **Prüfung**

Danach direkt ausführen.

## Anti-Loop

Ein Plan darf nur einmal erscheinen.

Wenn der Plan schon da ist, tue genau eines:
1. ausführen
2. konkrete Blockade nennen
3. eine gezielte Rückfrage stellen

Nie denselben Plan erneut formulieren.

## Regeln

- Erst verstehen, dann minimal ändern.
- Nur eine Aufgabe pro Durchlauf.
- Kleine Änderungen bevorzugen.
- Keine stillen Refactorings.
- Nach der Änderung kurz prüfen und stoppen.
- Nicht automatisch das nächste Problem anfangen.

## Debug-Reihenfolge

1. Start-/Importfehler
2. Konfiguration
3. Backend-Runtime
4. API/Auth
5. App/API-Integration
6. Deployment

## Stop

Sofort stoppen und Rückfrage stellen bei:
- `.env`, Secrets, Tokens
- Migrationen oder Datenbankschema
- Auth/Security
- produktionsrelevanten Deploy-Änderungen
- größeren Refactorings
- unklarer Zuständigkeit zwischen Bot, API und App

## Ende

Kurz melden:
- **Geändert**
- **Ergebnis**
- **Prüfung**
- **Offen**
