---
name: deploy
description: "Gefuehrtes Deployment auf den Hostinger VPS mit Pre-/Post-Checks"
---

# Deploy – Gefuehrtes Deployment

Fuehre ein Deployment auf den Hostinger VPS durch – mit Preflight-Checks, Schritt-fuer-Schritt-Ausfuehrung und Post-Deploy-Verifikation.

## Ablauf

### 0. Stop-Check

Dieses Skill veraendert den Produktionsserver. Vor dem Start:
- Explizite User-Bestaetigung einholen ("Soll ich jetzt deployen?")
- Ohne Bestaetigung: nur den Plan zeigen, nicht ausfuehren

### 1. Preflight-Checks

Alle muessen bestanden sein bevor das Deployment startet:

```
[ ] git status: Working Directory sauber
[ ] git branch: auf `main`
[ ] git log: lokaler main == origin/main (keine unpushed Commits)
[ ] CI: letzter CI-Run auf main ist gruen (GitHub MCP pruefen)
[ ] Keine offenen P0-critical Issues
```

Wenn ein Check fehlschlaegt: melden welcher und stoppen.

### 2. VPS-Status pruefen

Nutze Hostinger MCP (read-only):
- `mcp__hostinger__list_vps` → VPS laeuft?
- Melde: VPS-Status, IP, OS

### 3. Deployment-Plan zeigen

Zeige dem User was passieren wird:
```
## Deployment-Plan

1. SSH auf VPS: git pull origin main
2. pip install -r requirements.txt
3. Systemd-Services neustarten:
   - personal-assistant.service (Bot)
   - personal-assistant-api.service (API)
   - personal-assistant-webhook.service (Webhook)
4. Health-Check: /health Endpoint pruefen
```

User muss bestaetigen.

### 4. Deployment ausfuehren

**Wichtig:** Claude Code hat keinen direkten SSH-Zugang zum VPS.

Optionen:
- **Webhook-Deployer**: Wenn konfiguriert, loest ein Push auf main das Deployment automatisch aus (deploy/webhook_deployer.py)
- **Manuell**: User fuehrt `deploy/update.sh` auf dem Server aus

Wenn Webhook aktiv:
1. Pruefen ob der letzte Push das Deployment ausgeloest hat
2. Warten und Status pruefen

Wenn manuell:
1. Dem User die Befehle geben die auf dem Server auszufuehren sind
2. Warten auf Rueckmeldung

### 5. Post-Deploy-Verifikation

Nach dem Deployment pruefen:
- VPS-Status via Hostinger MCP (laeuft noch?)
- Health-Endpoint erreichbar? (User muss URL mitteilen oder aus .env bekannt)
- Keine neuen Fehler in den letzten Logs?

### 6. Bericht

```
## Deployment-Bericht

- **Zeitpunkt**: YYYY-MM-DD HH:MM
- **Commit**: <hash> – <message>
- **VPS-Status**: Running
- **Health-Check**: OK / FEHLER
- **Services**: Bot ✓ | API ✓ | Webhook ✓
- **Aktion bei Fehler**: ...
```

## Rollback

Wenn das Deployment fehlschlaegt:
1. Nicht automatisch rollbacken – User fragen
2. Optionen zeigen: git revert, Snapshot restore, manueller Fix
3. Wenn Snapshot vorhanden: `mcp__hostinger__restore_snapshot` als Option anbieten (D7-Guardrail beachten)

## Regeln

- Kein Deployment ohne explizite User-Bestaetigung (zweimal: Plan + Ausfuehrung)
- Kein Deployment wenn CI rot ist
- Kein Deployment von einem Feature-Branch (nur main)
- D7-Guardrail fuer alle Hostinger-Operationen beachten
- Wenn SSH-Zugang nicht moeglich: dem User klare Befehle geben
- Anti-Loop: Plan einmal zeigen, dann ausfuehren oder stoppen
