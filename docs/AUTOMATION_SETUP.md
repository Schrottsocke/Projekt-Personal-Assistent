# Automation Setup Guide

Anleitung zur Einrichtung der GitHub-Automation für dieses Repository.

## Übersicht der Workflows

| Workflow | Trigger | Zweck |
|----------|---------|-------|
| `ci.yml` | Push/PR auf `main` | Lint (ruff) + Tests (pytest, 50% Coverage) |
| `auto-add-to-project.yml` | Issue/PR opened | Items automatisch ins GitHub Project einfügen |
| `stale.yml` | Täglich 06:00 UTC | Inaktive Issues/PRs markieren und schließen |
| `triage.yml` | Montags 08:00 UTC + manuell | Wöchentlicher Triage-Report als Issue |
| `repo-review.yml` | Mittwochs 08:00 UTC + manuell | Urgency-Check: P0/P1, CI-Health, stale PRs |
| `pr-labeler.yml` | PR opened/synchronize | Automatische Area- und Size-Labels für PRs |
| `issue-label-priority.yml` | Issue opened | Priority- und Area-Labels aus Template-Dropdown setzen |
| `label-sync.yml` | Manuell + Push auf `labels.yml` | Standard-Labels synchronisieren |

## 1. GitHub Project einrichten

### Project erstellen

1. Gehe zu `https://github.com/users/Schrottsocke/projects`
2. Klick auf **New project**
3. Wähle **Board** als Vorlage
4. Benenne es z.B. "DualMind Assistent"

### Projekt-Nummer finden

Die Nummer steht in der URL: `https://github.com/users/Schrottsocke/projects/X` → `X` ist die Nummer.

### Empfohlene Project-Felder (7 Felder)

| Feld | Typ | Werte |
|------|-----|-------|
| Status | Single Select | Backlog, Todo, In Progress, In Review, Done |
| Priority | Single Select | P0-critical, P1-high, P2-medium |
| Type | Single Select | Bug, Enhancement, Task, Incident, Refactoring, Quality, Documentation |
| Area | Single Select | Bot, API, App, Deploy, CI, Config, Tests, Docs |
| Size | Single Select | XS, S, M, L, XL |
| Source | Single Select | Manual, Autopilot, Dependabot, Triage |
| Sprint | Iteration | 2-Wochen-Zyklen |

> **Hinweis:** Type, Area und Size spiegeln die gleichnamigen Labels wider.
> Source hilft beim Filtern nach Herkunft (manuell erstellte vs. automatisch generierte Items).
> Sprint ist ein Iterations-Feld fuer zeitbasierte Planung.

### Project Built-in Automations

Im Project unter **Settings → Workflows** aktivieren:

| Workflow | Trigger | Status-Feld setzen auf |
|----------|---------|----------------------|
| Item added to project | Item hinzugefuegt | Backlog |
| Item closed | Issue/PR geschlossen | Done |
| Pull request merged | PR gemergt | Done |
| Code review approved | Review approved | In Review |

> **Hinweis:** Status manuell auf "Todo" setzen, wenn ein Item fuer den naechsten Sprint eingeplant wird.
> "In Progress" setzen, wenn die Arbeit beginnt.
> Die `/work-next` Claude Skill setzt den Branch-Namen als Indikator.

### Erweiterte Status-Automation (GraphQL API)

Falls eigene Workflows den Project-Status ändern sollen (z.B. bei Branch-Erstellung automatisch "In Progress" setzen):

- Erfordert `PROJECT_TOKEN` mit `project` Scope (bereits konfiguriert)
- GraphQL-Mutation: `updateProjectV2ItemFieldValue`
- Doku: https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects

Dies ist optional und nur für fortgeschrittene Automation nötig. Die Built-in Workflows decken die meisten Fälle ab.

## 2. Issue-Templates & PR-Template

### Issue-Templates

Alle Templates liegen in `.github/ISSUE_TEMPLATE/` und erzwingen strukturierte Eingaben:

