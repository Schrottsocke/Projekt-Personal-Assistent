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
- Memory-Architektur: BaseMemoryService + zwei Spezialisierungen:
  - `src/memory/base_memory_service.py` – gemeinsame mem0-Logik (Basis)
  - `src/memory/memory_service.py` – BotMemoryService (+ SQLite Facts, Onboarding)
  - `src/services/memory_service.py` – ApiMemoryService (+ add_fact)
  - Beide exportieren `MemoryService` als Alias fuer Rueckwaertskompatibilitaet
- `.env` enthält Secrets. Niemals committen oder ungefragt ändern.

## Memory

- `CLAUDE.md` – Regeln und Workflow (selten aendern)
- `MEMORY.md` – Index fuer Gelerntes aus Sessions
- `memory/` – thematische Erkenntnisse (Automation, Debugging, App, Handoffs)
- `memory/` ist Dokumentation fuer Claude Code, NICHT der Python-Service (`src/memory/`)
- Siehe `MEMORY.md` fuer Speicher-Kriterien und Wachstumsschutz
- `/closeout` fuehrt Memory-Check automatisch inline aus (kein Zusatzprompt noetig)
- `/save-memory` nur fuer explizite Speicherung ausserhalb von Closeout

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

## Batch-Modus (Parallel-Issues)

Bei >= 4 offenen Issues standardmaessig die Parallel-Batch-Methode verwenden:
1. Alle offenen Issues sichten
2. In moeglichst unabhaengige Batches gruppieren (kein File in mehr als einem Batch)
3. Jeden Batch in einem isolierten Worktree parallel bearbeiten
4. Pro Batch ein Branch, ein Commit, ein PR mit allen `Fixes #...`
5. PRs konfliktfrei in beliebiger Reihenfolge mergen

Kriterien fuer Batch-Bildung: Datei-Ueberschneidungen minimieren, Modulzugehoerigkeit beachten.
Bei < 4 Issues oder auf User-Wunsch: Einzelmodus (ein Issue pro Durchlauf).

Details: `docs/issue-handling-playbook.md`

## Orchestrierung

Bei groesseren oder mehrteiligen Auftraegen arbeitet Claude zuerst als Orchestrator:

1. **Gesamtanalyse**: Umfang, betroffene Module, Abhaengigkeiten erfassen
2. **Plan**: Einen einzigen, konkreten Umsetzungsplan formulieren
3. **Zerlegung**: Arbeit in Tracks/Cluster aufteilen (z.B. Core, API, App, Infra, Docs)
4. **Parallelisierung**: Nur bei sauber getrennten Dateien und ohne Abhaengigkeiten
5. **Umsetzung**: Pro Track ein Agent in isoliertem Worktree
6. **Verifikation**: Ergebnisse pruefen, Konflikte ausschliessen

Regeln:
- Kritische Zentraldateien (`main.py`, `config/settings.py`, `base_memory_service.py`) sequentiell behandeln
- Dry-Run bei riskanten Automationen bevorzugen (z.B. Label-Sync, Workflow-Aenderungen)
- Kein Track darf Dateien eines anderen Tracks aendern
- Bei Unsicherheit ueber Abhaengigkeiten: sequentiell statt parallel

Details: `docs/orchestration-playbook.md`

## Commit- und PR-Regeln

- Commit-Format: `fix(scope): kurze beschreibung (#<issue>)`
- PR muss gegen den Default-Branch gehen
- PR-Beschreibung soll enthalten: `Fixes #<issue>`
- Ohne `Fixes #<issue>` ist das Issue nicht automatisch abschließbar
- Keine PR gegen Neben- oder Arbeits-Branches erstellen, wenn das Ziel automatisches Issue-Closing ist

## Debugging

Vorgehen: Reproduzieren → Hypothese → Experiment → Fix.
Kein Fix ohne plausible Root-Cause. Bei unklarer Ursache parallele Explore-Agents nutzen.
Bei >= 4 Bugs: Batch-Modus (siehe Batch-Modus Abschnitt).

Priorisierung nach Schicht:
1. Start-/Importfehler
2. Konfiguration
3. Backend-Runtime
4. API/Auth
5. App/API-Integration
6. Deployment

Details: `docs/debug-playbook.md`

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

## Entscheidung nach jedem abgeschlossenen Issue

Nach jedem abgeschlossenen Issue triff aktiv genau eine Entscheidung:

### Option A: In derselben Session weitermachen
Nur erlaubt, wenn alle folgenden Punkte erfüllt sind:
- das aktuelle Issue ist vollständig abgeschlossen
- das nächste Issue betrifft denselben Bereich oder eng verwandte Dateien
- kein Kontextdrift erkennbar ist
- keine neue breite Analyse nötig ist
- das nächste Issue ist klein genug für einen weiteren klaren Durchlauf

### Option B: Session beenden und neues Issue in neuer Session
Bevorzugt, wenn einer der folgenden Punkte zutrifft:
- das aktuelle Issue war größer oder über mehrere Dateien/Module verteilt
- das nächste Issue betrifft einen anderen Bereich des Projekts
- der Kontext ist bereits lang oder unübersichtlich geworden
- in der Session gab es Plan-Loops, Drift oder Wiederholungen
- für das nächste Issue wäre eine frische Analyse sinnvoller

## Entscheidungsregel

Nach Abschluss eines Issues tue genau eines von zwei Dingen:
1. genau ein weiteres kleines, verwandtes Issue in derselben Session beginnen
2. die Session sauber abschließen und ein nächstes Issue für eine neue Session empfehlen

Nicht ohne Entscheidung einfach mit dem nächsten Issue anfangen.

Im Zweifel immer **neue Session bevorzugen**.

## Handoff bei Sessionende

Wenn du empfiehlst, die Session zu beenden:
- fasse den Abschluss des aktuellen Issues kurz zusammen
- nenne das empfohlene nächste Issue
- nenne die ersten Dateien oder Bereiche für die nächste Session
- stoppe danach

Nicht in derselben Antwort schon mit dem nächsten Issue beginnen.

## Skills

Verfuegbare Claude Code Skills:

- `/triage` – Repo-Gesundheitscheck: Lint, Tests, offene Issues, neue Issues vorschlagen
- `/new-issue` – Genau ein GitHub Issue erstellen oder als Entwurf ausgeben
- `/work-next` – Naechstes Issue nach Prioritaet bearbeiten (kompletter GitHub-Flow)
- `/closeout` – Nach Issue-Abschluss: gleiche Session oder neue Session entscheiden
- `/automation-check` – Automation-Gesundheitscheck: Workflows, Labels, Templates, Secrets
- `/autopilot-status` – Status der Autopilot-Schicht: Workflows, Issues, Memory-Review
- `/save-memory` – Erkenntnisse aus der Session in memory/ speichern
- `/memory-review` – Memory-Dateien reviewen, kuerzen, archivieren

## Ende

Kurz melden:
- **Geändert**
- **Ergebnis**
- **Prüfung**
- **GitHub:** Branch, Push, PR, Merge, Issue-Status
- **Nächstes Issue**
- **Empfehlung:** gleiche Session / neue Session
- **Grund**
- **Offen**
