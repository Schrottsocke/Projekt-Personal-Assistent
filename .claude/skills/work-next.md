---
name: work-next
description: "Pick the next open issue by priority and work it through the full GitHub automation flow (branch, implement, verify, commit, push, PR, merge, close)"
---

# Work-Next – Naechstes Issue abarbeiten

Waehle das naechste sinnvolle offene Issue und arbeite es vollstaendig nach dem CLAUDE.md-Workflow ab.

## Ablauf

### 0. Pre-flight

Bevor ein Issue ausgewaehlt wird, kurz pruefen:

1. **Branch**: Auf `main`? Wenn nicht: `git checkout main && git pull origin main`
2. **Working Directory**: Sauber? Wenn nicht: uncommitted Changes melden und stoppen
3. **Handoffs**: `memory/handoffs.md` lesen – gibt es offene Faeden die zuerst erledigt werden muessen?
4. **Memory-Review**: Ist ein `Review bis`-Datum in einer memory-Datei ueberschritten? Wenn ja: kurz erwaehnen

Wenn alle Checks bestanden: weiter zu Schritt 1.
Wenn ein Check fehlschlaegt: dem User melden und Entscheidung abwarten.

### 1. Issue auswaehlen

Lade offene Issues fuer `schrottsocke/projekt-personal-assistent`.
Sortiere nach Prioritaet:
1. `P0-critical`
2. `P1-high`
3. `P2-medium`
4. Ohne Label

Waehle genau ein Issue. Bei gleicher Prioritaet: das aelteste zuerst.

Wenn keine Issues offen sind: dem User melden und stoppen.

Wenn Issues nicht geladen werden koennen: nicht raten, nicht frei losarbeiten. Den User um eine Issue-Nummer, kopierten Issue-Text oder direkten Arbeitsauftrag bitten.

### 2. Ankuendigung

Genau einmal kurz antworten mit:
- **Aufgabe**: Was wird gemacht?
- **Dateien**: Welche Dateien sind betroffen?
- **Erster Schritt**: Was wird zuerst getan?
- **Pruefung**: Wie wird das Ergebnis geprueft?

Danach direkt ausfuehren. Plan nicht wiederholen (Anti-Loop).

### 3. Branch anlegen

Branch-Name nach Typ:
- Bug: `fix/<issue-nummer>-kurzbeschreibung`
- Feature/Enhancement: `feat/<issue-nummer>-kurzbeschreibung`
- Refactor: `refactor/<issue-nummer>-kurzbeschreibung`

Branch vom Default-Branch (`main`) erstellen.

### 4. Implementieren

- Erst verstehen, dann minimal aendern.
- Nur eine Aufgabe pro Durchlauf.
- Kleine Aenderungen bevorzugen.
- Keine stillen Refactorings.
- Keine Features ueber das Issue hinaus einfuehren.

**Stop-Regeln** – Sofort stoppen und Rueckfrage stellen bei:
- `.env`, Secrets, Tokens
- Migrationen oder Datenbankschema
- Auth/Security
- produktionsrelevante Deploy-Aenderungen
- groessere Refactorings
- unklare Zustaendigkeit zwischen Bot (`src/`), API (`api/`) und App (`app/`)

### 5. Verifizieren

```bash
ruff check .
ruff format --check .
python -m pytest tests/ -v
```

Fehler beheben bevor weitergemacht wird.

### 6. Commit

Format: `fix(scope): kurze beschreibung (#<issue-nummer>)`

Beispiele:
- `fix(api): validate recipe schema on POST (#42)`
- `feat(bot): add /scan command for document upload (#55)`
- `refactor(memory): extract common query logic (#61)`

### 7. Push

Branch zum Remote pushen:
```bash
git push -u origin <branch-name>
```

Bei Netzwerkfehler: bis zu 4 Retries mit exponentiellem Backoff (2s, 4s, 8s, 16s).

### 8. Pull Request

PR erstellen gegen den Default-Branch (`main`).
- **Titel**: Kurz, unter 70 Zeichen
- **Body**: Muss `Fixes #<issue-nummer>` enthalten fuer automatisches Schliessen
- Beschreibung: Was wurde geaendert und warum

### 9. Merge

PR mergen. Danach pruefen ob das Issue automatisch geschlossen wurde.
Wenn nicht: Issue manuell schliessen mit Begruendung.

### 10. Abschlussmeldung

Kurz melden im Format:
- **Geaendert**: Welche Dateien
- **Ergebnis**: Was wurde erreicht
- **Pruefung**: Lint/Test-Status
- **GitHub**: Branch, Push, PR, Merge, Issue-Status
- **Naechstes Issue**: Nummer und Titel
- **Empfehlung**: gleiche Session / neue Session
- **Grund**: Warum diese Empfehlung
- **Offen**: Offene Punkte falls vorhanden

Nach der Abschlussmeldung nicht automatisch das naechste Issue anfangen.

## Definition of Done

Ein Issue ist erst fertig, wenn:
- [ ] Aenderung implementiert
- [ ] Aenderung verifiziert (Lint + Tests)
- [ ] Branch gepusht
- [ ] PR gegen Default-Branch existiert mit `Fixes #<issue>`
- [ ] PR gemergt
- [ ] Issue geschlossen (automatisch oder manuell)
