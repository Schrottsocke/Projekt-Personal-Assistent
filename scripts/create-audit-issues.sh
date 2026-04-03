#!/usr/bin/env bash
# ============================================================================
# Erstellt die 6 Audit-Issues aus dem WebApp-Visibility-Audit auf GitHub.
#
# Voraussetzung: gh CLI installiert und authentifiziert
#   brew install gh && gh auth login
#
# Ausfuehrung:
#   bash scripts/create-audit-issues.sh
#
# Alternativ mit Token:
#   GH_TOKEN=ghp_xxx bash scripts/create-audit-issues.sh
# ============================================================================

set -euo pipefail

REPO="Schrottsocke/Projekt-Personal-Assistent"

echo "Erstelle 6 Audit-Issues auf $REPO ..."
echo ""

# ---- Issue 1: P0 – Service Worker skipWaiting ----
echo "[1/6] Service Worker skipWaiting ..."
gh issue create --repo "$REPO" \
  --title "fix(webapp): Service Worker blockiert Updates – skipWaiting() und clients.claim() fehlen" \
  --label "P0-critical,webapp" \
  --body "$(cat <<'ISSUE_EOF'
## Problem

Der Service Worker (`api/static/sw.js`) verwendet eine cache-first Strategie ohne `self.skipWaiting()` und `self.clients.claim()`. Wenn eine neue SW-Version installiert wird (z.B. nach Deploy), bleibt sie im "waiting"-Status bis der User **alle** Browser-Tabs mit der App schliesst.

**Bestaetigt:** Desktop zeigt altes Design (alter SW cached), Mobil zeigt neues Design (frischer SW oder kein alter Cache).

## Ursache

- `sw.js` Zeile 36-38: `install`-Event cached Assets, ruft aber nicht `self.skipWaiting()` auf
- `sw.js` Zeile 40-46: `activate`-Event loescht alte Caches, ruft aber nicht `self.clients.claim()` auf
- `sw.js` Zeile 53-55: Cache-first Strategie (`caches.match(e.request).then((r) => r || fetch(e.request))`) liefert gecachte alte Dateien

## Betroffene Dateien

- `api/static/sw.js`

## Reproduktion

1. Oeffne https://dualmind.cloud/app auf Desktop-Browser
2. DevTools > Application > Service Workers
3. Beobachte: "waiting to activate" Status bei neuer SW-Version
4. Vergleiche mit Mobil-Browser: dort ist das neue Design sichtbar

## Erwartetes Verhalten

Nach einem Deploy aktualisiert sich der Service Worker automatisch beim naechsten Seitenbesuch. Der User sieht sofort die aktuelle Version.

## Tatsaechliches Verhalten

Der alte SW bleibt aktiv. Der User sieht veraltete Inhalte bis er alle Tabs manuell schliesst.

## Technische Hinweise / Fix-Vorschlag

```js
// install
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((c) => c.addAll(SHELL_ASSETS))
  );
  self.skipWaiting(); // Sofort aktivieren
});

// activate
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim(); // Sofort alle Tabs uebernehmen
});
```

Cache-Version auf `dualmind-v4` bumpen.

## Akzeptanzkriterien

- [ ] `self.skipWaiting()` im install-Event
- [ ] `self.clients.claim()` im activate-Event
- [ ] Cache-Version gebumpt
- [ ] Nach Deploy + Reload zeigt Desktop die aktuelle Version
- [ ] Kein manuelles Tab-Schliessen noetig
ISSUE_EOF
)"

# ---- Issue 2: P0 – Cache-Busting ----
echo "[2/6] Cache-Busting ..."
gh issue create --repo "$REPO" \
  --title "fix(webapp): Statische Assets ohne Cache-Busting – Browser liefert veraltete JS/CSS" \
  --label "P0-critical,webapp" \
  --body "$(cat <<'ISSUE_EOF'
## Problem

Alle JS- und CSS-Referenzen in `app.html` verwenden nackte Pfade ohne Versions-Suffix:

```html
<script src="/static/js/app.js"></script>
<link rel="stylesheet" href="/static/css/app.css">
```

Browser und Service Worker cachen diese URLs. Wenn der Server eine neue Version der Datei hat, fragt der Browser nicht nach, weil die URL identisch ist.

## Ursache

- `api/static/app.html`: 24 Script-Tags + 1 CSS-Link ohne `?v=hash` oder Content-Hash im Dateinamen
- `api/static/sw.js`: SHELL_ASSETS-Liste referenziert ebenfalls nackte Pfade
- Kein Build-Prozess der Hashes generiert (vanilla JS, kein Bundler)

