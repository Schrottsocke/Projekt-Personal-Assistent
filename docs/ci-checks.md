# CI Check-Matrix

## Welche Checks laufen wann?

| Geaenderte Dateien | `lint` | `test` | `docker` | `flutter-check` |
|---|---|---|---|---|
| `src/**`, `api/**`, `main.py`, `config/**`, `tests/**` | RUN | RUN | — | — |
| `requirements*.txt`, `ruff.toml`, `pytest.ini` | RUN | RUN | — | — |
| `Dockerfile`, `docker-compose.yml` | — | — | RUN | — |
| Python + Docker (beides) | RUN | RUN | RUN | — |
| `app/**` | — | — | — | RUN |
| `docs/**`, `memory/**`, `*.md`, `.claude/**` | skip | skip | skip | — |
| `deploy/**` | skip | skip | skip | — |

- **RUN** = Job wird vollstaendig ausgefuehrt
- **skip** = Job wird uebersprungen, GitHub meldet "passed" (blockiert keinen Merge)
- **—** = Wird von diesen Pfaden nicht ausgeloest

## Pfad-Filter Details

### Python-Filter (`lint`, `test`)
```
main.py, src/**, api/**, config/**, tests/**,
requirements*.txt, ruff.toml, pytest.ini
```

### Docker-Filter (`docker`)
```
Dockerfile, docker-compose.yml, requirements*.txt,
main.py, src/**, api/**, config/**
```

### Flutter-Filter (`flutter-check`)
```
app/**
```
Separater Workflow mit eigenem Path-Trigger (kein Required Check).

## Required Checks fuer Merge nach main

In **GitHub Settings > Branches > Branch protection rules** fuer `main`:

### Als Required Check setzen:
- `lint`
- `test`
- `docker`

Alle drei melden "skipped/passed" wenn ihre Pfade nicht betroffen sind.

### NICHT als Required Check setzen:
- `changes` (interner Routing-Job)
- `flutter-check` (nutzt Path-Trigger auf Workflow-Ebene, wuerde Nicht-App-PRs blockieren)
- `area-labels`, `size-label` (Automation)
- `stale`, `triage`, `repo-review` (Reports)

### Empfohlene Branch Protection Einstellungen:
1. "Require status checks to pass before merging" aktivieren
2. Required checks: `lint`, `test`, `docker`
3. "Require branches to be up to date before merging" aktivieren
4. "Include administrators" deaktiviert lassen (Notfall-Bypass)

## Technische Umsetzung

Die CI-Pipeline nutzt `dorny/paths-filter@v3` in einem leichtgewichtigen `changes`-Job (~10s).
Downstream-Jobs (`lint`, `docker`, `test`) haben `if:`-Bedingungen basierend auf den Filter-Outputs.
Uebersprungene Jobs gelten bei GitHub als "passed" fuer Required Checks.
