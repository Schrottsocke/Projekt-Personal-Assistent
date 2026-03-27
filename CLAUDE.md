# CLAUDE.md

DualMind Personal Assistant:
- Bots: `main.py`
- Backend: `src/`
- API: `api/`
- App: `app/`
- Config: `config/settings.py`
- Deploy: `deploy/`

Wichtige Dateien:
- `main.py`
- `api/main.py`
- `api/api_main.py`
- `app/lib/main.dart`
- `README.md`
- `CHANGELOG.md`
- `.env.example`

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

## GitHub-Automation

Bei Issue-Arbeit ist ein lokaler Branch oder lokaler Commit nicht das Endergebnis.

Standardablauf pro Issue:
1. Issue auswählen
2. Branch anlegen: `fix/<issue>-kurzbeschreibung`
3. Änderung umsetzen
4. kurz verifizieren
5. Commit erstellen
6. Branch zum Remote pushen
7. Pull Request gegen den Default-Branch erstellen
8. In PR-Titel oder PR-Beschreibung ein Closing-Keyword verwenden: `Fixes #<issue>`
9. PR mergen
10. prüfen, ob das Issue automatisch geschlossen wurde

Regeln:
- Nicht nach dem lokalen Commit stoppen.
- Nicht nur lokal arbeiten, wenn GitHub-Zugriff verfügbar ist.
- Ein Issue gilt erst als abgeschlossen, wenn die Änderung im Default-Branch ist oder der User etwas anderes vorgibt.
- Wenn Push, PR oder Merge nicht möglich sind, die genaue Blockade sofort nennen.
- Wenn Auto-Close nicht greift, prüfen ob der PR wirklich den Default-Branch targetet.
- Wenn das automatische Schließen deaktiviert ist oder nicht funktioniert, Issue manuell schließen und kurz begründen.

## Commit- und PR-Regeln

- Commit-Format: `fix(scope): kurze beschreibung (#<issue>)`
- PR muss gegen den Default-Branch gehen
- PR-Beschreibung soll enthalten: `Fixes #<issue>`
- Ohne `Fixes #<issue>` ist das Issue nicht automatisch abschließbar
- Keine PR gegen Neben- oder Arbeits-Branches erstellen, wenn das Ziel automatisches Issue-Closing ist

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

## Definition of Done bei Issue-Arbeit

Ein Issue ist erst fertig, wenn:
- die Änderung implementiert ist
- die Änderung kurz verifiziert ist
- der Branch gepusht ist
- ein PR gegen den Default-Branch existiert
- der PR `Fixes #<issue>` enthält
- der PR gemergt wurde oder klar zur User-Freigabe bereit ist
- das Issue geschlossen wurde oder nachweislich automatisch geschlossen wird

## Ende

Kurz melden:
- **Geändert**
- **Ergebnis**
- **Prüfung**
- **GitHub:** Branch, Push, PR, Merge, Issue-Status
- **Offen**
