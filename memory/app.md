# App

Flutter-App, API-Integration, plattformspezifische Erkenntnisse.

## Eintraege

- **Platform-Scaffolding**: `android/` und `ios/` via PR #333 hinzugefuegt. minSdk=21, INTERNET+RECORD_AUDIO, network_security_config (localhost/10.0.2.2), iOS ATS localhost + Microphone. pubspec.lock jetzt committed. (2026-03-30)
- **Android-Emulator URL**: Fuer lokalen API-Test `10.0.2.2:8000` statt `localhost:8000` verwenden (Android-Emulator-Eigenheit). network_security_config erlaubt Cleartext dorthin. (2026-03-30)
- **Deploy-Roadmap Flutter**: Phase 1 (lokaler Test) erledigt. Phase 2: Prod-URL + CORS + Secrets auf Server. Phase 3: App-Identifier aendern (`com.example.dualmind` → eigener), Keystore, Icons, CI-Fix, optional Firebase/Store. User muss liefern: Domain, Identifier, Signing-Keys, Firebase-Entscheidung. (2026-03-30)
- **applicationId**: Aktuell `com.example.dualmind` – muss vor Store-Release geaendert werden (Einmal-Aktion, nicht nachtraeglich aenderbar). (2026-03-30)
- **CI flutter.yml**: APK-Build laeuft nur bei Push auf main mit app/**-Aenderungen. Braucht android/ im Repo (jetzt vorhanden). Release-Signing noch nicht konfiguriert – baut mit Debug-Keys. (2026-03-30)
- **Web-App Architektur**: Lebt in `api/static/`, getrennt von Flutter-App. Hash-Router (`router.js`), IIFE-View-Module (`js/views/`), API-Client mit JWT (`api.js`). Dashboard ist Navigation-Hub fuer Views ohne Bottom-Nav-Eintrag (Calendar, Tasks, MealPlan, Drive). Inline-onclick-Handler muessen `this` weitergeben statt `window.event` zu nutzen (Firefox-Bug). (2026-03-31)

## Meta

- Zuletzt geprueft: 2026-03-28
- Review bis: 2026-06-28
- Max Eintraege: 20
