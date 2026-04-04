# E2E & Smoke Tests

## Teststruktur

### API Smoke Flows (`tests/integration/test_smoke_flows.py`)
Cross-Modul User Journeys via TestClient. Kein laufender Server nötig.

**Getestete Kernflows:**
| Flow | Beschreibung |
|------|-------------|
| Dashboard | Leerzustand + Dashboard mit Daten |
| Task-Lifecycle | Erstellen → Anzeigen → Status ändern → Dashboard |
| Shopping-Lifecycle | Hinzufügen → Abhaken → Gecheckte löschen |
| Recipe-Flow | Speichern → Liste → Favorit → Suche |
| Chat-Flow | Nachricht senden → History prüfen |
| Global Search | Suche findet Daten modulübergreifend |
| Notifications | Erstellen → Lesen → Bulk-Update → Mark All Read |
| Multi-User-Isolation | Taake/Nina sehen nur eigene Daten |

### Playwright Browser Tests (`tests/e2e/test_smoke.py`)
UI-Tests mit echtem Browser. Benötigt laufenden Server.

**Getestete Flows:**
- Login-Seite lädt, falsche Credentials zeigen Fehler
- Dashboard rendert Widgets
- Navigation: Shopping, Recipes, Chat, Profile, Tasks
- Shopping-View hat Eingabefeld und Liste
- Tasks-View rendert Aufgabenliste
- Chat-View hat Input + Senden-Button
- Unbekannte Route fällt auf Dashboard zurück

## Lokal ausführen

```bash
# API Smoke Flows (schnell, kein Server nötig)
pytest tests/integration/test_smoke_flows.py -v

# Alle Integration-Tests
pytest tests/integration/ -v

# Playwright E2E (braucht laufenden Server)
export E2E_BASE_URL=http://localhost:8000
export E2E_TEST_USER=taake
export E2E_TEST_PASSWORD=<dein-passwort>
python -m playwright install chromium
pytest tests/e2e/ -v

# Alles mit Coverage
pytest tests/ -v --cov=src --cov=api --cov-report=term-missing
```

## CI

- **API Smoke Flows** laufen im `test`-Job (pytest erfasst `tests/integration/` automatisch)
- **Playwright E2E** laufen im `e2e`-Job (`continue-on-error: true` bis stabil)
- Smoke-Flow-Tests brauchen keine extra CI-Konfiguration

## Bekannte Testlücken

- **Streaming-Chat** (SSE) – nicht mit TestClient testbar
- **Voice-Transcription** – externer Service
- **Calendar-Events** – Google Calendar API (gemockt in `test_calendar_api.py`)
- **Drive/Documents** – Google Drive API
- **Mealplan → Shopping** – Zutaten-Export zum Einkauf
- **Offline-Queue** – Frontend-only, kein API-Test möglich
- **Command Palette / Quick Capture** – Frontend-only Modal/Keyboard-Shortcut
- **Contacts, Shifts, Automation** – CRUD existiert, aber noch keine Smoke-Tests
