# Deploy auf Hostinger VPS via GitHub Actions

## Uebersicht

Nach jedem Merge auf `main` deployt GitHub Actions automatisch auf den Hostinger VPS.
Der Workflow nutzt den Webhook-Deployer (`deploy/webhook_deployer.py`) auf Port 9000.
Workflow-Datei: `.github/workflows/deploy-hostinger.yml`

## Voraussetzungen

### 1. VPS muss einmalig provisioniert sein

Bevor der automatische Deploy funktioniert, muss der VPS einmal manuell eingerichtet werden:

```bash
ssh root@<VPS_IP>
bash /home/assistant/projekt-personal-assistent/deploy/setup_server.sh
nano /home/assistant/projekt-personal-assistent/.env   # Secrets eintragen
```

### 2. Webhook-Deployer muss laufen

Der Webhook-Deployer laeuft als systemd Service auf Port 9000:

```bash
systemctl status personal-assistant-webhook
```

Er wird automatisch beim Serverstart gestartet. Der Service braucht `WEBHOOK_SECRET` in der `.env`.

### 3. GitHub Secrets setzen

Gehe zu: **GitHub Repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret | Wert | Pflicht |
|--------|------|---------|
| `HOSTINGER_WEBHOOK_URL` | `http://<VPS_IP>:9000/deploy` | Ja |
| `HOSTINGER_WEBHOOK_SECRET` | Wert von `WEBHOOK_SECRET` aus `.env` auf dem VPS | Ja |
| `HOSTINGER_HEALTH_URL` | `http://<VPS_IP>:8000/health` (oder `http://<VPS_IP>/health` mit Nginx) | Empfohlen |

**WEBHOOK_SECRET** auf dem VPS anzeigen:

```bash
grep WEBHOOK_SECRET /home/assistant/projekt-personal-assistent/.env
```

### Alte SSH-Secrets (nicht mehr benoetigt)

Die folgenden Secrets koennen geloescht werden:
- `HOSTINGER_HOST`
- `HOSTINGER_PORT`
- `HOSTINGER_USER`
- `HOSTINGER_SSH_KEY`
- `HOSTINGER_KNOWN_HOSTS`

## Deploy ausloesen

### Automatisch

Jeder Push/Merge auf `main` startet den Deploy automatisch.

### Manuell (workflow_dispatch)

1. GitHub Repo oeffnen
2. **Actions** → **Deploy to Hostinger VPS** (links)
3. **Run workflow** → Branch `main` auswaehlen → **Run workflow**

## Was der Deploy tut

1. GitHub Actions sendet einen signierten Webhook an den VPS (Port 9000)
2. Der Webhook-Deployer verifiziert die HMAC-Signatur
3. Bei gueltigem Webhook:
   - `git pull --rebase origin main`
   - `pip install -r requirements.txt`
   - Restart: `personal-assistant`, `personal-assistant-api`, `personal-assistant-webhook`
4. GitHub Actions wartet 30 Sekunden
5. Health-Check gegen die API

## App-URL

### Mit Nginx (empfohlen)

| URL | Inhalt |
|-----|--------|
| `http://<VPS_IP>/` | Landing Page |
| `http://<VPS_IP>/app` | Web-App (SPA) |
| `http://<VPS_IP>/health` | Health-Check JSON |
| `http://<VPS_IP>/docs` | API-Dokumentation |

### Ohne Nginx (Direktzugriff)

| URL | Inhalt |
|-----|--------|
| `http://<VPS_IP>:8000/` | Landing Page |
| `http://<VPS_IP>:8000/app` | Web-App (SPA) |
| `http://<VPS_IP>:8000/health` | Health-Check JSON |

### Mit eigener Domain + SSL

1. DNS A-Record: `deine-domain.de` → `<VPS_IP>`
2. SSL einrichten: `bash deploy/setup_ssl.sh deine-domain.de`
3. HTTPS-Block in `deploy/nginx.conf` aktivieren

## Fehlerbehebung

### Webhook-Deploy schlaegt fehl

1. GitHub Actions → Run oeffnen → Logs lesen
2. Haeufige Ursachen:
   - `HOSTINGER_WEBHOOK_SECRET` stimmt nicht mit `.env` auf dem VPS ueberein
   - Webhook-Deployer laeuft nicht: `systemctl status personal-assistant-webhook`
   - Port 9000 nicht in Hostinger-Firewall offen

### Services laufen nicht

```bash
journalctl -u personal-assistant -n 30 --no-pager
journalctl -u personal-assistant-api -n 30 --no-pager
journalctl -u personal-assistant-webhook -n 30 --no-pager
```
