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
| `label-sync.yml` | Manuell + Push auf `labels.yml` | Standard-Labels synchronisieren |

## 1. GitHub Project einrichten

### Project erstellen

1. Gehe zu `https://github.com/users/Schrottsocke/projects`
2. Klick auf **New project**
3. Wähle **Board** als Vorlage
4. Benenne es z.B. "DualMind Assistent"

### Projekt-Nummer finden

Die Nummer steht in der URL: `https://github.com/users/Schrottsocke/projects/X` → `X` ist die Nummer.

### Empfohlene Project-Felder

| Feld | Typ | Werte |
|------|-----|-------|
| Status | Single Select | Todo, In Progress, Done |
| Priority | Single Select | P0-critical, P1-high, P2-medium |

### Project Built-in Automations

Im Project unter **Settings → Workflows** aktivieren:

| Workflow | Trigger | Status-Feld setzen auf |
|----------|---------|----------------------|
| Item added to project | Item hinzugefügt | Todo |
| Item closed | Issue/PR geschlossen | Done |
| Pull request merged | PR gemergt | Done |
| Code review approved | Review approved | Done |

> **Hinweis:** Für "In Progress" gibt es keine automatische Built-in-Regel.
> Empfehlung: Status manuell auf "In Progress" setzen, wenn die Arbeit beginnt.
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
