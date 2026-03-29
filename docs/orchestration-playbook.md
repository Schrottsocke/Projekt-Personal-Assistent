# Orchestrierungs-Playbook

Wie Claude dieses Repo bei groesseren Auftraegen orchestriert.

## Zielbild

Claude arbeitet als Orchestrator: Zuerst Gesamtbild erfassen, dann planen, dann zerlegen, dann parallel umsetzen. Nie direkt losarbeiten bei mehrteiligen Aufgaben.

## Ablauf

### 1. Analyse

- Alle betroffenen Dateien und Module identifizieren
- Abhaengigkeiten zwischen Dateien erkennen
- Risiken einschaetzen (Zentraldateien, Shared State, Auth, Deploy)
- Umfang pro Teilaufgabe grob bewerten

### 2. Clusterung in Tracks

Arbeit in logische Tracks aufteilen:

| Track | Typische Dateien | Beispiele |
|-------|-----------------|-----------|
| Core | `main.py`, `config/settings.py`, `src/memory/` | Startlogik, Konfiguration, Memory-Architektur |
| API | `api/`, `src/services/` (API-relevante) | Router, Schemas, Auth, API-Services |
| App | `app/lib/` | Flutter-Widgets, Screens, State |
| Infra | `deploy/`, `.github/workflows/`, `Dockerfile` | CI/CD, Deployment, Docker |
| Docs | `docs/`, `README.md`, `CHANGELOG.md` | Playbooks, Guides, Changelog |
| QA | `tests/`, `.github/workflows/ci.yml` | Tests, Lint-Regeln, Coverage |
| Security | Auth-relevante Dateien, `.env.example` | Token-Handling, Rate-Limiting |
| Workflow | `.github/ISSUE_TEMPLATE/`, `.github/labels.yml` | Templates, Labels, Automation |

Regeln:
- Kein File in mehr als einem Track
- Tracks mit gemeinsamen Dateien zusammenlegen oder sequentiell bearbeiten
- Kleine Tracks (< 3 Dateien) koennen zusammengelegt werden

### 3. Parallelisierungsplan

Entscheidung pro Track: parallel oder sequentiell.

| Kriterium | Parallel | Sequentiell |
|-----------|----------|-------------|
| Dateien ueberschneidungsfrei | ja | – |
| Keine Import-Abhaengigkeit zwischen Tracks | ja | – |
| Zentraldateien betroffen | – | ja |
| Shared State (DB, Config, Memory) | – | ja |
| Riskante Automation (Workflows, Deploy) | – | ja |
| Einfache, isolierte Aenderungen | ja | – |

Zentraldateien (immer sequentiell):
- `main.py`
- `config/settings.py`
- `src/memory/base_memory_service.py`
- `src/handlers/__init__.py`
- `api/main.py`

### 4. Arbeitspakete

Pro Track ein Arbeitspaket definieren:

```
Track: <Name>
Issues: #1, #2, ...
Dateien: <Liste>
Abhaengigkeiten: keine / wartet auf Track X
Execution: parallel / sequentiell
Risk: low / medium / high
Branch: fix/<track>-<kurzbeschreibung>
```

### 5. Umsetzung

- Parallele Tracks: je ein Agent in isoliertem Worktree (gleichzeitig starten)
- Sequentielle Tracks: nacheinander im Hauptkontext
- Pro Track: Branch erstellen, aendern, committen, pushen
- Dry-Run bei riskanten Aenderungen (Workflows, Label-Sync, Deploy)

### 6. Verifikation

- Syntax-Check aller geaenderten Dateien
- Keine Merge-Konflikte zwischen parallelen Branches
- PRs erstellen, `Fixes #<issue>` in Beschreibung
- PRs in beliebiger Reihenfolge mergebar

## Risiko-Management

| Risiko | Massnahme |
|--------|-----------|
| Merge-Konflikt | Tracks mit Datei-Ueberschneidung zusammenlegen |
| Zentraldatei geaendert | Sequentiell bearbeiten, andere Tracks warten |
| Workflow-Aenderung | Dry-Run zuerst, manuell pruefen |
| Auth/Security-Aenderung | Stop-Regel: Rueckfrage an User |
| Unklare Abhaengigkeit | Sequentiell statt parallel |

## Blocker-Handling

Wenn ein Track blockiert ist:
1. Blocker dokumentieren (welche Datei, welche Abhaengigkeit)
2. Nicht-blockierte Tracks weiterlaufen lassen
3. Blocker dem User melden mit konkretem Loesungsvorschlag
4. Nie einen Blocker durch Workaround umgehen ohne Rueckfrage

## GitHub-Project-Modell

Empfohlene Felder fuer das GitHub Project Board:

| Feld | Typ | Werte |
|------|-----|-------|
| Status | Single Select | Todo, In Progress, Review, Done |
| Priority | Single Select | P0-critical, P1-high, P2-medium |
| Risk | Single Select | Low, Medium, High |
| Track | Single Select | Core, API, App, Infra, Docs, QA, Security, Workflow |
| Batch | Text | Batch-Nummer oder -Name (z.B. "Batch 1 – API") |
| Blocked By | Text | Issue-Nummern oder Beschreibung der Blockade |
| Execution Mode | Single Select | Parallel, Sequential |

