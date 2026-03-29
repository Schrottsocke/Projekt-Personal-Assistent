# Issue-Handling Playbook: Parallel-Batch-Methode

## Wann welcher Modus?

| Situation | Modus |
|-----------|-------|
| >= 4 offene Issues | **Batch-Modus** (Standard) |
| < 4 offene Issues | Einzelmodus (ein Issue pro Durchlauf) |
| User sagt "einzeln" / "eins nach dem anderen" | Einzelmodus |
| Issues betreffen alle dieselbe Datei | Einzelmodus (sequentiell) |

## Batch-Modus: Schritt fuer Schritt

### 1. Sichten

- Alle offenen Issues laden (`list_issues`, State: OPEN)
- Nach Prioritaet sortieren: P0 > P1 > P2
- Fuer jedes Issue notieren: betroffene Dateien, betroffene Module

### 2. Gruppieren

Ziel: **Kein File darf in mehr als einem Batch vorkommen.**

Kriterien fuer die Batch-Bildung:
- **Modulzugehoerigkeit**: Issues im selben Modul/Ordner gehoeren zusammen
- **Datei-Ueberschneidungen**: Wenn zwei Issues dieselbe Datei aendern, muessen sie im selben Batch sein
- **Unabhaengigkeit**: Batches sollen keine gemeinsamen Dateien haben
- **Groesse**: Batches moeglichst gleichmaessig verteilen (3-6 Issues pro Batch)

Typische Batch-Schnitte:
- `api/` (API-Layer, Router, Auth)
- `src/handlers/` (Bot-Handler, Callbacks)
- `src/services/` aufgeteilt nach Untergruppen (AI, Memory, externe Services)
- `app/` (Flutter-App)
- `config/`, `deploy/` (Infrastruktur)

### 3. Plan praesentieren

Vor der Umsetzung dem User zeigen:
- Batch-Name, enthaltene Issues, betroffene Dateien
- Konflikt-Risiko pro Batch
- Cross-Batch-Konflikte (sollte KEINE geben)

### 4. Parallel bearbeiten

- Pro Batch einen Agent in einem **isolierten Worktree** starten
- Alle Agents gleichzeitig launchen (ein Message, mehrere Tool-Calls)
- Jeder Agent:
  1. Branch erstellen: `fix/batch<N>-<kurzname>` (basierend auf `main`)
  2. Alle betroffenen Dateien lesen
  3. Minimale, gezielte Fixes
  4. Commit: `fix(scope): batch<N> – kurzbeschreibung (#issue1, #issue2, ...)`
  5. Push: `git push -u origin <branch>`

### 5. PRs erstellen

- Pro Batch ein PR gegen `main`
- PR-Beschreibung enthaelt fuer jedes Issue: `Fixes #<issue>`
- PR-Titel: `fix(scope): Batch <N> – Kurzbeschreibung`

### 6. Mergen

- Alle PRs koennen gleichzeitig offen sein
- In beliebiger Reihenfolge mergen (squash bevorzugt)
- Nach Merge: pruefen ob Issues automatisch geschlossen wurden

## Branch-Namenskonvention

```
fix/batch<N>-<module1>-<module2>
```

Beispiele:
- `fix/batch1-api-drive-shopping`
- `fix/batch2-handlers-scanner`
- `fix/batch3-ai-commands-memory`
- `fix/batch4-services-spotify-email-tts-docs-weather`

## Konfliktvermeidung

Die wichtigste Regel: **Kein File in mehr als einem Batch.**

Wenn zwei Issues dieselbe Datei betreffen:
- Pruefen ob die Aenderungen an weit entfernten Stellen sind (z.B. Zeile 67 vs. 370)
- Wenn ja: im selben Batch, Konflikt-Risiko als "niedrig-mittel" markieren
- Wenn die Aenderungen nah beieinander liegen: zwingend im selben Batch

## Beispiel: Session vom 2026-03-29

17 offene Issues in 4 Batches:

| Batch | Issues | Dateien | Konflikt |
|-------|--------|---------|----------|
| 1 – API Layer | #170, #169, #168, #167 | api/routers/*, drive_service, shopping_service | NIEDRIG |
| 2 – Handlers | #172, #177, #178, #175 | message_handlers, scanner_service, proposal_handlers | NIEDRIG-MITTEL |
| 3 – AI & Memory | #164, #176, #165, #163 | ai_service, command_handlers, memory/* | NIEDRIG-MITTEL |
| 4 – Services | #171, #166, #174, #173, #162 | spotify, email, tts, document, weather | NIEDRIG-MITTEL |

Ergebnis: Alle 4 PRs konfliktfrei gemergt, 17 Issues geschlossen.
