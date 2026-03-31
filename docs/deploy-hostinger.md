# Deploy auf Hostinger VPS via GitHub Actions

## Uebersicht

Nach jedem Merge auf `main` deployt GitHub Actions automatisch auf den Hostinger VPS.
Workflow-Datei: `.github/workflows/deploy-hostinger.yml`

## Voraussetzungen

### 1. VPS muss einmalig provisioniert sein

Bevor der automatische Deploy funktioniert, muss der VPS einmal manuell eingerichtet werden:

```bash
ssh root@<VPS_IP>
bash /home/assistant/projekt-personal-assistent/deploy/setup_server.sh
nano /home/assistant/projekt-personal-assistent/.env   # Secrets eintragen
```

Falls das Repo noch nicht auf dem VPS liegt, klont `setup_server.sh` es automatisch.

### 2. SSH-Key fuer GitHub Actions erzeugen

Auf deinem lokalen Rechner:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/hostinger_deploy -C "github-actions-deploy" -N ""
```

Den **oeffentlichen** Key auf den VPS kopieren:

```bash
ssh-copy-id -i ~/.ssh/hostinger_deploy.pub root@<VPS_IP>
```

Oder manuell:

```bash
cat ~/.ssh/hostinger_deploy.pub | ssh root@<VPS_IP> 'cat >> ~/.ssh/authorized_keys'
```

### 3. GitHub Secrets setzen

Gehe zu: **GitHub Repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret | Wert | Pflicht |
|--------|------|---------|
| `HOSTINGER_HOST` | VPS-IP, z.B. `72.62.152.187` | Ja |
| `HOSTINGER_PORT` | SSH-Port, z.B. `22` | Ja |
| `HOSTINGER_USER` | SSH-User, z.B. `root` | Ja |
| `HOSTINGER_SSH_KEY` | Inhalt von `~/.ssh/hostinger_deploy` (Private Key!) | Ja |
| `HOSTINGER_KNOWN_HOSTS` | Ausgabe von `ssh-keyscan -p 22 <VPS_IP>` | Empfohlen |
| `DEPLOY_PATH` | Projektpfad auf dem VPS (Standard: `/home/assistant/projekt-personal-assistent`) | Optional |

**HOSTINGER_SSH_KEY** einfuegen:

```bash
cat ~/.ssh/hostinger_deploy
```

Den gesamten Inhalt (inkl. `-----BEGIN/END-----` Zeilen) als Secret-Wert einfuegen.

**HOSTINGER_KNOWN_HOSTS** erzeugen (empfohlen fuer sichere Verbindung):

```bash
ssh-keyscan -p 22 <VPS_IP> 2>/dev/null
```

Ausgabe als Secret-Wert einfuegen.

## Deploy ausloesen

### Automatisch

Jeder Push/Merge auf `main` startet den Deploy automatisch.

### Manuell (workflow_dispatch)

1. GitHub Repo oeffnen
2. **Actions** → **Deploy to Hostinger VPS** (links)
3. **Run workflow** → Branch `main` auswaehlen → **Run workflow**

## Was der Deploy tut

1. SSH-Verbindung zum VPS aufbauen
2. `git pull origin main` (als User `assistant`)
3. `pip install -r requirements.txt` (im virtualenv)
4. Restart: `personal-assistant`, `personal-assistant-api`, `personal-assistant-webhook`
5. 5 Sekunden warten
6. Alle drei Services auf `active` pruefen
7. Health-Check: `curl http://127.0.0.1:8000/health`
8. Web-App-Check: `curl http://127.0.0.1:8000/app`
9. Commit-Hash und Timestamp ausgeben

Bei Fehlern bricht der Deploy ab und zeigt die letzten 15 Log-Zeilen des fehlerhaften Services.

## App-URL

### Mit Nginx (empfohlen)

Wenn Nginx auf dem VPS eingerichtet ist (`deploy/nginx.conf`):

| URL | Inhalt |
|-----|--------|
| `http://<VPS_IP>/` | Landing Page |
| `http://<VPS_IP>/app` | Web-App (SPA) |
| `http://<VPS_IP>/health` | Health-Check JSON |
| `http://<VPS_IP>/docs` | API-Dokumentation |

Nginx einrichten (einmalig auf dem VPS):

```bash
apt install -y nginx
cp /home/assistant/projekt-personal-assistent/deploy/nginx.conf /etc/nginx/sites-available/dualmind-api
ln -sf /etc/nginx/sites-available/dualmind-api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

### Ohne Nginx (Direktzugriff)

| URL | Inhalt |
|-----|--------|
| `http://<VPS_IP>:8000/` | Landing Page |
| `http://<VPS_IP>:8000/app` | Web-App (SPA) |
| `http://<VPS_IP>:8000/health` | Health-Check JSON |

Port 8000 muss in der Hostinger-Firewall geoeffnet sein.

### Mit eigener Domain + SSL

1. DNS A-Record: `deine-domain.de` → `<VPS_IP>`
2. Nginx aktivieren (siehe oben)
3. SSL einrichten: `bash /home/assistant/projekt-personal-assistent/deploy/setup_ssl.sh deine-domain.de`
4. HTTPS-Block in `nginx.conf` aktivieren (Anleitung in der Datei)

## Offene Blocker fuer oeffentliche App-URL

| Blocker | Loesung |
|---------|---------|
| Nginx nicht installiert | `apt install -y nginx` + Config kopieren (siehe oben) |
| Port 80 nicht offen | Hostinger → VPS → Firewall → TCP Port 80 freigeben |
| Port 8000 nicht offen (ohne Nginx) | Hostinger → VPS → Firewall → TCP Port 8000 freigeben |
| Keine Domain | App ist ueber IP erreichbar, Domain ist optional |
| Kein SSL | Funktioniert ueber HTTP, SSL optional via `setup_ssl.sh` |

## Fehlerbehebung

### Deploy schlaegt fehl

1. GitHub Actions → den fehlgeschlagenen Run oeffnen → Logs lesen
2. Haeufige Ursachen:
   - SSH-Key falsch → `HOSTINGER_SSH_KEY` pruefen
   - VPS nicht erreichbar → Firewall/Port 22 pruefen
   - Service startet nicht → `.env` auf dem VPS pruefen (Pflichtfelder fehlen?)
   - `venv` fehlt → `setup_server.sh` wurde nicht ausgefuehrt

### Services laufen nicht

Auf dem VPS pruefen:

```bash
journalctl -u personal-assistant -n 30 --no-pager
journalctl -u personal-assistant-api -n 30 --no-pager
journalctl -u personal-assistant-webhook -n 30 --no-pager
```
