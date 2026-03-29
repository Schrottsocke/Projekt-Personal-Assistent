# Debug-Playbook

## Grundprinzip

Erst reproduzieren, dann Hypothese, dann Experiment, dann Fix.
Kein vorschneller Fix ohne plausible Root-Cause.

## Wann linear, wann parallel?

| Situation | Vorgehen |
|-----------|----------|
| Ein einzelner Bug, klare Fehlermeldung | Linear: Repro → Trace → Fix |
| Bug ohne klare Ursache, mehrere Verdachtsstellen | Parallel: Subagents fuer verschiedene Hypothesen |
| >= 4 Bugs in unterschiedlichen Modulen | Parallel: Batch-Modus (siehe `docs/issue-handling-playbook.md`) |
| Bug in einer einzelnen Datei, klarer Stack-Trace | Linear: direkt fixen |
| Intermittierender Bug, schwer reproduzierbar | Parallel: Logs + Codepfade + Repro gleichzeitig untersuchen |

## Lineares Debugging: Schritt fuer Schritt

### 1. Reproduzieren

- Fehlermeldung/Stack-Trace lesen und verstehen
- Minimalen Reproduktionsfall identifizieren
- Wenn moeglich: failing test oder dry-run schreiben
- Wenn nicht reproduzierbar: Log-Stellen und Bedingungen dokumentieren

### 2. Hypothese bilden

- Genau eine plausible Ursache formulieren
- Betroffene Codestelle(n) lesen und nachvollziehen
- Annahmen explizit machen (z.B. "dieser Wert ist hier immer != None")

### 3. Experiment

- Hypothese mit minimalem Eingriff pruefen
- Bevorzugt: bestehende Logs/Traces lesen, Codepfade nachvollziehen
- Wenn noetig: temporaere Log-Zeile oder assert einfuegen

### 4. Fix

- Minimale Aenderung, die die Root-Cause behebt
- Kein Refactoring nebenbei
- Kein spekulatives Error-Handling fuer andere Szenarien

### 5. Verifizieren

- Reproduktionsfall erneut pruefen
- Seiteneffekte auf benachbarte Funktionalitaet bedenken
- Wenn Test angelegt: Test muss gruen sein

## Paralleles Debugging mit Subagents

Bei unklarer Ursache oder mehreren Verdachtsstellen koennen parallele Subagents verschiedene Aspekte gleichzeitig untersuchen.

### Empfohlene Rollen

| Rolle | Aufgabe | Typ |
|-------|---------|-----|
| **Repro** | Fehlerbild reproduzieren, minimalen Testfall skizzieren | Explore |
| **Logs/Tracing** | Relevante Log-Stellen finden, Aufrufkette nachvollziehen | Explore |
| **Codepfade** | Betroffene Funktionen lesen, Datenfluesse verfolgen | Explore |
| **Tests** | Bestehende Tests pruefen, fehlende Abdeckung identifizieren | Explore |
| **Fix** | Nach Ursachenfindung den Fix implementieren | General |

### Ablauf

1. **Sichten**: Bug-Report lesen, betroffene Module identifizieren
2. **Parallel erkunden**: Bis zu 3 Explore-Agents mit verschiedenen Rollen starten
3. **Ergebnisse zusammenfuehren**: Root-Cause aus den Erkenntnissen ableiten
4. **Fix umsetzen**: Ein Agent oder direkt im Hauptkontext

### Wann Subagents sinnvoll sind

- Fehlerursache nicht offensichtlich (kein klarer Stack-Trace auf eine Zeile)
- Mehrere Module/Dateien koennten betroffen sein
- Aufrufkette ist komplex (Handler → Service → External API)
- Zeitersparnis durch parallele Analyse ueberwiegt Agent-Overhead

### Wann Subagents nicht noetig sind

- Stack-Trace zeigt direkt auf die fehlerhafte Zeile
- Fix ist offensichtlich (Typo, fehlender Parameter, falscher Variablenname)
- Nur eine Datei betroffen

## Abschlussformat

Jeder abgeschlossene Debug-Vorgang endet mit:

- **Ursache**: Was war die Root-Cause? (eine Zeile)
- **Beleg**: Wie wurde die Ursache verifiziert? (Repro, Trace, Test)
- **Fix**: Was wurde geaendert? (Dateien + Kurzfassung)
- **Restrisiko**: Gibt es verwandte Stellen, die aehnlich betroffen sein koennten?

## Debug-Priorisierung nach Schicht

Bei mehreren offenen Bugs diese Reihenfolge einhalten:

1. Start-/Importfehler (Bot startet nicht)
2. Konfiguration (Settings, ENV)
3. Backend-Runtime (Services, DB)
4. API/Auth (Endpunkte, Tokens)
5. App/API-Integration (Frontend-Backend)
6. Deployment (CI, Docker, Infra)

## Verbindung zum Batch-Modus

Wenn mehrere Bugs parallel gefixt werden sollen:
1. Bugs nach diesem Playbook einzeln analysieren (Ursache verstehen)
2. Dann nach `docs/issue-handling-playbook.md` in Batches gruppieren
3. Fixes parallel in isolierten Worktrees umsetzen

Die Analyse-Phase ist immer linear oder mit Explore-Agents.
Nur die Fix-Phase wird parallelisiert.
