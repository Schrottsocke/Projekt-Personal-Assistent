---
name: closeout
description: "Post-issue decision: evaluate whether to continue in the same session or recommend a new session"
---

# Closeout – Session-Entscheidung

Evaluiere nach Abschluss eines Issues, ob in derselben Session weitergearbeitet oder eine neue Session empfohlen werden soll.

## Ablauf

### 1. Abschluss pruefen

Pruefe ob das letzte Issue die Definition of Done erfuellt:
- [ ] Aenderung implementiert
- [ ] Aenderung verifiziert (Lint + Tests)
- [ ] Branch gepusht
- [ ] PR gegen Default-Branch existiert mit `Fixes #<issue>`
- [ ] PR gemergt
- [ ] Issue geschlossen

Wenn nicht alle Punkte erfuellt: benennen was fehlt und zuerst abschliessen.

### 2. Naechstes Issue ermitteln

Lade offene Issues fuer `schrottsocke/projekt-personal-assistent`.
Identifiziere das naechste Issue nach Prioritaet (P0 → P1 → P2 → ohne Label).

Wenn keine offenen Issues: melden und Session sauber beenden.

### 3. Memory-Check (automatisch, inline)

Pruefe ob in dieser Session etwas memory-wuerdiges passiert ist.
Dieser Schritt laeuft automatisch im Closeout – kein separater Prompt noetig.

**Prueffragen:**
- Gab es einen nicht-offensichtlichen Bug oder Workaround?
- Wurde ein wiederverwendbares Pattern oder eine Config-Erkenntnis entdeckt?
- Gibt es offene Faeden fuer die naechste Session?

**Wenn nichts speicherwuerdig:** `Memory: keine neuen Erkenntnisse` melden, weiter zu Schritt 4.

**Wenn speicherwuerdig (max 0-3 Eintraege):**

1. Lies die passende memory-Datei:
   - CI/CD, Workflows, Labels, Deploy → `memory/automation.md`
   - Bugs, Debug-Muster, Workarounds → `memory/debugging.md`
   - Flutter, API-Integration, App → `memory/app.md`
   - Offene Faeden, naechste Schritte → `memory/handoffs.md`

2. Pruefe ob ein bestehender Eintrag dasselbe Thema betrifft:
   - Ja → bestehenden Eintrag aktualisieren (ersetzen, nicht anhaengen)
   - Nein → neuen Eintrag hinzufuegen

3. Format: `- **Stichwort**: Erkenntnis (YYYY-MM-DD)`
   - Maximal 2 Zeilen pro Eintrag
   - Kein Chatverlauf, keine Session-Details, keine temporaeren Zustaende
   - Nur was in einer zukuenftigen Session hilft

4. Wachstum pruefen: Wenn Maximum erreicht (20, bzw. 5 bei handoffs),
   aeltesten Eintrag nach `memory/archive/YYYY-MM-DD-thema.md` verschieben.

5. `Zuletzt geprueft` auf heute setzen.

**Nicht speichern wenn:**
- Issue wurde normal abgearbeitet (kein besonderes Learning)
- Info steht schon in `CLAUDE.md`, einem Skill oder einer memory-Datei
- Es war ein einmaliger, bereits geloester Fehler
- Es ist allgemeines Programmierwissen

### 4. Entscheidung treffen

#### Option A: In derselben Session weitermachen

Nur wenn ALLE Punkte zutreffen:
- das aktuelle Issue ist vollstaendig abgeschlossen
- das naechste Issue betrifft denselben Bereich oder eng verwandte Dateien
- kein Kontextdrift erkennbar
- keine neue breite Analyse noetig
- das naechste Issue ist klein genug fuer einen weiteren klaren Durchlauf

#### Option B: Neue Session (im Zweifel bevorzugen)

Wenn EINER dieser Punkte zutrifft:
- das aktuelle Issue war groesser oder ueber mehrere Dateien/Module verteilt
- das naechste Issue betrifft einen anderen Bereich
- der Kontext ist bereits lang oder unuebersichtlich
- in der Session gab es Plan-Loops, Drift oder Wiederholungen
- fuer das naechste Issue waere eine frische Analyse sinnvoller

### 5. Ausgabe

```
## Session-Entscheidung

### Abgeschlossenes Issue
- #XX: Titel – Status

### Memory
- [keine neuen Erkenntnisse | X Eintrag/Eintraege gespeichert in memory/datei.md]

### Naechstes Issue
- #YY: Titel (Prioritaet)
- Bereich: src/services/ | api/routers/ | app/lib/ | ...
- Erste Dateien: ...

### Entscheidung: [Gleiche Session / Neue Session]
### Grund: ...
```

## Regeln

- Genau eine Entscheidung treffen. Nicht beides gleichzeitig.
- Im Zweifel immer **neue Session bevorzugen**.
- Wenn "Neue Session" empfohlen: danach stoppen. Nicht in derselben Antwort mit dem naechsten Issue beginnen.
- Wenn "Gleiche Session": den User fragen ob er weitermachen moechte, bevor `/work-next` gestartet wird.
