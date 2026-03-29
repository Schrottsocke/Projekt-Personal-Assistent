# GitHub Project Board – Feldmodell

Dieses Dokument definiert die Felder, Werte und Automationen fuer das GitHub Project Board
des DualMind Personal Assistant Repos.

Es dient als **Single Source of Truth** fuer die manuelle Einrichtung oder spaetere API-Automation.

## Projekt-Metadaten

| Eigenschaft | Wert |
|-------------|------|
| Name | DualMind Assistent |
| Typ | Board |
| Scope | User-Project (github.com/users/Schrottsocke/projects) |
| Repo | schrottsocke/projekt-personal-assistent |
| Variable | `PROJECT_NUMBER` (Repository Variable) |
| Secret | `PROJECT_TOKEN` (PAT mit `project` + `repo` Scope) |

## Felder

### Status (Single Select) – Pflichtfeld

| Wert | Bedeutung | Automation |
|------|-----------|------------|
| Backlog | Item erkannt, nicht eingeplant | Built-in: Item added → Backlog |
| Todo | Fuer naechsten Sprint eingeplant | Manuell setzen |
| In Progress | Branch existiert, Arbeit laeuft | Manuell setzen (oder per Workflow) |
| In Review | PR erstellt, wartet auf Merge | Manuell oder per Review-Approved Workflow |
| Done | PR gemergt, Issue geschlossen | Built-in: Item closed → Done, PR merged → Done |

### Priority (Single Select)

| Wert | Bedeutung | SLA |
|------|-----------|-----|
| P0-critical | System nicht nutzbar | Sofort bearbeiten |
| P1-high | Wichtige Funktion beeintraechtigt | Naechste Session |
| P2-medium | Stoerend, Workaround vorhanden | Wenn Kapazitaet frei |

Korrespondiert mit Labels: `P0-critical`, `P1-high`, `P2-medium`

### Track (Single Select)

| Wert | Dateien | Label |
|------|---------|-------|
| Core | `main.py`, `config/settings.py`, `src/memory/` | `track:core` |
| API | `api/`, `src/services/` (API-relevante) | `track:api` |
| App | `app/lib/` | `track:app` |
| Infra | `deploy/`, `.github/workflows/`, `Dockerfile` | `track:infra` |
| Docs | `docs/`, `README.md`, `CHANGELOG.md` | `track:docs` |
| QA | `tests/`, `.github/workflows/ci.yml` | `track:qa` |
| Security | Auth-relevante Dateien, `.env.example` | `track:security` |
| Workflow | `.github/ISSUE_TEMPLATE/`, `.github/labels.yml` | `track:workflow` |

### Risk (Single Select)

| Wert | Kriterium | Label |
|------|-----------|-------|
| Low | Isolierte Aenderung, ein Modul | `risk:low` |
| Medium | Mehrere Module, moderate Komplexitaet | `risk:medium` |
| High | Zentraldateien, Auth, Deploy, Migrationen | `risk:high` |

### Execution Mode (Single Select)

| Wert | Bedeutung | Label |
|------|-----------|-------|
| Parallel | Kann parallel mit anderen Issues bearbeitet werden | `exec:parallel` |
| Sequential | Muss sequentiell bearbeitet werden | `exec:sequential` |

### Batch (Text)

Freitext-Feld fuer die Batch-Zuordnung bei paralleler Bearbeitung.
Format: `Batch <N> – <Beschreibung>` (z.B. "Batch 1 – API Layer")

Regeln:
- Kein File in mehr als einem Batch
- Batches muessen konfliktfrei mergebar sein
- Batch-Zuordnung wird pro Orchestrierungszyklus neu vergeben

### Blocked By (Text)

Freitext-Feld fuer Blocker-Dokumentation.
Format: `#<issue>` oder Freitext-Beschreibung (z.B. "#42 muss zuerst gemergt werden")

### Type (Single Select)

| Wert | Label |
|------|-------|
| Bug | `bug` |
| Enhancement | `enhancement` |
| Task | `task` |
| Incident | `incident` |
| Refactoring | `refactoring` |
| Quality | `quality` |
| Documentation | `documentation` |

### Area (Single Select)

| Wert | Label |
|------|-------|
| Bot | `area/bot` |
| API | `area/api` |
| App | `area/app` |
| Deploy | `area/deploy` |
| CI | `area/ci` |
| Config | `area/config` |
| Tests | `area/tests` |
| Docs | `area/docs` |

### Size (Single Select)

| Wert | Kriterium | Label |
|------|-----------|-------|
| XS | < 10 Zeilen | `size/XS` |
| S | < 50 Zeilen | `size/S` |
| M | < 200 Zeilen | `size/M` |
| L | < 500 Zeilen | `size/L` |
| XL | 500+ Zeilen | `size/XL` |

### Source (Single Select)

| Wert | Bedeutung |
|------|-----------|
| Manual | Manuell erstellt |
| Autopilot | Von Autopilot-Workflows erstellt |
| Triage | Von Triage/Review-Workflows erstellt |

## Built-in Project Automations

Diese Automationen in den Project Settings aktivieren:

| Workflow | Trigger | Status setzen auf |
|----------|---------|-------------------|
| Item added to project | Item hinzugefuegt | Backlog |
| Item closed | Issue/PR geschlossen | Done |
| Pull request merged | PR gemergt | Done |
| Code review approved | Review approved | In Review |

## Einrichtungsschritte

1. Project erstellen: github.com/users/Schrottsocke/projects → New project → Board
2. Felder anlegen (siehe Tabellen oben)
3. Built-in Automations aktivieren (siehe Tabelle oben)
4. Projekt-Nummer aus URL ablesen
5. `PROJECT_NUMBER` als Repository Variable setzen (Settings → Variables → Actions)
6. `PROJECT_TOKEN` als Repository Secret erstellen (PAT mit `project` + `repo` Scope)
7. Label-Sync Workflow einmalig ausfuehren (Actions → Label Sync → Run workflow)
8. Test: Neues Issue erstellen → erscheint automatisch im Project Board

## Zusammenspiel mit Labels

Jedes Project-Feld hat korrespondierende GitHub Labels (siehe Label-Spalten oben).
Labels werden automatisch gesetzt durch:
- **Issue-Templates:** Priority + Area (via `issue-label-priority.yml`)
- **PR-Labeler:** Area + Size (via `pr-labeler.yml`)
- **Manuell:** Track, Risk, Execution Mode

Die Project-Felder koennen manuell oder per GraphQL-API synchron zu den Labels gehalten werden.
Fuer den Anfang reicht manuelle Pflege – Labels sind die primaere Quelle.

## Referenzen

- `docs/orchestration-playbook.md` – Orchestrierungslogik und Track-Definitionen
- `docs/AUTOMATION_SETUP.md` – Setup-Anleitung fuer Workflows und Project
- `.github/labels.yml` – Label-Definitionen (44 Labels)
- `docs/autopilot-policy.md` – Was autonom automatisiert werden darf