## Betroffene Dateien

- `api/static/app.html` – Script/CSS-Tags
- `api/static/sw.js` – SHELL_ASSETS Array
- `api/main.py` – app.html Auslieferung (muss Version injizieren)

## Technische Hinweise / Fix-Vorschlag

1. Bei FastAPI-Startup den Git-Commit-Hash lesen:
   ```python
   import subprocess
   _COMMIT_HASH = subprocess.run(
       ["git", "rev-parse", "--short", "HEAD"],
       capture_output=True, text=True
   ).stdout.strip() or "dev"
   ```

2. `app.html` als Template mit Version rendern (String-Replace oder Jinja2):
   ```python
   @app.get("/app", include_in_schema=False)
   async def web_app_root():
       html = (_static_dir / "app.html").read_text()
       html = html.replace("__VERSION__", _COMMIT_HASH)
       return HTMLResponse(html)
   ```

3. In `app.html` Platzhalter verwenden:
   ```html
   <script src="/static/js/app.js?v=__VERSION__"></script>
   ```

4. SW CACHE_NAME an Version koppeln: `'dualmind-' + version`

## Akzeptanzkriterien

- [ ] Alle Script/CSS-Tags enthalten `?v=<commit-hash>`
- [ ] Nach Deploy laedt der Browser automatisch neue Assets
- [ ] SW CACHE_NAME enthaelt oder korreliert mit Deploy-Version
- [ ] `app.html` (HTML-Shell) wird mit `Cache-Control: no-cache` ausgeliefert
ISSUE_EOF
)"

# ---- Issue 3: P1 – Deployer Self-Restart ----
echo "[3/6] Deployer Self-Restart ..."
gh issue create --repo "$REPO" \
  --title "fix(deploy): Webhook-Deployer restartet sich selbst und hat keine Erfolgsverifikation" \
  --label "P1-high,deploy" \
  --body "$(cat <<'ISSUE_EOF'
## Problem

1. **Self-Restart:** Der Webhook-Deployer (`deploy/webhook_deployer.py`, Zeile 36) listet sich selbst in der SERVICES-Liste:
   ```python
   SERVICES = ["personal-assistant", "personal-assistant-api", "personal-assistant-webhook"]
   ```
   Beim `systemctl restart personal-assistant-webhook` wird der Deploy-Thread beendet, bevor moeglicherweise der API-Service neugestartet wurde.

2. **Keine Verifikation:** Nach `git pull` + `pip install` + `systemctl restart` (Zeilen 90-131) gibt es keinen Health-Check. Wenn die API nicht startet, bemerkt es niemand.

## Betroffene Dateien

- `deploy/webhook_deployer.py`

## Reproduktion

1. Merge einen PR auf main
2. Webhook feuert, Deployer startet
3. Deployer restartet sich selbst bei Zeile 125-128
4. Falls der API-Restart danach scheitert, gibt es keinen Alert

## Technische Hinweise / Fix-Vorschlag

```python
# Self-Restart aus der Liste entfernen
SERVICES = ["personal-assistant", "personal-assistant-api"]

# Nach Restart: Health-Check
import urllib.request
for attempt in range(5):
    try:
        resp = urllib.request.urlopen("http://localhost:8000/health", timeout=5)
        if resp.status == 200:
            logger.info("Health-Check OK nach Deploy")
            break
    except Exception:
        time.sleep(5)
else:
    logger.error("Health-Check nach Deploy fehlgeschlagen!")
```

## Akzeptanzkriterien

- [ ] Deployer restartet sich nicht mehr waehrend des Deployments
- [ ] Post-Deploy Health-Check gegen localhost:8000/health
- [ ] Bei Health-Check-Fehler wird geloggt (und idealerweise benachrichtigt)
ISSUE_EOF
)"

# ---- Issue 4: P1 – HTTP Cache-Header ----
echo "[4/6] HTTP Cache-Header ..."
gh issue create --repo "$REPO" \
  --title "fix(deploy): Keine HTTP Cache-Header fuer statische Dateien und HTML" \
  --label "P1-high,deploy,webapp" \
  --body "$(cat <<'ISSUE_EOF'
## Problem

Weder Nginx noch FastAPI setzen explizite HTTP Cache-Header:
- `deploy/nginx.conf`: Reiner Reverse-Proxy, kein Cache-Control, kein expires
- FastAPI StaticFiles: Setzt nur Last-Modified (Browser-Verhalten unvorhersehbar)
- HTML-Seiten (/, /app): Kein no-cache Header – Browser cached auch die App-Shell

## Betroffene Dateien