### Statuswerte

| Status | Bedeutung |
|--------|-----------|
| Todo | Issue erkannt, noch nicht begonnen |
| In Progress | Branch existiert, Arbeit laeuft |
| Review | PR erstellt, wartet auf Merge |
| Done | PR gemergt, Issue geschlossen |

### Prioritaeten

| Prioritaet | Bedeutung | SLA |
|------------|-----------|-----|
| P0-critical | System nicht nutzbar | Sofort bearbeiten |
| P1-high | Wichtige Funktion beeintraechtigt | Naechste Session |
| P2-medium | Stoerend, Workaround vorhanden | Wenn Kapazitaet frei |

## Label-Konvention

Ergaenzend zu den bestehenden Labels (`P0-critical`, `bug`, `area/bot`, etc.):

### Track-Labels

Ordnen Issues einem Arbeitsbereich zu:
- `track:core` – Kernlogik, Startprozess, Konfiguration
- `track:api` – REST API, Router, Auth
- `track:app` – Flutter App
- `track:infra` – Deployment, Docker, CI/CD
- `track:docs` – Dokumentation
- `track:qa` – Tests, Qualitaet
- `track:security` – Auth, Secrets, Sicherheit
- `track:workflow` – GitHub Automation, Templates, Labels

### Risk-Labels

Markieren das Aenderungsrisiko:
- `risk:high` – Zentraldateien, Auth, Deploy, Migrationen
- `risk:medium` – Mehrere Module betroffen, moderate Komplexitaet
- `risk:low` – Isolierte Aenderung, ein Modul

### Execution-Labels

Bestimmen den Bearbeitungsmodus:
- `exec:parallel` – Kann parallel mit anderen Issues bearbeitet werden
- `exec:sequential` – Muss sequentiell bearbeitet werden (Abhaengigkeiten/Risiko)

## Zusammenspiel mit bestehenden Playbooks

- **Batch-Modus** (`docs/issue-handling-playbook.md`): Definiert die technische Umsetzung paralleler Batches (Worktrees, Branch-Naming, Merge-Reihenfolge)
- **Debug-Playbook** (`docs/debug-playbook.md`): Definiert die Debugging-Methodik (linear vs. parallel, Priorisierung nach Schicht)
- **Autopilot-Policy** (`docs/autopilot-policy.md`): Definiert was automatisiert werden darf und was nicht

Dieses Playbook ergaenzt diese um die **uebergeordnete Orchestrierungslogik**: Wann und wie wird Arbeit in Tracks zerlegt, parallelisiert und koordiniert.

## Referenzen

- `config/project-fields.md` – Vollstaendiges Feldmodell fuer das GitHub Project Board (Single Source of Truth fuer Felder, Werte, Automationen)
- `docs/AUTOMATION_SETUP.md` – Setup-Anleitung fuer Workflows, Project, Secrets
- `.github/labels.yml` – Label-Definitionen (44 Labels, korrespondieren mit Project-Feldern)

## Aktuelle Arbeitspakete (Stand 2026-03-29)

Die folgenden Issues bilden die naechste Orchestrierungsrunde:

### Batch 1 – Infrastruktur-Aktivierung (Sequential)

| Issue | Titel | Track | Priority |
|-------|-------|-------|----------|
| #252 | Label-Sync ausfuehren und verifizieren | Workflow | P1-high |
| #253 | GitHub Project Board erstellen und konfigurieren | Workflow | P1-high |
| #254 | PROJECT_NUMBER und PROJECT_TOKEN setzen | Workflow | P1-high |

Reihenfolge: #252 → #253 → #254 (Abhaengigkeitskette)

### Batch 2 – Produkt-Verifikation (Parallel)

| Issue | Titel | Track | Priority |
|-------|-------|-------|----------|
| #255 | Smoke-Test: Bot-Start verifizieren | Core | P2-medium |
| #256 | Smoke-Test: API-Start verifizieren | API | P2-medium |
| #257 | CI-Pipeline auf main validieren | QA | P2-medium |

Alle drei ueberschneidungsfrei – gleichzeitig bearbeitbar.

### Batch 3 – Bekannte Bugs (Parallel)

| Issue | Titel | Track | Priority |
|-------|-------|-------|----------|
| #258 | Google OAuth offline_access fixen | Core | P1-high |
| #259 | Webhook-Deployer Default-Branch korrigieren | Infra | P1-high |

Dateien ueberschneidungsfrei – gleichzeitig bearbeitbar.

### Batch 4 – Feature-Luecken (Parallel)

| Issue | Titel | Track | Priority |
|-------|-------|-------|----------|
| #260 | Flutter App: API-Verbindung E2E testen | App | P2-medium |
| #261 | Autopilot-Workflows Dry-Run validieren | Workflow | P2-medium |

Ueberschneidungsfrei – gleichzeitig bearbeitbar. #261 wartet auf #252 (Labels).
