---
name: save-memory
description: "Erkenntnisse aus der aktuellen Session in memory/ speichern"
---

# Save Memory – Session-Erkenntnisse sichern

Pruefe ob die aktuelle Session etwas Dokumentationswuerdiges hervorgebracht hat
und speichere es in der passenden memory-Datei.

## Ablauf

### 1. Session-Erkenntnisse pruefen

Frage dich:
- Gab es einen nicht-offensichtlichen Bug oder Workaround?
- Wurde ein wiederverwendbares Pattern entdeckt?
- Gibt es offene Faeden fuer die naechste Session?
- Wurde eine Automation/Config-Erkenntnis gewonnen?

Wenn keine dieser Fragen mit Ja beantwortet wird: nichts speichern,
melden "Keine memory-wuerdigen Erkenntnisse" und stoppen.

### 2. Ziel-Datei bestimmen

| Thema | Datei |
|-------|-------|
| CI/CD, Workflows, Labels, Deploy | `memory/automation.md` |
| Bugs, Debug-Muster, Workarounds | `memory/debugging.md` |
| Flutter, API-Integration, App | `memory/app.md` |
| Offene Faeden, naechste Schritte | `memory/handoffs.md` |

### 3. Eintrag formulieren

Regeln:
- Maximal 2 Zeilen pro Eintrag
- Format: `- **Stichwort**: Erkenntnis (YYYY-MM-DD)`
- Kein Chatverlauf, kein Kontext-Dump
- Nur was in einer zukuenftigen Session hilft

### 4. Wachstum pruefen

Vor dem Schreiben:
- Lies die Ziel-Datei
- Zaehle bestehende Eintraege
- Wenn Maximum erreicht (20, bzw. 5 bei handoffs): den aeltesten oder
  unwichtigsten Eintrag nach `memory/archive/YYYY-MM-DD-thema.md` verschieben
- Pruefen ob ein bestehender Eintrag durch den neuen ersetzt werden kann
  (gleiches Thema → ersetzen statt anhaengen)

### 5. Eintrag schreiben

Fuege den Eintrag unter `## Eintraege` ein.
Aktualisiere `Zuletzt geprueft` auf das heutige Datum.

### 6. Bestaetigung

Melde:
- **Datei**: welche memory-Datei wurde beschrieben
- **Eintrag**: der geschriebene Eintrag (Kurzfassung)
- **Anzahl**: X / Max

## Regeln

- Nie mehr als 2 Eintraege pro Session speichern.
- Im Zweifel nichts speichern.
- Handoffs sind immer erlaubt (auch wenn sonst nichts gespeichert wird).
- Keine Duplikate. Vor dem Schreiben bestehende Eintraege lesen.
- Siehe `MEMORY.md` fuer Speicher-Kriterien.
