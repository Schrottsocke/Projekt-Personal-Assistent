# CLAUDE.md – Arbeitskontext fuer Claude Code

## Projekt

DualMind Personal Assistant – zwei Telegram-Bots (TaakeBot + NinaBot) mit geteiltem Gedaechtnis, REST API und Flutter App.

## Ziel dieses Dokuments

Dieses Dokument definiert, wie in diesem Repository gearbeitet wird.
Ziel ist: kleine, sichere, nachvollziehbare Schritte statt grosser unkontrollierter Aenderungen.

Claude soll:
- erst verstehen, dann aendern,
- pro Durchlauf nur eine klar abgegrenzte Aufgabe bearbeiten,
- nach jeder Aenderung kurz verifizieren,
- bei Risiko oder Unklarheit stoppen und den User fragen.

## Architektur

- **Backend (Python):** `src/` – Services, Handler, Scheduler, Memory, Bots
- **REST API:** `api/` – FastAPI mit JWT-Auth
- **Mobile App:** `app/` – Flutter (Dart), Riverpod State-Management
- **Config:** `config/settings.py` – zentralisierte Settings aus `.env`
- **Deploy:** `deploy/` – Systemd-Services, Bootstrap, Webhook-Deployer

## Einstiegspunkte

| Datei | Zweck |
|---|---|
| `main.py` | Telegram-Bots (TaakeBot + NinaBot) |
| `api/main.py` | FastAPI App-Definition |
| `api/api_main.py` | Standalone-Startskript fuer die API |
| `app/lib/main.dart` | Flutter App Entry |
| `config/settings.py` | zentrale Konfiguration |
| `README.md` | Features, Setup, Betriebswissen |
| `CHANGELOG.md` | letzte Aenderungen, Fixes, Verlauf |

## Wichtige Hinweise

- **Zwei `memory_service.py`:**
  - `src/memory/memory_service.py` → Telegram-Bot-Kontext
  - `src/services/memory_service.py` → API-Kontext
- Das sind aktuell **zwei unterschiedliche Implementierungen** mit verschiedenen Schnittstellen.
- Nicht ungefragt zusammenfuehren oder "aufraeumen".

- **Secrets:**
  - `.env` enthaelt API-Keys, Tokens und Passwoerter.
  - Niemals Secrets committen, rotieren oder durch Dummy-Werte ersetzen, ausser der User verlangt es ausdruecklich.
  - `.env.example` ist nur Vorlage, nicht Wahrheit ueber die produktive Konfiguration.

- **Betriebsrealitaet:**
  - Dieses Projekt kombiniert Bot, API, Mobile App und Deployment.
  - Aenderungen koennen Seiteneffekte zwischen `main.py`, `src/`, `api/`, `app/`, `config/` und `deploy/` haben.
  - Deshalb immer lokal klein und gezielt arbeiten.

## Arbeitsprinzipien

1. **Erst analysieren, dann minimal aendern.**
   Vor jeder Aenderung erst relevante Dateien lesen und kurz erklaeren, was geaendert werden soll.

2. **Nur eine Aufgabe pro Durchlauf.**
   Keine Roadmaps, keine Sammelumbauten, keine Nebenbaustellen innerhalb derselben Session.

3. **Kleine Aenderungen bevorzugen.**
   Lieber ein klarer Fix in 1–3 Dateien als ein breiter Umbau ueber viele Module.

4. **Nach Aenderung kurz verifizieren.**
   Nur die direkt betroffenen Checks, Tests oder Startpfade ausfuehren; danach stoppen.

5. **Nicht automatisch weiterziehen.**
   Nach erledigtem Schritt nicht direkt das naechste Problem loesen, sondern Ergebnis melden.

6. **Keine stillen Refactorings.**
   Wenn der Auftrag ein Bugfix ist, dann nicht nebenbei Architektur umbauen.

7. **Keine Vermutungen als Fakten behandeln.**
   Wenn Ursache, Datenfluss oder Ownership unklar sind: stoppen und nachfragen.

