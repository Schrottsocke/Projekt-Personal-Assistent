# Agent Guardrails

Haeufige Fehlerquellen und Pruefpunkte fuer Claude Code bei der Arbeit an diesem Projekt.

## D1: Web-App-Architektur

**Trigger:** Aenderungen an `api/static/`, `api/main.py`, oder Routing-Logik.

**Checks:**
- Script-Ladereihenfolge in `app.html` pruefen: `utils.js` → `api.js` → `router.js` → Views → `app.js`
- Globale Funktionen (`escapeHtml`, etc.) muessen in `utils.js` definiert sein, nicht in einzelnen Views
- Hash-Routing (`#/route`) nicht mit Server-Routing (`/route`) verwechseln
- `Router.navigate()` verwendet Hash-Pfade, nicht Server-Pfade

**Anti-Pattern:**
- Globale Helfer in View-Dateien definieren (funktioniert nur wenn View zuerst geladen)
- DOM-Text-Matching fuer Datenabgleich (fragil) → stattdessen `data-*` Attribute verwenden

## D2: Auth / Storage

**Trigger:** Aenderungen an `api.js`, Login/Logout, Token-Handling.

**Checks:**
- Tokens in `localStorage` (nicht `sessionStorage`) unter Keys `dm_access_token`, `dm_refresh_token`, `dm_user_key`
- Auto-Refresh bei 401 mit Debouncing (`_refreshing` Promise)
- `Api.logout()` muss alle drei Keys loeschen und zu `#/login` navigieren

**Anti-Pattern:**
- `sessionStorage` verwenden (Tabs verlieren Login)
- Token-Refresh ohne Debouncing (Race Conditions)

## D3: Deploy / Monitoring

**Trigger:** Aenderungen an `deploy/`, Systemd-Units, Nginx-Config.

**Checks:**
- Health-Check ist `/health`, nicht `/`
- Homepage (`/`) liefert statisches HTML, keine Abhaengigkeit zu externen Services
- `.env` wird nie committed — nur `.env.example` tracken

**Anti-Pattern:**
- Health-Check auf `/` setzen (blockiert Homepage-Debugging)
- `.env` oder Secrets in Commits

## D4: Backend/Frontend-Kontrakt

**Trigger:** Aenderungen an API-Endpunkten oder JS API-Client.

**Checks:**
- `Api.*` Methoden in `api.js` muessen mit Backend-Endpunkten uebereinstimmen
- Response-Schemas pruefen (z.B. `ShoppingItemOut` Felder vs. JS-Zugriff)
- PATCH-Endpunkte: Client sendet den Zielwert, Backend setzt ihn (kein Toggle)

**Anti-Pattern:**
- Backend togglet Werte statt den Client-Wert zu uebernehmen
- Frontend erwartet Felder die das Backend nicht liefert

## D5: JS-Quality

**Trigger:** Neue oder geaenderte JavaScript-Dateien.

**Checks:**
- IIFE-Pattern (`const View = (() => { ... return { ... }; })();`)
- Alle oeffentlichen Methoden im `return`-Objekt exponieren
- `escapeHtml()` fuer alle User-generierten Inhalte in HTML verwenden
- Event-Handler als String-Attribute (`onclick="View.method()"`) muessen auf exponierte Methoden zeigen

**Anti-Pattern:**
- Inline-Funktionen in `onclick` die auf nicht-exponierte Closure-Variablen zugreifen
- HTML-Injection durch fehlende Escaping

## D6: Concurrency / External Services

**Trigger:** Aenderungen an Service-Klassen, API-Aufrufe an externe Dienste.

**Checks:**
- Graceful Degradation: Dashboard zeigt Fehlerzustand statt zu crashen wenn Services unavailable
- Rate-Limiting via `slowapi` auf Write-Endpunkten
- SQLAlchemy Sessions korrekt schliessen (Context Manager)

**Anti-Pattern:**
- Unbehandelte Exceptions bei externen API-Aufrufen
- Offene DB-Sessions nach Fehler