- `deploy/nginx.conf`
- Alternativ: `api/main.py` (Middleware oder Response-Header)

## Technische Hinweise / Fix-Vorschlag

**Option A: Nginx-Konfiguration**
```nginx
# HTML-Seiten: Immer neu laden
location = /app {
    proxy_pass http://127.0.0.1:8000;
    add_header Cache-Control "no-cache, must-revalidate" always;
}

# Statische Assets mit Version: Lang cachen
location /static/ {
    proxy_pass http://127.0.0.1:8000;
    expires 1y;
    add_header Cache-Control "public, immutable" always;
}
```

**Option B: FastAPI-Middleware**
```python
@app.middleware("http")
async def cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path in ("/app", "/"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response
```

## Akzeptanzkriterien

- [ ] /app antwortet mit Cache-Control: no-cache
- [ ] /static/* antwortet mit Cache-Control: public, max-age=31536000, immutable (wenn Assets versioniert)
- [ ] API-Endpoints haben kein ungewolltes Caching
ISSUE_EOF
)"

# ---- Issue 5: P2 – Version in Health ----
echo "[5/6] Version in Health-Endpoint ..."
gh issue create --repo "$REPO" \
  --title "feat(api): Deployed-Version im Health-Endpoint anzeigen" \
  --label "P2-medium,api" \
  --body "$(cat <<'ISSUE_EOF'
## Problem

GET /health gibt nur Service-Status zurueck (status + services), aber keinen Commit-Hash oder Build-Timestamp. Es gibt keine Moeglichkeit remote zu verifizieren, welche Code-Version auf dem VPS deployed ist, ohne SSH-Zugang.

## Betroffene Dateien

- `api/main.py` (Funktion health(), Zeile 261-316)

## Technische Hinweise / Fix-Vorschlag

```python
# Bei Startup einmalig lesen
import subprocess, datetime
_DEPLOY_COMMIT = subprocess.run(
    ["git", "rev-parse", "--short", "HEAD"],
    capture_output=True, text=True
).stdout.strip() or "unknown"
_DEPLOY_TIME = datetime.datetime.utcnow().isoformat() + "Z"

# In health() Response einbauen
return JSONResponse(
    status_code=status_code,
    content={
        "status": status_str,
        "commit": _DEPLOY_COMMIT,
        "deployed_at": _DEPLOY_TIME,
        "services": checks,
    },
)
```

## Akzeptanzkriterien

- [ ] GET /health enthaelt "commit" und "deployed_at" Felder
- [ ] Commit-Hash stimmt mit origin/main HEAD ueberein nach Deploy
- [ ] Endpoint bleibt ohne Auth erreichbar
ISSUE_EOF
)"

# ---- Issue 6: P2 – Deploy-Benachrichtigung ----
echo "[6/6] Deploy-Benachrichtigung ..."
gh issue create --repo "$REPO" \
  --title "feat(deploy): Deploy-Benachrichtigung nach Webhook-Deployment" \
  --label "P2-medium,deploy" \
  --body "$(cat <<'ISSUE_EOF'
## Problem

Nach einem PR-Merge + Webhook-Deploy gibt es keine externe Benachrichtigung ob das Deployment erfolgreich war. Der Deployer loggt zwar lokal, aber ohne SSH sieht man nicht ob es funktioniert hat.

## Betroffene Dateien

- `deploy/webhook_deployer.py`

## Technische Hinweise / Fix-Vorschlag

Nach erfolgreichem Deploy eine Telegram-Nachricht ueber den bestehenden Bot senden:

```python
def _notify_deploy(success: bool, commit: str, details: str):
    import urllib.request, json, os
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("DEPLOY_NOTIFY_CHAT_ID")
    if not token or not chat_id:
        return
    emoji = "OK" if success else "FEHLER"
    text = f"[{emoji}] Deploy {'erfolgreich' if success else 'fehlgeschlagen'}\nCommit: {commit}\n{details[:500]}"
    data = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data, headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f"Deploy-Notification fehlgeschlagen: {e}")
```

## Akzeptanzkriterien

- [ ] Nach erfolgreichem Deploy: Telegram-Nachricht mit Commit-Hash
- [ ] Nach fehlgeschlagenem Deploy: Telegram-Warnung mit Fehlerdetails
- [ ] Benachrichtigung ist optional (graceful degradation wenn Token fehlt)
ISSUE_EOF
)"

echo ""
echo "Alle 6 Issues erstellt."
echo "Labels pruefen: Falls P0-critical, P1-high, P2-medium noch nicht existieren,"
echo "werden sie automatisch angelegt."
