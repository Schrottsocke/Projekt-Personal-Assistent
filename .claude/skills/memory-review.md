---
name: memory-review
description: "Memory-Dateien reviewen, veraltete Eintraege archivieren, Wachstum kontrollieren"
---

# Memory Review – Gedaechtnis aufraumen

Pruefe alle memory-Dateien auf Aktualitaet und entferne Veraltetes.

## Wann ausfuehren

- Quartalsweise (wenn `Review bis` erreicht ist)
- Wenn eine memory-Datei mehr als 15 Eintraege hat
- Auf User-Anfrage

## Ablauf

### 1. Alle memory-Dateien lesen

Lies:
- `memory/automation.md`
- `memory/debugging.md`
- `memory/app.md`
- `memory/handoffs.md`

Zaehle Eintraege pro Datei. Pruefe `Review bis`-Datum.

### 2. Eintraege bewerten

Fuer jeden Eintrag pruefen:
- Ist die Erkenntnis noch aktuell? (Code/Config koennte sich geaendert haben)
- Wurde das Problem inzwischen dauerhaft geloest?
- Steht die Information mittlerweile in `CLAUDE.md` oder einem Skill?
- Ist der Eintrag ein Handoff der bereits abgearbeitet wurde?

### 3. Archivieren oder loeschen

- Veraltete Eintraege nach `memory/archive/YYYY-MM-DD-thema.md` verschieben
- Handoffs die abgearbeitet sind: direkt loeschen (nicht archivieren)
- `Zuletzt geprueft` in jeder Datei auf heute setzen
- `Review bis` auf naechstes Quartal setzen

### 4. Bericht

```
## Memory Review

| Datei | vorher | nachher | archiviert |
|-------|--------|---------|------------|
| automation.md | X | Y | Z |
| debugging.md | X | Y | Z |
| app.md | X | Y | Z |
| handoffs.md | X | Y | Z |

Gesamt: X Eintraege
```

## Regeln

- Im Zweifel loeschen. Lieber zu wenig als zu viel behalten.
- Archiv-Dateien nicht reviewen (die sind abgelegt).
- Wenn nach Review eine Datei leer ist: Struktur beibehalten, nur Eintraege entfernen.
