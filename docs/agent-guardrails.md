# Agent Guardrails

Checklisten fuer Claude Code vor Aenderungen in spezifischen Bereichen.
Aktiviere den passenden Guard basierend auf den betroffenen Dateien.

---

## D1. Web-App-Architektur-Guard

**Trigger:** Aenderung an `api/static/js/**`

**Vor der Aenderung pruefen:**
- [ ] Keine globalen Funktionen ausserhalb `utils.js`
- [ ] Kein `innerHTML` mit unescapten Werten (immer `escapeHtml()`)
- [ ] Keine unescapten Variablen in Inline-Event-Handlern (`onclick`, `onchange`)
- [ ] DOM-Queries nach gesichertem Render oder mit Null-Check
- [ ] Script-Ladereihenfolge in `app.html` pruefen

**Anti-Pattern:**
- Helper in View-Dateien definieren statt in `utils.js`
- Elemente per DOM-Text-Matching finden statt per Data-Attribut
- `alert()` fuer Produktions-Flows

---

## D2. Auth/Storage-Guard

**Trigger:** Aenderung an `api/static/js/api.js`, `api/auth/**`, `api/routers/auth.py`

**Vor der Aenderung pruefen:**
- [ ] Storage-Typ bewusst gewaehlt (session vs local) und begruendet
- [ ] Refresh-Token-Flow: 401 → Refresh → Retry → bei Failure: Logout
- [ ] Kein Token in URL-Parametern, Logs oder Error-Messages
- [ ] Logout raeumt alle Storage-Keys auf

**Anti-Pattern:**
- Token in localStorage ohne Expiry-Check
- Refresh-Token im Klartext in Fehlermeldungen
- Mehrere parallele Refresh-Requests ohne Debouncing

---

## D3. Deploy/Monitoring-Guard

**Trigger:** Aenderung an `/`, `/health`, `/status`, `deploy/**`, `docker-compose.yml`

**Vor der Aenderung pruefen:**
- [ ] Health-Check-URLs in Deploy-Configs: `deploy/*.service`, `docker-compose.yml`
- [ ] Response-Format (JSON vs HTML) passt zu Consumer-Erwartung
- [ ] Neuer Endpoint → Deploy-Config-Update noetig?
- [ ] Nginx-Location bei neuem Pfad-Prefix pruefen

**Aktuelle Health-Check-URLs (Stand 2026-03-31):**
- systemd: `curl -sf http://localhost:8000/health`
- Docker API: `urllib.request.urlopen('http://localhost:8000/health')`
- Docker Webhook: `urllib.request.urlopen('http://localhost:9000/health')`

**Anti-Pattern:**
- Route aendern ohne Deploy-Configs anzupassen
- HTML-Antwort auf Endpoint den Monitoring als JSON erwartet

---

## D4. Backend/Frontend-Kontrakt-Guard

**Trigger:** Aenderung an `api/routers/*.py` ODER `api/static/js/api.js`

**Vor der Aenderung pruefen:**
- [ ] Request-Body-Felder werden vom Backend tatsaechlich gelesen (nicht ignoriert)
- [ ] Response-Format im Frontend korrekt konsumiert
- [ ] Endpoint-Pfade zwischen api.js und routers/*.py stimmen ueberein
- [ ] Fehler-Format (detail-Feld) wird korrekt geparst

**Bekanntes Muster:**
- `PATCH /shopping/items/{id}` TOGGLET `checked` statt den gesendeten Wert zu setzen
- Immer Backend-Implementierung pruefen, nicht nur das Schema

**Anti-Pattern:**
- Frontend sendet Wert, Backend ignoriert ihn
- Endpoint-Pfad im Frontend weicht von Router-Prefix ab

---

## D5. JS-Quality-Guard

**Trigger:** Aenderung an `api/static/**`

**Vor der Aenderung pruefen:**
- [ ] Kein neuer globaler Scope ohne IIFE/Modul-Pattern
- [ ] `escapeHtml()` fuer jeden User-Content in innerHTML
- [ ] Keine `alert()` fuer User-Feedback (UI-Element verwenden)
- [ ] Script-Ladereihenfolge in `app.html` korrekt

**Datei-Zustaendigkeiten:**
- `utils.js` – Shared Helper (escapeHtml, etc.)
- `api.js` – API-Client, Auth-Handling
- `router.js` – Hash-Router, Auth-Guard
- `views/*.js` – View-Module (je ein IIFE)
- `app.js` – View-Registrierung, Init

**Anti-Pattern:**
- Global definierte Funktion in beliebiger View-Datei
- innerHTML ohne escapeHtml bei User-Daten
- Inline-Handler mit unescapten String-Variablen

---

## D6. Concurrency/External-Service-Guard

**Trigger:** Aenderung an `src/services/*.py`, `src/scheduler/*.py`, `src/memory/*.py`

**Vor der Aenderung pruefen:**
- [ ] Kein Sync-I/O in Async-Context ohne `asyncio.to_thread()`
- [ ] Externe API-Aufrufe haben Timeout-Parameter
- [ ] Shared State hat Lock oder ist immutable
- [ ] Google OAuth Refresh mit Timeout

**Bekannte Probleme:**
- SimpleFallbackMemory nicht thread-safe (#284)
- Webhook-Deployer ohne Lock bei parallelen Deploys (#311)
- Scheduler blockiert Event-Loop mit Sync-DB-Queries (#313)
- DuckDuckGo blockiert VPS-IPs → wttr.in/Tavily als Fallback

**Anti-Pattern:**
- `requests.get()` direkt in async Handler
- Google OAuth ohne Timeout → haengt endlos
- Shared Dict ohne Lock in Multi-Thread-Kontext
