---
name: autopilot-status
description: "Zeige den aktuellen Status der Autopilot-Schicht"
---

# Autopilot Status – Ueberblick ueber die Autopilot-Operations-Schicht

Zeige den aktuellen Zustand aller Autopilot-Workflows, offener Autopilot-Issues und Memory-Review-Status.

## Ablauf

### 1. Offene Autopilot-Issues pruefen

Nutze die GitHub MCP Tools um alle offenen Issues mit Label `autopilot` abzufragen.

Liste sie auf:
- Titel
- Erstellt am
- Letzter Kommentar (Datum)

### 2. Letzte Autopilot-Workflow-Runs abfragen

Nutze die GitHub MCP Tools um die letzten Runs dieser Workflows abzufragen:
- `autopilot-review.yml`
- `autopilot-issue-sync.yml`
- `autopilot-reminders.yml`

Fuer jeden Workflow:
- Letzter Run: Datum + Status (success/failure/skipped)

### 3. Memory-Review-Status pruefen

Lies alle memory-Dateien:
- `memory/automation.md`
- `memory/debugging.md`
- `memory/app.md`
- `memory/handoffs.md`

Pruefe das `Review bis`-Datum in jeder Datei. Melde ob ein Review faellig ist.

### 4. Bestehende Reports pruefen

Pruefe ob aktuelle Triage- und Repo-Review-Issues existieren:
- Offenes Issue mit Label `triage` → letzter Kommentar <7 Tage?
- Offenes Issue mit Label `repo-review` → letzter Kommentar <7 Tage?

### 5. Bericht ausgeben

```
## Autopilot Status

### Workflows
| Workflow | Letzter Run | Status |
|----------|-------------|--------|
| autopilot-review | Datum | success/failure |
| autopilot-issue-sync | Datum | success/failure |
| autopilot-reminders | Datum | success/failure |

### Offene Autopilot-Issues
- #Nr Titel (erstellt: Datum)
- ...
_Keine offenen Autopilot-Issues._ (wenn leer)

### Reports
| Report | Aktuell (<7 Tage) |
|--------|-------------------|
| Triage | Ja/Nein |
| Repo Review | Ja/Nein |

### Memory-Review
| Datei | Review bis | Faellig |
|-------|-----------|---------|
| automation.md | Datum | Ja/Nein |
| debugging.md | Datum | Ja/Nein |
| app.md | Datum | Ja/Nein |
| handoffs.md | Datum | Ja/Nein |

### Empfohlene naechste Aktion
- ...
```

## Regeln

- Keine Aenderungen vornehmen. Nur analysieren und berichten.
- Anti-Loop: Bericht genau einmal ausgeben.
- Bei fehlenden Workflow-Runs: darauf hinweisen dass der Workflow noch nicht gelaufen ist.
- Maximal 3 Empfehlungen.
- Verweis auf `docs/autopilot-policy.md` fuer Details zu Sicherheitsgrenzen.
