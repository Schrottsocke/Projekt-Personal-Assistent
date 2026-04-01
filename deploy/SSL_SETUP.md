# SSL/HTTPS Setup – dualmind.cloud

## Uebersicht

| Komponente     | Wert                              |
|----------------|-----------------------------------|
| Domain         | dualmind.cloud                    |
| VPS IP         | 72.62.152.187                     |
| Webserver      | Nginx (Reverse Proxy)             |
| Zertifikat     | Let's Encrypt (certbot)           |
| Auto-Renewal   | systemd certbot.timer             |
| App-Port       | 8000 (FastAPI, intern)            |
| HTTPS-Port     | 443 (Nginx)                       |

---

## Ersteinrichtung

### 1. DNS konfigurieren (Hostinger hPanel)

**hPanel → Domains → dualmind.cloud → DNS Zone:**

| Typ   | Name  | Wert            | TTL   |
|-------|-------|-----------------|-------|
| A     | @     | 72.62.152.187   | 14400 |
| CNAME | www   | dualmind.cloud  | 14400 |

Propagation pruefen:
```bash
dig +short dualmind.cloud
# Erwartung: 72.62.152.187
```

### 2. Firewall – Port 443 oeffnen

**hPanel → VPS → Firewall → Regel hinzufuegen:**
- Protokoll: TCP
- Port: 443
- Quelle: Alle (0.0.0.0/0)

### 3. Temporaere HTTP-Config deployen

Fuer die initiale Zertifikatsausstellung muss Nginx HTTP auf Port 80 bedienen:

```bash
# Auf dem VPS:
cd /home/assistant/projekt-personal-assistent
git pull origin main

# Temporaer die HTTP-only Config verwenden (siehe Kommentar am Ende von nginx.conf)
# Dann:
sudo cp deploy/nginx.conf /etc/nginx/sites-available/dualmind-api
sudo ln -sf /etc/nginx/sites-available/dualmind-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### 4. SSL-Zertifikat ausstellen

```bash
sudo bash deploy/setup_ssl.sh dualmind.cloud
```

Das Script:
- Prueft DNS-Aufloesung
- Installiert certbot
- Fordert Let's Encrypt Zertifikat an (inkl. www falls DNS gesetzt)
- Aktiviert Auto-Renewal

### 5. HTTPS-Config aktivieren

Nach erfolgreichem certbot die finale Nginx-Config deployen:

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/dualmind-api
sudo nginx -t && sudo systemctl reload nginx
```

### 6. Verifizierung

```bash
# HTTP → HTTPS Redirect
curl -I http://dualmind.cloud
# Erwartung: 301 → https://dualmind.cloud/

# HTTPS funktioniert
curl -I https://dualmind.cloud
# Erwartung: 200 OK

# API Health Check
curl https://dualmind.cloud/health
# Erwartung: {"status": "ok", ...}

# Auto-Renewal testen
sudo certbot renew --dry-run

# SSL-Qualitaet pruefen (extern)
# https://www.ssllabs.com/ssltest/analyze.html?d=dualmind.cloud
```

---

## Zertifikat-Erneuerung

Let's Encrypt Zertifikate sind 90 Tage gueltig. Certbot erneuert automatisch via systemd timer.

```bash
# Timer-Status pruefen
systemctl status certbot.timer

# Manuelle Erneuerung
sudo certbot renew

# Dry-Run (ohne echte Erneuerung)
sudo certbot renew --dry-run
```

---

## Troubleshooting

### Zertifikat abgelaufen
```bash
sudo certbot renew --force-renewal
sudo nginx -t && sudo systemctl reload nginx
```

### Nginx laesst sich nicht starten
```bash
sudo nginx -t                    # Config-Fehler anzeigen
sudo journalctl -u nginx -n 50  # Logs pruefen
```

### Port 443 nicht erreichbar
1. Hostinger Firewall pruefen (hPanel → VPS → Firewall)
2. `sudo ss -tlnp | grep 443` → Nginx muss auf 443 lauschen

### DNS zeigt nicht auf VPS
```bash
dig +short dualmind.cloud
# Falls nicht 72.62.152.187: DNS-Record in Hostinger hPanel korrigieren
```

### Zertifikat fuer www fehlt
```bash
sudo certbot --nginx -d dualmind.cloud -d www.dualmind.cloud
```

---

## Rollback auf HTTP-only

Falls HTTPS Probleme macht, temporaer zurueck auf HTTP:

```bash
# In deploy/nginx.conf: HTTPS-Bloecke auskommentieren,
# HTTP-only Block aus dem FIRST-TIME SETUP Kommentar aktivieren
sudo cp deploy/nginx.conf /etc/nginx/sites-available/dualmind-api
sudo nginx -t && sudo systemctl reload nginx
```

---

## CORS fuer Produktion

In `.env` auf dem VPS:
```
API_CORS_ORIGINS=https://dualmind.cloud,https://www.dualmind.cloud
```

Danach API neustarten:
```bash
sudo systemctl restart personal-assistant-api
```

---

## Flutter App mit HTTPS bauen

```bash
flutter build apk --dart-define=API_BASE_URL=https://dualmind.cloud
```
