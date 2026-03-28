---
name: triage
description: "Run a full repo health check: lint, tests, open issues, code scan, and suggest or create new issues"
---

# Triage – Repo-Gesundheitscheck

Fuehre einen vollstaendigen Gesundheitscheck des Repositories durch und schlage konkrete, sinnvolle Issues vor.

## Ablauf

### 1. Lint-Check

Fuehre aus:
```bash
ruff check .
ruff format --check .
```
Fasse Ergebnisse zusammen: Anzahl Fehler, betroffene Dateien.

### 2. Test-Check

Fuehre aus:
```bash
python -m pytest tests/ --cov=src --cov=api --cov-report=term-missing --cov-fail-under=50 -v
```
Fasse zusammen: Anzahl Tests, Pass/Fail, Coverage-Prozent, ungetestete Module.

### 3. Offene Issues

Lade alle offenen GitHub Issues fuer `schrottsocke/projekt-personal-assistent`.
Sortiere nach Priority-Labels:
1. `P0-critical`
2. `P1-high`
3. `P2-medium`
4. Ohne Label

Gib eine kurze Uebersicht: Anzahl pro Prioritaet, aelteste Issues.

### 4. Code-Scan

Scanne die Hauptverzeichnisse auf haeufige Probleme:
- **Bereiche**: `src/`, `api/`, `app/lib/`, `config/`, `deploy/`, `tests/`
- **Pruefe auf**:
  - Module ohne zugehoerige Tests
  - `TODO`, `FIXME`, `HACK` Kommentare
  - Bare `except:` ohne spezifische Exception
  - API-Routen ohne Schema-Validierung
  - Services die von keinem Handler/Router importiert werden

Zaehle Fundstellen, liste die wichtigsten auf.

### 5. Bericht

Gib einen strukturierten Bericht aus:

```
## Triage-Bericht

### Lint
- Status: OK / X Fehler
- Betroffene Dateien: ...

### Tests
- Status: X/Y bestanden
- Coverage: X%
- Ungetestete Module: ...

### Offene Issues
- P0: X | P1: X | P2: X | Ohne Label: X
- Aeltestes: #XX (Titel)

### Code-Qualitaet
- TODOs/FIXMEs: X Fundstellen
- Bare Excepts: X
- Module ohne Tests: X

### Vorgeschlagene Issues (3-5)
1. **Titel** – Kurzbeschreibung (Label: `P2-medium`, `enhancement`)
2. ...
```

### 6. Issues erstellen (optional)

Frage den User: "Soll ich die vorgeschlagenen Issues auf GitHub erstellen?"

- **Ja**: Erstelle jedes Issue einzeln mit passendem Titel, Beschreibung und Labels.
- **Nein**: Belasse es beim Bericht.

## Regeln

- Anti-Loop: Den Bericht genau einmal ausgeben. Nicht wiederholen.
- Keine Aenderungen am Code vornehmen. Nur analysieren und berichten.
- Wenn GitHub-Issues nicht geladen werden koennen: den User informieren und nur Lint/Test/Code-Scan ausgeben.
- Maximal 5 Issue-Vorschlaege. Qualitaet vor Quantitaet.