| Template | Datei | Auto-Label | Pflichtfelder |
|----------|-------|------------|---------------|
| Bug Report | `bug_report.yml` | `bug` | Priorität, Bereich, Beschreibung |
| Feature Request | `feature_request.yml` | `enhancement` | Priorität, Bereich, Beschreibung |
| Aufgabe | `task.yml` | `task` | Priorität, Bereich, Beschreibung |
| Debugging / Incident | `incident.yml` | `incident` | Priorität, Bereich, Auswirkung, Symptome |
| Refactoring | `refactoring.yml` | `refactoring` | Priorität, Bereich, Umfang, Motivation |
| Qualität / Tests | `quality.yml` | `quality` | Priorität, Bereich, Art, Beschreibung |

Blank Issues sind deaktiviert (`config.yml`). Jedes Issue bekommt automatisch ein Typ-Label.

### PR-Template

Das PR-Template (`.github/PULL_REQUEST_TEMPLATE.md`) enthält Abschnitte für:

- **Ziel / Problem** mit `Fixes #`-Referenz
- **Betroffene Bereiche** als Checkbox-Liste
- **Änderungen** (Kurzbeschreibung)
- **Verifikation** (Lint, Tests, manuell)
- **Risiken / Rollback**
- **Checkliste** (main-Target, Secrets-Check)

### Backlog-Hygiene (Stale-Workflow)

Der Stale-Workflow (`stale.yml`) markiert Issues/PRs konservativ:

- **60 Tage** ohne Aktivität → `stale`-Label + Erinnerungskommentar
- **90 weitere Tage** (150 Tage gesamt) → automatisch geschlossen
- **Ausgenommen:** `P0-critical`, `P1-high`, `blocked`
- Nachrichten auf Deutsch, Wiedereröffnung jederzeit möglich

## 3. Repository Secrets & Variables

### Variables (Settings → Secrets and variables → Actions → Variables)

| Name | Wert | Beschreibung |
|------|------|--------------|
| `PROJECT_NUMBER` | `<Projekt-Nummer>` | Nummer des GitHub Projects |

### Secrets (Settings → Secrets and variables → Actions → Secrets)

| Name | Beschreibung | Erstellung |
|------|--------------|------------|
| `PROJECT_TOKEN` | Personal Access Token für Project-Zugriff | Siehe unten |

### Personal Access Token erstellen

1. Gehe zu `https://github.com/settings/tokens`
2. Klick auf **Generate new token (classic)**
3. Name: z.B. "Project Automation"
4. Scopes auswählen:
   - `project` (vollständig)
   - `repo` (für Issue/PR-Zugriff)
5. Token generieren und als `PROJECT_TOKEN` Secret speichern

> **Hinweis:** `GITHUB_TOKEN` wird automatisch bereitgestellt und braucht nicht manuell konfiguriert zu werden. Es reicht für die meisten Workflows, aber nicht für Project-Board-Zugriff.

## 4. Labels synchronisieren

Nach dem ersten Push dieses Branches:

1. Gehe zu **Actions → Label Sync**
2. Klick auf **Run workflow**
3. Alle Labels aus `.github/labels.yml` werden automatisch erstellt

Dies muss nur einmal ausgeführt werden. Danach werden Labels bei Änderungen an `labels.yml` automatisch synchronisiert.

## 5. Erste Nutzung

### Checkliste

- [ ] GitHub Project erstellt und Nummer notiert
- [ ] `PROJECT_NUMBER` als Repository Variable gesetzt
- [ ] `PROJECT_TOKEN` als Repository Secret gesetzt
- [ ] Label-Sync Workflow einmalig ausgeführt
- [ ] Project Built-in Automations aktiviert (Todo/Done)
- [ ] Test: Neues Issue über Template erstellt → erscheint im Project Board

### Claude Code Skills

| Skill | Beschreibung |
|-------|--------------|
| `/triage` | Repo-Gesundheitscheck (Lint, Tests, Issues, Code-Scan) |
| `/new-issue` | Ein GitHub Issue erstellen |
| `/work-next` | Nächstes Issue nach Priorität bearbeiten |
| `/closeout` | Nach Issue-Abschluss: gleiche/neue Session entscheiden |
| `/automation-check` | Automation-Gesundheitscheck (Workflows, Labels, Secrets) |

