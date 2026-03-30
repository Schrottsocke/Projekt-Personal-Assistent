# Automation

Erkenntnisse zu CI/CD, GitHub Workflows, Label-Patterns, Deploy-Pipelines.

## Eintraege

- **YAML-Bug in 6 Workflows**: `concurrency:` ist unter `permissions:` eingerueckt → wird als Permission geparst, nicht als Top-Level. Betrifft: autopilot-review, autopilot-issue-sync, autopilot-reminders, stale, triage, repo-review. Issue #238. (2026-03-29)
- **Webhook-Deployer Branch**: Default in deploy/webhook_deployer.py:35 ist `claude/dual-personal-assistants-0Uqna` statt `main`. Pushes auf main loesen kein Deploy aus wenn DEPLOY_BRANCH nicht in .env steht. Issue #239. (2026-03-29)
- **Node.js 20 Deprecation in Actions**: Alle 6 Autopilot-Workflows (autopilot-review, issue-sync, reminders, stale, repo-review, triage) zeigen Node.js 20 Warning. Mittelfristig auf Node.js 22-kompatible Action-Versionen aktualisieren. (2026-03-30)

## Meta

- Zuletzt geprueft: 2026-03-28
- Review bis: 2026-06-28
- Max Eintraege: 20
