# Handoffs

Session-Uebergaben, offene Faeden zwischen Sessions, naechste Schritte.
Wird aggressiv bereinigt - nur die letzten Eintraege behalten.

## Eintraege

- **Flutter E2E (#260)**: PR #333 gemergt = Android/iOS Platforms, pubspec.lock, Permissions, Network Config. Naechster Schritt: User testet manuell auf Emulator/Geraet (API starten → flutter run → Login → Dashboard → Chat). Danach #260 schliessen. (2026-03-30)
- **Flutter Deploy-Readiness**: Phase 2 (Prod-URL, CORS, CI) abgeschlossen via #388 + #390. Phase 3 offen: applicationId, Keystore-Signing, Icons. Tracking: #392. Naechste Session: User entscheidet applicationId, dann Signing einrichten. (2026-04-01)
- **Restrisiko**: Docker-Build mit OCR-Deps (#274) ungetestet. Auth-Test `test_login_empty_password` verifizieren. aware/naive Datetimes bei DB-Migration beachten. (2026-03-30)
- **Node.js 20 Deprecation**: Alle 6 Autopilot-Workflows zeigen Warning. Kein Blocker, mittelfristig Actions auf Node.js 22 aktualisieren. (2026-03-30)

## Meta

- Zuletzt geprueft: 2026-04-01
- Review bis: 2026-06-28
- Max Eintraege: 5
