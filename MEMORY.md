# MEMORY.md

Index fuer das `memory/`-Verzeichnis.
Fuer Claude Code Sessions gedacht, nicht fuer Menschen.

## Abgrenzung

| Datei | Inhalt | Aenderungshaeufigkeit |
|-------|--------|-----------------------|
| `CLAUDE.md` | Regeln, Workflow, Skills | selten |
| `MEMORY.md` | Index fuer Gelerntes | bei Bedarf |
| `memory/` | thematische Erkenntnisse | regelmaessig |
| `src/memory/` | Python-Service-Code | **NICHT verwechseln** |

## Dateien

| Datei | Inhalt | Max |
|-------|--------|-----|
| `memory/automation.md` | CI/CD, Workflows, Labels, Deploy | 20 |
| `memory/debugging.md` | Bugs, Debug-Muster, Workarounds | 20 |
| `memory/app.md` | Flutter, API-Integration | 20 |
| `memory/handoffs.md` | Session-Uebergaben, offene Faeden | 5 |
| `memory/archive/` | Archivierte Eintraege | – |

## Merksaetze

1. Nur speichern, was in einer zukuenftigen Session hilft.
2. Kein Chatverlauf. Kein Changelog. Keine temporaeren Zustaende.
3. Ein Eintrag = eine Erkenntnis, maximal 2 Zeilen.
4. Wenn ein Eintrag veraltet ist: loeschen oder archivieren, nicht ergaenzen.
5. Ersetzen ist besser als anhaengen.

## Wann speichern

- Ein Bug wurde geloest und die Ursache war nicht offensichtlich
- Ein Workaround war noetig und sollte dokumentiert sein
- Eine Konfiguration oder ein Pattern wurde entdeckt, das wiederverwendbar ist
- Eine Session endet mit offenen Faeden (→ `handoffs.md`)

## Wann NICHT speichern

- Issue wurde normal abgearbeitet (kein besonderes Learning)
- Information steht schon in `CLAUDE.md` oder einer Skill-Datei
- Information ist nur fuer diese eine Session relevant
- Es handelt sich um allgemeines Programmierwissen

## Wachstumsschutz

- Jede memory-Datei hat ein Maximum (siehe Tabelle oben).
- Wenn das Maximum erreicht ist: aelteste oder unwichtigste Eintraege archivieren.
- Archivierte Eintraege wandern nach `memory/archive/` mit Datumspraefix.
- `handoffs.md` wird aggressiv bereinigt: nur die letzten 5 Eintraege behalten.
- Quartalsweise Review mit `/memory-review`.
- Ziel: Gesamtumfang aller memory-Dateien unter 200 Zeilen.
- Nie mehr als 3 neue Eintraege pro Session.

## Eintragsformat

```
- **Stichwort**: Erkenntnis (YYYY-MM-DD)
```

Maximal 2 Zeilen pro Eintrag. Kein Kontext-Dump.

## Skills

| Skill | Zweck |
|-------|-------|
| `/save-memory` | Erkenntnisse aus der Session in memory/ speichern |
| `/memory-review` | Memory-Dateien reviewen, kuerzen, archivieren |
| `/closeout` | Enthaelt Memory-Check vor Session-Entscheidung |
