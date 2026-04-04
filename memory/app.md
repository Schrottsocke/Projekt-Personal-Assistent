# App

Flutter-App, API-Integration, plattformspezifische Erkenntnisse.

## Eintraege

- **Platform-Scaffolding**: `android/` und `ios/` via PR #333 hinzugefuegt. minSdk=21, INTERNET+RECORD_AUDIO, network_security_config (localhost/10.0.2.2), iOS ATS localhost + Microphone. pubspec.lock jetzt committed. (2026-03-30)
- **Android-Emulator URL**: Fuer lokalen API-Test `10.0.2.2:8000` statt `localhost:8000` verwenden (Android-Emulator-Eigenheit). network_security_config erlaubt Cleartext dorthin. (2026-03-30)
- **Deploy-Roadmap Flutter**: Phase 1 (lokaler Test) erledigt. Phase 2 (Prod-URL + CORS) erledigt: SSL (#388), CORS (#390), CI mit Prod-URL. Phase 3 offen: App-Identifier aendern (`com.example.dualmind` → eigener), Keystore, Icons, optional Firebase/Store. Tracking: #392. (2026-04-01)
- **applicationId**: Aktuell `com.example.dualmind` – muss vor Store-Release geaendert werden (Einmal-Aktion, nicht nachtraeglich aenderbar). (2026-03-30)
- **CI flutter.yml**: APK-Build laeuft bei Push auf main (app/**) und per manueller `workflow_dispatch`. Baut mit `--dart-define=API_BASE_URL=https://dualmind.cloud`. Release-Signing noch nicht konfiguriert – baut mit Debug-Keys. Artifact: `personal-assistant-apk`. Siehe #392 fuer naechste Schritte. (2026-04-01)
- **Web-App Architektur**: Lebt in `api/static/`, getrennt von Flutter-App. Hash-Router (`router.js`), IIFE-View-Module (`js/views/`), API-Client mit JWT (`api.js`). Dashboard ist Navigation-Hub fuer Views ohne Bottom-Nav-Eintrag (Calendar, Tasks, MealPlan, Drive). Inline-onclick-Handler muessen `this` weitergeben statt `window.event` zu nutzen (Firefox-Bug). (2026-03-31)

## Meta

- **CORS Produktion**: VPS auf `https://dualmind.cloud,https://www.dualmind.cloud` eingeschraenkt. Steuerung ueber `API_CORS_ORIGINS` in `.env`, FastAPI CORSMiddleware in `api/main.py:162-177`. Wildcard nur fuer Dev. (2026-04-01)
- **VPS-Projektpfad**: `/home/assistant/projekt-personal-assistent` – User `assistant`, venv mit Python 3.12 (nicht 3.11, Ubuntu 24.04). Services: `personal-assistant`, `personal-assistant-api`, `personal-assistant-webhook`. (2026-04-01)
- **VPS .env Setup**: `.env` wird aus `.env.example` kopiert. Platzhalter muessen manuell gesetzt werden: `API_SECRET_KEY` (token_hex(32)), `API_PASSWORD_TAAKE/NINA` (token_urlsafe(16)), `GITHUB_TOKEN`. API startet nicht mit unsicherem API_SECRET_KEY-Platzhalter. (2026-04-01)
- **Webapp GitHub Issues**: `GET /github/issues` Endpoint mit 5-Min-Cache. View zeigt Issue-Liste + Erstellformular. Labels zuerst laden (fuer Farbdaten), dann Issues. Cache-Invalidierung nach Erstellung. (2026-04-01)
- **Parallel-Agent Shared-Utility-Bug**: Wenn mehrere Agents parallel Views aendern und eine gemeinsame Utility nutzen (z.B. `Toast.showUndo`), muss genau ein Agent die Utility definieren. Workaround: Shared Utilities in separatem Batch VOR den Views implementieren, oder manuell nach Agent-Completion pruefen. (2026-04-04)
- **Webapp Undo/Offline Patterns**: `Toast.showUndo(msg, cb, ms)` in `api.js` fuer optimistic-delete mit 5s Undo. `OfflineQueue.enqueue*(...)` in `offlineQueue.js` fuer offline-queuing. `localStorage` stale-while-revalidate in Dashboard, Calendar, Chat, Inbox. (2026-04-04)
- Zuletzt geprueft: 2026-04-01
- Review bis: 2026-06-28
- Max Eintraege: 20
