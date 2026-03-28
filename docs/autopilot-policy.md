# Autopilot Policy

Die Autopilot-Schicht erkennt Handlungsbedarf autonom und dokumentiert ihn als GitHub Issues.
Sie fuehrt **keine Produktcode-Aenderungen** durch.

## Was autonom erkannt wird

| Befund | Quelle | Schwelle |
|--------|--------|----------|
| CI-Failures | Workflow-Runs (letzte 30) | >3 Failures |
| P0-critical ueberfaellig | Issues mit Label `P0-critical` | >3 Tage offen |
| P1-high ueberfaellig | Issues mit Label `P1-high` | >14 Tage offen |
| Stale PRs | PRs ohne Aktivitaet | >7 Tage (Review), >14 Tage (Issue-Sync) |
| PRs ohne Review | Offene PRs ohne Review-Decision | sofort |
| Issues ohne Labels | Offene Issues ohne Labels | >3 Issues |
| Issues ohne Area-Label | Offene Issues ohne `area/*` Label | gemeldet |
| Memory-Review faellig | `Review bis`-Datum in memory/*.md | Datum ueberschritten |

## Was autonom angestossen werden darf

- GitHub Issues erstellen (Label `autopilot`)
- Kommentare auf bestehende Issues/PRs schreiben
- Labels setzen (`needs-review`)
- Bestehende Autopilot-Issues schliessen (wenn Befund geloest)
- Status-Reports als Issue-Kommentare

## Was manuell bleibt

- Produktcode aendern (`src/`, `api/`, `app/`, `main.py`)
- API-Endpunkte, Auth, Datenbank, Deployment
- PRs erstellen oder mergen
- Secrets oder Konfiguration aendern
- `.env`, Tokens, Credentials
- Branches erstellen oder loeschen
- Deployments ausloesen
- Memory-Dateien aendern (nur Signal, Review per `/memory-review`)

## Trigger-Uebersicht

| Workflow | Schedule | Manuell | Zweck |
|----------|----------|---------|-------|
| `autopilot-review.yml` | Taeglich 07:00 UTC | `workflow_dispatch` (dry_run) | Dashboard: CI, P0/P1, PRs, Labels, Memory |
| `autopilot-issue-sync.yml` | Freitag 08:00 UTC | `workflow_dispatch` (dry_run) | Issues erstellen/schliessen bei klaren Befunden |
| `autopilot-reminders.yml` | Montag 07:30 UTC | `workflow_dispatch` (dry_run) | P0-Reminder, needs-review Labels |

### Zusammenspiel mit bestehenden Workflows

| Workflow | Schedule | Manuell | Rolle |
|----------|----------|---------|-------|
| `triage.yml` | Montag 08:00 UTC | `workflow_dispatch` (dry_run) | Woechentlicher Issue/PR-Bericht |
| `repo-review.yml` | Mittwoch 08:00 UTC | `workflow_dispatch` (dry_run) | Woechentlicher Health-Check |
| `stale.yml` | Taeglich 06:00 UTC | `workflow_dispatch` (dry_run) | Stale-Markierung und Auto-Close |

Die Autopilot-Workflows **ergaenzen** die bestehenden Workflows:
- `autopilot-review` liefert ein taegliches Dashboard (triage/repo-review sind woechentlich)
- `autopilot-issue-sync` erstellt actionable Issues aus Befunden (triage/repo-review erstellen nur Reports)
- `autopilot-reminders` setzt aktiv Labels und Kommentare (stale.yml nur fuer inaktive Issues)

## Sicherheitsgrenzen

1. Alle Autopilot-Workflows nutzen nur `GITHUB_TOKEN` (keine zusaetzlichen Secrets)
2. Permissions sind minimal: `contents: read`, `issues: write`, `pull-requests: read/write`, `actions: read`
3. Kein `contents: write` – es werden keine Dateien im Repo geaendert
4. Keine `deployments`-Permission
5. Alle Issues werden mit Label `autopilot` markiert (leicht filterbar)
6. Duplikat-Schutz: vor Issue-Erstellung wird nach existierendem Issue mit gleichem Titel gesucht
7. Auto-Close: Issues werden geschlossen wenn der Befund sich erledigt hat

## Claude Code Skills

| Skill | Zweck |
|-------|-------|
| `/autopilot-status` | Zeigt aktuellen Autopilot-Zustand |
| `/automation-check` | Prueft Workflow-Konfiguration |
| `/memory-review` | Fuehrt Memory-Review durch (manuell) |
| `/triage` | Repo-Gesundheitscheck |

## Test-Anleitung

### Dry-Run-Verhalten pro Workflow

| Workflow | Bei `dry_run: true` | Unterdrueckt |
|----------|---------------------|--------------|
| `autopilot-review` | Report mit Score im Log | Issue erstellen/updaten, Label anlegen |
| `autopilot-issue-sync` | Befunde + Schwellen im Log | Issues erstellen/schliessen, Label anlegen |
| `autopilot-reminders` | Betroffene Issues/PRs + Aktionszaehler im Log | Kommentare schreiben, Labels setzen |
| `repo-review` | Report im Log | Issue erstellen/updaten, Label anlegen |
| `triage` | Report im Log | Issue erstellen/updaten, Label anlegen |
| `stale` | Debug-Output (actions/stale) | Stale-Markierung, Auto-Close |

### Erster Test (Dry Run)

1. **Label erstellen:** Label-Sync Workflow manuell ausfuehren (einmalig, kein dry_run noetig)
2. **autopilot-review testen (empfohlener Einstieg):**
   - GitHub UI: Actions → "Autopilot Review" → "Run workflow"
   - Branch: `main`
   - Input: `dry_run` Checkbox aktivieren
   - Klick: "Run workflow"
   - Erwartung: Step "Dry run output" zeigt Report mit Score und Metriken
   - Pruefen: Kein neues Issue mit Label `autopilot`, kein Label angelegt
3. **autopilot-issue-sync testen:**
   - Actions → "Autopilot Issue Sync" → Run workflow → dry_run: true
   - Erwartung: Befunde (CI-Failures, Stale PRs, Unlabeled, Memory) im Log
4. **autopilot-reminders testen:**
   - Actions → "Autopilot Reminders" → Run workflow → dry_run: true
   - Erwartung: Betroffene Issues/PRs gelistet, Aktionszaehler, "UNTERDRUECKT (dry_run)"
5. **stale testen:**
   - Actions → "Stale Issues" → Run workflow → dry_run: true
   - Erwartung: Debug-Output zeigt welche Issues/PRs markiert wuerden
6. **repo-review und triage:**
   - Jeweils mit dry_run: true testen
   - Erwartung: Report im Log, kein Issue erstellt

### Produktiv-Test

1. `autopilot-review.yml` manuell ohne dry_run ausfuehren
2. Pruefen ob ein Issue mit Label `autopilot` erstellt wird
3. `autopilot-issue-sync.yml` manuell ohne dry_run ausfuehren
4. Pruefen ob Issues fuer aktive Befunde erstellt werden
5. Erneut ausfuehren → pruefen dass keine Duplikate entstehen
6. In Claude Code Session: `/autopilot-status` ausfuehren

## Manuelle GitHub-Einstellungen

- **Label-Sync einmal ausfuehren** damit das `autopilot` Label erstellt wird
- Keine zusaetzlichen Secrets oder Variables noetig
- Alle Workflows nutzen den Standard `GITHUB_TOKEN`