## 6. Troubleshooting

### Auto-Add-to-Project funktioniert nicht

- Prüfe ob `PROJECT_NUMBER` Variable korrekt gesetzt ist
- Prüfe ob `PROJECT_TOKEN` Secret vorhanden ist und `project` Scope hat
- Token darf nicht abgelaufen sein

### Labels fehlen nach PR-Labeling

- Label-Sync Workflow ausführen (erstellt fehlende Labels)
- Prüfe `.github/labeler.yml` für korrekte Pfad-Zuordnungen

### Triage-Report wird nicht erstellt

- Prüfe ob der Workflow unter Actions → Triage Report aktiv ist
- Manuell triggern: Actions → Triage Report → Run workflow

## 7. Autopilot-Schicht

Die Autopilot-Schicht erkennt Handlungsbedarf autonom und erstellt GitHub Issues.
Sie fuehrt keine Produktcode-Aenderungen durch.

| Workflow | Trigger | Zweck |
|----------|---------|-------|
| `autopilot-review.yml` | Taeglich 07:00 UTC + manuell | Taegliches Dashboard: CI, P0/P1, PRs, Labels, Memory |
| `autopilot-issue-sync.yml` | Freitag 08:00 UTC + manuell | Issues erstellen/schliessen bei klaren Befunden |
| `autopilot-reminders.yml` | Montag 07:30 UTC + manuell | P0-Reminder, needs-review Labels |

Alle Autopilot-Issues tragen das Label `autopilot`.

### Einrichtung

1. Label-Sync Workflow ausfuehren (erstellt `autopilot` Label)
2. Keine zusaetzlichen Secrets noetig

### Test

1. `autopilot-review.yml` mit `dry_run: true` manuell ausfuehren
2. `autopilot-issue-sync.yml` mit `dry_run: true` manuell ausfuehren
3. In Claude Code Session: `/autopilot-status` ausfuehren

Details: siehe `docs/autopilot-policy.md`

## 8. Aktueller Einrichtungsstatus (Stand 2026-03-29)

### Erledigt

- [x] `.github/labels.yml` mit 44 Labels definiert
- [x] `label-sync.yml` Workflow erstellt
- [x] `auto-add-to-project.yml` Workflow erstellt
- [x] `issue-label-priority.yml` Workflow erstellt (Priority + Area aus Templates)
- [x] `pr-labeler.yml` + `.github/labeler.yml` konfiguriert
- [x] 7 Issue-Templates erstellt (Bug, Feature, Task, Incident, Refactoring, Quality + config)
- [x] PR-Template erstellt
- [x] `stale.yml` konfiguriert (60d stale, 150d close, P0/P1 ausgenommen)
- [x] Autopilot-Workflows erstellt (review, issue-sync, reminders)
- [x] `ci.yml` + `flutter.yml` konfiguriert
- [x] `config/project-fields.md` – Feldmodell dokumentiert
- [x] 10 Arbeitspakete als GitHub Issues angelegt (#252–#261)
- [x] CODEOWNERS konfiguriert (@schrottsocke)

### Noch offen (manuelle Schritte)

- [ ] **Label-Sync Workflow ausfuehren** → Actions → Label Sync → Run workflow (Issue #252)
- [ ] **GitHub Project Board erstellen** → github.com/users/Schrottsocke/projects (Issue #253)
- [ ] **PROJECT_NUMBER als Repository Variable setzen** (Issue #254)
- [ ] **PROJECT_TOKEN als Repository Secret erstellen** (Issue #254)
- [ ] **Project Built-in Automations aktivieren** (Item added → Backlog, etc.)
- [ ] **Autopilot-Workflows im Dry-Run testen** (Issue #261)

### Naechste Schritte (empfohlene Reihenfolge)

1. Label-Sync ausfuehren (#252) – Voraussetzung fuer alles andere
2. Project Board erstellen + konfigurieren (#253)
3. PROJECT_NUMBER/TOKEN setzen (#254) – danach funktioniert auto-add-to-project
4. Autopilot-Workflows Dry-Run (#261) – validiert die gesamte Automation
