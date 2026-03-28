---
name: new-issue
description: "Create exactly one GitHub issue with proper labels, or output as a draft for review"
---

# New-Issue – Einzelnes GitHub Issue erstellen

Erstelle genau ein GitHub Issue fuer `schrottsocke/projekt-personal-assistent`.

## Ablauf

### 1. Input erfassen

Wenn der User eine Beschreibung mitgibt, verwende diese.
Wenn nicht, frage gezielt nach:
- **Was?** Kurze Beschreibung des Problems oder der Verbesserung
- **Wo?** Betroffener Bereich: `bot` / `api` / `app` / `config` / `deploy` / `tests`
- **Typ?** `bug` / `enhancement` / `refactor` / `test` / `docs`
- **Prioritaet?** `P0-critical` / `P1-high` / `P2-medium`

### 2. Issue formulieren

Erstelle einen Entwurf mit:
- **Titel**: Kurz, praegnant, im Format: `[Bereich] Beschreibung`
- **Beschreibung**: Was ist das Problem / die Verbesserung? Welche Dateien sind betroffen? Erwartetes Verhalten.
- **Labels**: Prioritaet + Typ (z.B. `P2-medium`, `enhancement`)

### 3. Draft anzeigen

Zeige den Entwurf dem User zur Pruefung:

```
## Issue-Entwurf

**Titel:** [api] Fehlende Schema-Validierung in /recipes Endpoint
**Labels:** P2-medium, enhancement
**Beschreibung:**
...
```

Frage: "Issue so erstellen, oder etwas aendern?"

### 4. Erstellen

Nach Bestaetigung: Issue auf GitHub erstellen mit Titel, Body und Labels.

Ausgabe:
```
Issue erstellt: #XX – Titel
URL: ...
```

## Regeln

- Genau ein Issue pro Aufruf. Nicht verketten.
- Nach dem Erstellen nicht automatisch mit der Implementierung beginnen.
- **Stop-Regel**: Wenn das Issue `.env`/Secrets, Migrationen, Auth/Security oder Produktions-Deploy betrifft, dies explizit im Issue-Body vermerken.
- Wenn GitHub nicht erreichbar ist: Issue als Markdown-Draft ausgeben, den der User manuell erstellen kann.