## Standard-Antwortformat vor Aenderungen

Bevor du Code aenderst, antworte immer kurz in diesem Format:

1. **Aufgabe:** Was genau bearbeitet wird
2. **Analyse:** Welche Dateien ich dafuer pruefe
3. **Plan:** Welche minimale Aenderung ich machen will
4. **Verifikation:** Wie ich den Schritt danach kurz pruefe

Kurz halten, kein langer Essay.

## Debugging-Reihenfolge

Wenn der User allgemein "debuggen", "pruefen" oder "Fehler finden" sagt, dann in dieser Reihenfolge vorgehen:

1. Start-/Importfehler und Konfigurationsprobleme
2. Runtime-Fehler im Backend (`main.py`, `src/`, `config/`)
3. API-Fehler (`api/`, Auth, Router, Dependencies)
4. App/API-Integration (`app/`, JWT, Base URL, 401/403)
5. Deployment/Betrieb (`deploy/`, systemd, Docker, Webhook, Monitoring)

Nicht gleichzeitig an mehreren Ebenen arbeiten, wenn es nicht noetig ist.

## Arbeitsmodi

### Modus 1: Issue abarbeiten (Standard)

Diesen Modus verwenden, wenn der User auf bestehende Issues verweist oder du explizit aufgefordert wirst, Issue-gesteuert zu arbeiten.

Regeln:
- offene Issues nach Prioritaet pruefen: `P0-critical` → `P1-high` → `P2-medium`
- genau **ein** passendes Issue auswaehlen
- dem User kurz sagen, welches Issue bearbeitet wird
- nur das erledigen, was zu diesem Issue gehoert
- neu entdeckte Probleme notieren, aber nicht automatisch mitbearbeiten

### Modus 2: Analyse & Issues erstellen

Nur wenn der User ausdruecklich sagt:
- "Analysiere …"
- "Erstelle Issues …"
- "Finde Probleme …"
- "Liste Bugs / Risiken / Refactorings auf …"

Regeln:
- keine Code-Aenderungen
- nur Analyse, Problemfindung, Strukturierung und Issue-Vorschlaege
- wenn GitHub-Issues erstellt werden sollen: pro Thema klarer Titel, Beschreibung, Prioritaet, DoD

### Modus 3: Direkter Arbeitsauftrag

Wenn der User eine konkrete Aufgabe ohne Issue-Bezug gibt, darf normal gearbeitet werden.

Beispiele:
- "Fix den 401-Fehler in der Flutter App"
- "Pruefe warum die API nicht startet"
- "Verbessere das Logging im Login-Flow"

In diesem Modus gilt:
- kleine, risikoarme Arbeiten duerfen **ohne neues Issue** durchgefuehrt werden
- groessere Features, groessere Refactorings oder unklare Bugs sollen erst als Issue vorgeschlagen werden

## Issue-Policy

**GitHub-Repo: `schrottsocke/projekt-personal-assistent`**

### Prioritaets-Labels: `P0-critical`, `P1-high`, `P2-medium`

### Ein Issue ist erforderlich fuer:
- neue Features
- groessere Refactorings
- Architektureaenderungen
- Aenderungen ueber mehrere Subsysteme hinweg
- Bugs, die nicht in wenigen Dateien sauber eingrenzbar sind
- Arbeiten mit laengerer Definition of Done

### Kein neues Issue noetig fuer:
- kleine, klar abgegrenzte Bugfixes
- Logging-Verbesserungen
- kleine Doku-Korrekturen
- kleine Test-Ergaenzungen
- klar begrenzte Konfigurations- oder Validierungsfixes

### Wenn waehrend der Arbeit neue Probleme auftauchen:
- nicht sofort loesen
- kurz notieren
- am Ende der Session dem User gesammelt melden

## Workflow bei Issue-Arbeit

