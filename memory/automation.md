# Automation

Erkenntnisse zu CI/CD, GitHub Workflows, Label-Patterns, Deploy-Pipelines.

## Eintraege

- **Node.js 20 Deprecation in Actions**: Alle 6 Autopilot-Workflows (autopilot-review, issue-sync, reminders, stale, repo-review, triage) zeigen Node.js 20 Warning. Mittelfristig auf Node.js 22-kompatible Action-Versionen aktualisieren. (2026-03-30)

- **Flutter APK via CI**: Produktions-APK wird ueber GitHub Actions gebaut, nicht lokal. Workflow: `.github/workflows/flutter.yml`, Job `build-apk`, manuell per `workflow_dispatch` oder automatisch bei Push auf main. Artifact: `personal-assistant-apk`. Kein lokales Flutter noetig. (2026-04-01)
- **CORS-Steuerung**: `API_CORS_ORIGINS` in `.env` (kommasepariert), gelesen in `config/settings.py:120`, angewendet in `api/main.py:162-177`. Nach Aenderung: `systemctl restart personal-assistant-api`. Kein Nginx-CORS – alles ueber FastAPI. (2026-04-01)

## Archiv

- ~~YAML-Bug in 6 Workflows (#238)~~: Behoben – alle Workflows haben korrekte concurrency. (geloest 2026-03-30)
- ~~Webhook-Deployer Branch (#239)~~: Behoben – Default ist jetzt "main". (geloest 2026-03-30)

## Meta

- Zuletzt geprueft: 2026-04-01
- Review bis: 2026-06-28
- Max Eintraege: 20
