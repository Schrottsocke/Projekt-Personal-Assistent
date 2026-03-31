---
name: skill-audit
description: "Pruefe ob Skills, Guardrails und Regeln noch zum aktuellen Projektstand passen"
---

# Skill Audit – Self-Review

Pruefe ob die Claude Code Skills, Guardrails und CLAUDE.md-Regeln noch zum aktuellen Stand des Projekts passen.

## Wann ausfuehren

- Quartalsweise (zusammen mit `/memory-review`)
- Nach neuer MCP-Integration
- Nach neuer zentraler Architekturdatei
- Nach grundlegender Auth/Security/Deploy-Aenderung
- Wenn ein Bug-Typ 3x in verschiedenen Sessions auftritt

## Ablauf

### 1. Skills-Registry pruefen

Lies alle Dateien in `.claude/skills/`.
Vergleiche mit der Skills-Liste in CLAUDE.md (Abschnitt "## Skills").

Melde:
- Skill-Datei existiert, aber nicht in CLAUDE.md gelistet
- In CLAUDE.md gelistet, aber keine Skill-Datei vorhanden

### 2. Guardrail-Abdeckung pruefen

Lies `docs/agent-guardrails.md`. Fuer jeden aktiven Projektbereich pruefen ob ein Guardrail existiert:

| Bereich | Erwarteter Guardrail |
|---------|---------------------|
| `api/static/` (Web-App) | D1 |
| Auth/Token-Handling | D2 |
| `deploy/`, Systemd, Nginx | D3 |
| API-Endpunkte ↔ JS-Client | D4 |
| JavaScript-Dateien | D5 |
| Externe Services, DB-Sessions | D6 |
| Hostinger MCP, VPS, DNS | D7 |
| `app/` (Flutter) | D8 |
| Database/Schema | D9 |

Melde Bereiche ohne Guardrail.

### 3. MCP-Abdeckung pruefen

Pruefe welche MCP-Server in `.mcp.json` konfiguriert sind.
Fuer jeden MCP-Server pruefen:
- Gibt es mindestens einen Skill der ihn nutzt?
- Gibt es einen Guardrail fuer schreibende Operationen?
- Ist er im CLAUDE.md-Abschnitt "MCP-Integrationen" dokumentiert?

Melde unabgedeckte MCP-Server.

### 4. Workflow-Liste pruefen

Lies `.github/workflows/` (Dateiliste).
Vergleiche mit der erwarteten Liste in `.claude/skills/automation-check.md`.

Melde Workflows die in der Skill-Liste fehlen.

### 5. Stop-Regeln pruefen

Lies den "## Stop"-Abschnitt in CLAUDE.md.
Fuer jeden Guardrail-Trigger pruefen ob eine passende Stop-Regel existiert.

Melde Guardrails ohne korrespondierende Stop-Regel.

### 6. Memory-Status pruefen

Lies alle memory-Dateien. Pruefe:
- Eintragsanzahl vs. Maximum
- `Review bis`-Datum ueberschritten?
- Handoffs aelter als 14 Tage?

### 7. Bericht

```
## Skill Audit

### Skills Registry
- Dateien: X | In CLAUDE.md: Y | Match: JA/NEIN
- Fehlend in CLAUDE.md: ...
- Fehlende Datei: ...

### Guardrail-Abdeckung
| Bereich | Guardrail | Status |
|---------|-----------|--------|
| Web-App | D1 | OK / LUECKE |
| ... | ... | ... |

### MCP-Abdeckung
| MCP | Skill | Guardrail | Dokumentiert | Status |
|-----|-------|-----------|-------------|--------|
| GitHub | ja | - | ja | OK |
| Hostinger | ja | D7 | ja | OK |
| Slack | nein | nein | ja | LUECKE |

### Workflows
- Erwartet: X | Tatsaechlich: Y | Match: JA/NEIN

### Stop-Regeln
- Abgedeckte Guardrails: X/Y

### Memory
| Datei | Eintraege | Max | Review faellig |
|-------|-----------|-----|---------------|
| automation.md | X | 20 | Ja/Nein |
| ... | ... | ... | ... |

### Empfehlungen (max 5)
1. ...
```

## Regeln

- Keine Aenderungen vornehmen. Nur analysieren und berichten.
- Anti-Loop: Bericht genau einmal ausgeben.
- Maximal 5 Empfehlungen, priorisiert nach Risiko.
- Wenn Aenderungen noetig sind: dem User vorschlagen, nicht selbst ausfuehren.
