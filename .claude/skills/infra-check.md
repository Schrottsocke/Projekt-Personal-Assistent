---
name: infra-check
description: "Hostinger VPS, DNS und Firewall Status pruefen (read-only)"
---

# Infra Check – Hostinger Status

Pruefe den aktuellen Zustand der Hostinger-Infrastruktur. Nur lesende Operationen.

## Ablauf

### 1. VPS-Status

Nutze `mcp__hostinger__list_vps` um alle VPS-Instanzen mit Status, IPs und Specs abzufragen.

### 2. DNS-Zonen

Nutze `mcp__hostinger__list_dns_zones` fuer eine Uebersicht aller Domains.
Bei Bedarf: `mcp__hostinger__list_dns_records` fuer eine spezifische Domain.

### 3. Firewall

Nutze `mcp__hostinger__list_firewalls` fuer eine Uebersicht.
Bei Bedarf: `mcp__hostinger__get_firewall` fuer Details einer Firewall.

### 4. Snapshots

Nutze `mcp__hostinger__list_snapshots` fuer Backup-Uebersicht.

### 5. Bericht

```
## Infra-Status

| Bereich | Status |
|---------|--------|
| VPS | Running/Stopped – IP – Specs |
| DNS Zones | Anzahl Domains |
| Firewall | Aktiv/Inaktiv – Regelanzahl |
| Snapshots | Letzter Snapshot – Alter |

### Auffaelligkeiten
- ...
```

## Regeln

- NUR lesende Operationen. Keine Aenderungen.
- Bei Problemen: beschreiben was gefunden wurde, nicht automatisch fixen.
- Fuer Aenderungen an VPS/DNS/Firewall: immer zuerst User-Bestaetigung einholen (siehe D7 in `docs/agent-guardrails.md`).
- Anti-Loop: Bericht genau einmal ausgeben.
- Maximal 3 Empfehlungen.
