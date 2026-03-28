---
name: automation-check
description: "Prüfe den Zustand aller GitHub-Automation-Workflows, Labels und Konfiguration"
---

# Automation Check – Gesundheitscheck der Repo-Automation

Prüfe ob alle GitHub-Workflows, Labels und Automation-Konfigurationen korrekt eingerichtet sind.

## Ablauf

### 1. Workflow-Dateien prüfen

Lies alle Dateien in `.github/workflows/` und prüfe:
- Sind alle erwarteten Workflows vorhanden? (`ci.yml`, `auto-add-to-project.yml`, `stale.yml`, `triage.yml`, `pr-labeler.yml`, `label-sync.yml`)
- Ist die YAML-Syntax korrekt? (grundlegende Strukturprüfung)
- Stimmen die Trigger-Events? (schedule, workflow_dispatch, push, pull_request)

### 2. Label-Konfiguration prüfen

Lies `.github/labels.yml` und prüfe:
- Sind alle Priority-Labels definiert? (`P0-critical`, `P1-high`, `P2-medium`)
- Sind alle Area-Labels definiert? (`area/bot`, `area/api`, `area/app`, etc.)
- Sind alle Size-Labels definiert? (`size/XS` bis `size/XL`)
- Stimmen die Farben und Beschreibungen?

### 3. Labeler-Konfiguration prüfen

Lies `.github/labeler.yml` und prüfe:
- Sind alle Hauptverzeichnisse abgedeckt? (`src/`, `api/`, `app/`, `deploy/`, `tests/`, `config/`)
- Stimmen die Glob-Patterns?

### 4. Issue-Templates prüfen

Prüfe `.github/ISSUE_TEMPLATE/`:
- Sind Templates vorhanden? (`bug_report.yml`, `feature_request.yml`, `task.yml`)
- Ist `config.yml` vorhanden? (blank issues deaktiviert)
- Haben alle Templates ein Priority-Dropdown?

### 5. Letzte Workflow-Runs prüfen

Nutze die GitHub MCP Tools um die letzten Workflow-Runs abzufragen:
- Sind alle Workflows kürzlich gelaufen?
- Gibt es fehlgeschlagene Runs?
- Wann war der letzte erfolgreiche Triage-Report?

### 6. Bericht

Gib einen strukturierten Bericht aus:

```
## Automation-Check

### Workflows
| Workflow | Datei vorhanden | Trigger korrekt | Letzter Run |
|----------|----------------|-----------------|-------------|
| CI       | ✅/❌          | ✅/❌          | Datum/Status |
| ...      | ...            | ...             | ...         |

### Labels
- Definiert in labels.yml: X Labels
- Priority: ✅/❌
- Area: ✅/❌
- Size: ✅/❌

### Issue-Templates
- Bug Report: ✅/❌
- Feature Request: ✅/❌
- Task: ✅/❌
- Blank Issues deaktiviert: ✅/❌

### Fehlende Einrichtung
- [ ] Aktion 1 ...
- [ ] Aktion 2 ...

### Empfehlungen
1. ...
```

## Regeln

- Keine Änderungen vornehmen. Nur analysieren und berichten.
- Anti-Loop: Bericht genau einmal ausgeben.
- Bei fehlenden GitHub-Secrets/Variables: klar benennen was fehlt und auf `docs/AUTOMATION_SETUP.md` verweisen.
- Maximal 5 Empfehlungen.