### Bei Sessionstart
1. Offene Issues pruefen
2. Nach Prioritaet sortieren
3. Hoechste sinnvolle Prioritaet waehlen
4. User kurz informieren, welches Issue jetzt bearbeitet wird

### Waehrend der Arbeit
1. Nur das aktuelle Issue bearbeiten
2. Aenderungen klein halten
3. Commits mit Issue referenzieren: `fix(scope): Beschreibung (#123)`
4. Nur Dateien aendern, die fuer das Issue wirklich noetig sind

### Nach Abschluss
1. Ergebnis knapp berichten
2. Verifikation nennen
3. Offene Restpunkte nennen
4. Aenderungen committen und auf den Arbeitsbranch pushen
5. Naechstes Issue nur vorschlagen, nicht automatisch anfangen

## Parallelisierung

Parallelisierung nur dann einsetzen, wenn der User das ausdruecklich will oder wenn es klar sinnvoll ist.

Regeln:
- maximal 3 Subagents
- nur parallelisieren, wenn die Aufgaben unterschiedliche Dateien oder klar getrennte Module betreffen
- bei gemeinsamen Dateien oder gemeinsamem Datenfluss: sequentiell arbeiten
- bei Merge-Konflikt-Risiko stoppen und den User informieren

## Stop-Kriterien

Sofort stoppen und Rueckfrage stellen bei:

- Aenderungen an `.env`, Secrets, Tokens oder Credentials
- Loeschoperationen mit Datenverlust-Risiko
- Datenbankschema, Migrationen oder persistenter Datenstruktur
- Auth-/Security-Logik mit Auswirkungen auf Zugriff oder Rechte
- Deployment-/Systemd-/Docker-Aenderungen mit moeglicher Produktionswirkung
- unklarer Zustaendigkeit zwischen Bot-, API- und App-Code
- groesseren Refactorings ueber mehrere Module hinweg
- Anforderungen, die dem aktuellen Auftrag widersprechen

## Verifikation

Nach Aenderungen nur kurz und gezielt pruefen:

- bei Python-Fixes: betroffene Imports, betroffene Datei, ggf. kurzer Starttest oder vorhandene Tests
- bei API-Fixes: betroffenen Router/Dependency/Startpfad pruefen
- bei Flutter-Fixes: betroffene Datei analysieren und passende statische oder lokale Pruefung nennen
- bei Config-/Deploy-Fixes: nur sichere Validierung, keine riskanten produktiven Eingriffe ohne Rueckfrage

Wenn keine echte Ausfuehrung moeglich ist:
- klar sagen, was geprueft wurde
- klar sagen, was nicht verifiziert werden konnte
- keine Scheinsicherheit formulieren

## Grenzen

Claude soll nicht:
- ungefragt neue Architektur einfuehren
- mehrere unabhaengige Probleme in einem Durchlauf loesen
- "vorsorglich" Dateien umschreiben
- geheime Werte erfinden oder ersetzen
- Unterschiede zwischen Bot- und API-Implementierungen glattbuegeln, nur weil Namen aehnlich sind

## Tech-Stack

- Python 3.11, python-telegram-bot, OpenAI SDK (OpenRouter), FastAPI, SQLAlchemy, mem0ai
- Flutter/Dart, Riverpod
- Docker, Systemd (Hostinger VPS)

## Praktische Prioritaeten fuer dieses Repo

Wenn unklar ist, womit begonnen werden soll, bevorzuge:

1. reproduzierbare Fehler
2. Startprobleme
3. Auth- und Konfigurationsfehler
4. klare Runtime-Exceptions
5. Integration zwischen API und App
6. Deployment-/Betriebsprobleme
7. erst danach Refactorings oder Komfortverbesserungen

## Erwartetes Verhalten am Ende eines Durchlaufs

Am Ende jeder Aufgabe kurz antworten mit:

- **Geaendert:** welche Datei(en)
- **Ergebnis:** was behoben / angepasst wurde
- **Verifikation:** was geprueft wurde
- **Offen:** was noch nicht geklaert ist
