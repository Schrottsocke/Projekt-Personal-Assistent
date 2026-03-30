# Handoffs

Session-Uebergaben, offene Faeden zwischen Sessions, naechste Schritte.
Wird aggressiv bereinigt - nur die letzten Eintraege behalten.

## Eintraege

- **Flutter E2E (#260)**: PR #333 gemergt = Android/iOS Platforms, pubspec.lock, Permissions, Network Config. Naechster Schritt: User testet manuell auf Emulator/Geraet (API starten → flutter run → Login → Dashboard → Chat). Danach #260 schliessen. (2026-03-30)
- **Flutter Deploy-Readiness Gap-Analyse**: Vollstaendiger Plan in `/root/.claude/plans/harmonic-splashing-hejlsberg.md` – Kurzfassung unten in app.md. Offene Entscheidungen: Produktions-URL, App-Identifier, Signing, Firebase ja/nein. (2026-03-30)
- **Restrisiko**: Docker-Build mit OCR-Deps (#274) ungetestet. Auth-Test `test_login_empty_password` verifizieren. aware/naive Datetimes bei DB-Migration beachten. (2026-03-30)
- **Node.js 20 Deprecation**: Alle 6 Autopilot-Workflows zeigen Warning. Kein Blocker, mittelfristig Actions auf Node.js 22 aktualisieren. (2026-03-30)

## Meta

- Zuletzt geprueft: 2026-03-30
- Review bis: 2026-06-28
- Max Eintraege: 5
