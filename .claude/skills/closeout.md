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

### 3. Memory-Check

Pruefe kurz ob in dieser Session etwas memory-wuerdiges passiert ist:
- Nicht-offensichtlicher Bug oder Workaround?
- Wiederverwendbares Pattern entdeckt?
- Offene Faeden fuer die naechste Session?

Wenn ja: `/save-memory` ausfuehren bevor die Session-Entscheidung getroffen wird.
Wenn nein: weiter zu Schritt 4.

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
