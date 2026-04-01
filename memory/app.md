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
- Zuletzt geprueft: 2026-04-01
- Review bis: 2026-06-28
- Max Eintraege: 20
