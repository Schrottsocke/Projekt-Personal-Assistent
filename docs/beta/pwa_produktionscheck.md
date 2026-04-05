# PWA-Produktionscheck – DualMind Personal Assistant

> **Version:** 1.0
> **Datum:** 2026-04-05
> **Zweck:** Checkliste fuer den produktionsreifen Betrieb der Web-App als Progressive Web App

---

## Anleitung

Jeder Punkt wird mit einem Status versehen:

- **OK** – Pruefung bestanden
- **WARNUNG** – funktioniert, aber mit Einschraenkungen
- **FEHLER** – funktioniert nicht, muss behoben werden
- **N/A** – nicht zutreffend

---

## 1. HTTPS und Domain

| Nr. | Pruefpunkt | Status | Anmerkungen |
| --- | ---------- | ------ | ----------- |
| 1.1 | Die App ist ausschliesslich ueber HTTPS erreichbar. | | |
| 1.2 | Let's Encrypt Zertifikat ist installiert und gueltig. | | |
| 1.3 | Zertifikat laeuft nicht innerhalb der naechsten 30 Tage ab. | | |
| 1.4 | Auto-Renewal fuer das Zertifikat ist eingerichtet. | | |
| 1.5 | HTTP-Anfragen werden automatisch auf HTTPS umgeleitet (301 Redirect). | | |
| 1.6 | HSTS-Header ist gesetzt (`Strict-Transport-Security`). | | |
| 1.7 | HSTS `max-age` ist mindestens 31536000 (1 Jahr). | | |
| 1.8 | Die Domain ist korrekt konfiguriert und erreichbar. | | |
| 1.9 | Keine Mixed-Content-Warnungen im Browser (alle Ressourcen ueber HTTPS). | | |

### Pruefen mit

```bash
# Zertifikat pruefen
openssl s_client -connect example.com:443 -servername example.com 2>/dev/null | openssl x509 -noout -dates

# HSTS-Header pruefen
curl -sI https://example.com | grep -i strict-transport

# HTTP-Redirect pruefen
curl -sI http://example.com | grep -i location
```

---

## 2. PWA Manifest

| Nr. | Pruefpunkt | Status | Anmerkungen |
| --- | ---------- | ------ | ----------- |
| 2.1 | `manifest.json` (oder `manifest.webmanifest`) ist vorhanden und wird im HTML referenziert (`<link rel="manifest">`). | | |
| 2.2 | `name` ist gesetzt (vollstaendiger App-Name). | | |
| 2.3 | `short_name` ist gesetzt (max. 12 Zeichen empfohlen). | | |
| 2.4 | `start_url` ist gesetzt und zeigt auf die richtige Seite. | | |
| 2.5 | `display` ist auf `standalone` oder `fullscreen` gesetzt. | | |
| 2.6 | `theme_color` ist gesetzt und passt zum App-Design. | | |
| 2.7 | `background_color` ist gesetzt. | | |
| 2.8 | `icons` enthaelt mindestens ein 192x192 und ein 512x512 Icon (PNG). | | |
| 2.9 | Alle referenzierten Icons sind erreichbar (kein 404). | | |
| 2.10 | `scope` ist korrekt gesetzt (falls verwendet). | | |
| 2.11 | Die App ist auf Android (Chrome) installierbar – „Zum Startbildschirm hinzufuegen" erscheint. | | |
| 2.12 | Die App ist auf iOS (Safari ab 16.4) installierbar – „Zum Home-Bildschirm" funktioniert. | | |
| 2.13 | Die App ist auf Desktop (Chrome/Edge) installierbar – Install-Icon in der Adressleiste erscheint. | | |

### Pruefen mit

```bash
# Manifest abrufen
curl -s https://example.com/manifest.json | python3 -m json.tool

# Icons pruefen
curl -sI https://example.com/icon-192x192.png | head -1
curl -sI https://example.com/icon-512x512.png | head -1
```

---

## 3. Service Worker

| Nr. | Pruefpunkt | Status | Anmerkungen |
| --- | ---------- | ------ | ----------- |
| 3.1 | Service Worker wird im HTML oder App-Code registriert (`navigator.serviceWorker.register`). | | |
| 3.2 | Service Worker Datei (`sw.js`) ist erreichbar und liefert keinen Fehler. | | |
| 3.3 | Service Worker wird erfolgreich aktiviert (keine Konsolenfehler). | | |
| 3.4 | Offline-Fallback: Bei fehlender Netzwerkverbindung wird eine sinnvolle Seite oder Meldung angezeigt (kein Chrome-Dino). | | |
| 3.5 | API-GET-Anfragen werden gecacht (Stale-While-Revalidate oder Cache-First). | | |
| 3.6 | Statische Assets (HTML, CSS, JS, Icons) werden gecacht. | | |
| 3.7 | Cache-Versionierung: Bei App-Updates wird der alte Cache geloescht. | | |
| 3.8 | Update-Mechanismus: Benutzer erhaelt bei neuer Version einen Hinweis oder die App aktualisiert sich automatisch. | | |
| 3.9 | `skipWaiting` und `clients.claim` sind implementiert oder ein manueller Update-Flow existiert. | | |
| 3.10 | Kein unkontrolliertes Cache-Wachstum (Cache-Groesse wird begrenzt oder alte Eintraege werden entfernt). | | |

### Pruefen mit

- Browser DevTools → Application → Service Workers: Status pruefen
- Browser DevTools → Application → Cache Storage: Inhalte pruefen
- Netzwerk trennen (DevTools → Offline) und App neu laden

---

## 4. Kamera-Zugriff

| Nr. | Pruefpunkt | Status | Anmerkungen |
| --- | ---------- | ------ | ----------- |
| 4.1 | Kamera-Zugriff funktioniert auf Android (Chrome). | | |
| 4.2 | Kamera-Zugriff funktioniert auf iOS (Safari ab 16.4). Aeltere Versionen werden erkannt und der Benutzer informiert. | | |
| 4.3 | Kamera-Zugriff funktioniert auf Desktop (Chrome/Firefox/Edge). | | |
| 4.4 | Die App fragt die Kamera-Berechtigung (`getUserMedia` oder `<input capture>`) korrekt an. | | |
| 4.5 | Wenn der Benutzer die Berechtigung verweigert, erscheint eine verstaendliche Meldung. | | |
| 4.6 | Ein Fallback existiert fuer Geraete ohne Kamera (z.B. Datei-Upload statt Kamera). | | |
| 4.7 | Kamera-Zugriff funktioniert nur ueber HTTPS (Pflicht fuer `getUserMedia`). | | |
| 4.8 | Auf iOS im Standalone-Modus (installierte PWA) funktioniert die Kamera. | | |

### Pruefen mit

- Auf verschiedenen Geraeten die Kamera-Funktion aufrufen
- Berechtigung einmal verweigern, dann erneut versuchen
- Browser DevTools → Sensors → Kamera-Override testen

---

## 5. Push Notifications

| Nr. | Pruefpunkt | Status | Anmerkungen |
| --- | ---------- | ------ | ----------- |
| 5.1 | VAPID-Schluessel (Public + Private) sind generiert und konfiguriert. | | |
| 5.2 | Der Server kann Push-Nachrichten ueber die Web Push API senden. | | |
| 5.3 | Die App fragt den Benutzer um Erlaubnis fuer Benachrichtigungen. | | |
| 5.4 | Push-Subscription wird nach Zustimmung an den Server gesendet und gespeichert. | | |
| 5.5 | Empfangene Push-Nachrichten werden als System-Benachrichtigung angezeigt. | | |
| 5.6 | Klick auf eine Benachrichtigung oeffnet die App an der richtigen Stelle. | | |
| 5.7 | Android (Chrome): Push Notifications funktionieren zuverlaessig. | | |
| 5.8 | iOS (Safari ab 16.4): Push Notifications funktionieren mit bekannten Einschraenkungen. | | |
| 5.9 | **iOS-Einschraenkung beachtet:** Push auf iOS funktioniert NUR wenn die PWA installiert (zum Homescreen hinzugefuegt) ist. Im normalen Safari-Browser werden keine Push-Benachrichtigungen unterstuetzt. | | |
| 5.10 | **iOS-Einschraenkung beachtet:** Der Benutzer muss die App nach der Installation mindestens einmal oeffnen, bevor Push funktioniert. | | |
| 5.11 | Desktop (Chrome/Edge/Firefox): Push Notifications funktionieren. | | |
| 5.12 | Wenn der Benutzer Benachrichtigungen ablehnt, wird dies respektiert und keine erneute Abfrage erzwungen. | | |
| 5.13 | Abgelaufene oder ungueltige Subscriptions werden serverseitig bereinigt. | | |

### Pruefen mit

```bash
# VAPID-Schluessel testen (Node.js)
npx web-push send-notification --endpoint="..." --key="..." --auth="..."
```

- Browser DevTools → Application → Push Messaging
- Auf iOS: App installieren, oeffnen, Berechtigung erteilen, Testnachricht senden

---

## 6. Lighthouse-Audit

| Nr. | Pruefpunkt | Zielwert | Ergebnis | Status |
| --- | ---------- | -------- | -------- | ------ |
| 6.1 | PWA-Score | >= 90 | | |
| 6.2 | Performance-Score | >= 70 | | |
| 6.3 | Accessibility-Score | >= 80 | | |
| 6.4 | Best Practices-Score | >= 80 | | |
| 6.5 | SEO-Score (optional) | >= 70 | | |
| 6.6 | Installierbarkeit: Lighthouse meldet „Installable". | Ja | | |
| 6.7 | Kein Fehler in „PWA Optimized"-Kategorie. | 0 Fehler | | |

### Pruefen mit

```bash
# Lighthouse CLI
npx lighthouse https://example.com --output=json --output=html --output-path=./lighthouse-report

# Oder im Browser
# Chrome DevTools → Lighthouse → Bericht generieren (Kategorien: PWA, Performance, Accessibility)
```

**Wichtig:** Lighthouse-Audit immer im Inkognito-Modus durchfuehren, um Erweiterungen auszuschliessen.

---

## Ergebnis-Protokoll

### Zusammenfassung

| Bereich | OK | WARNUNG | FEHLER | N/A |
| ------- | -- | ------- | ------ | --- |
| 1. HTTPS und Domain | | | | |
| 2. PWA Manifest | | | | |
| 3. Service Worker | | | | |
| 4. Kamera-Zugriff | | | | |
| 5. Push Notifications | | | | |
| 6. Lighthouse-Audit | | | | |

### Details

| Datum | Pruefer | Gesamtbewertung | Naechste Schritte |
| ----- | ------- | --------------- | ----------------- |
| | | | |

### Offene Punkte

| Nr. | Bereich | Beschreibung | Prioritaet | Verantwortlich |
| --- | ------- | ------------ | ---------- | -------------- |
| | | | | |

---

## Wiederholungs-Rhythmus

- **Vor jedem Release:** Abschnitte 1-6 komplett pruefen.
- **Woechentlich in der Beta-Phase:** Abschnitte 3 (Service Worker) und 6 (Lighthouse) pruefen.
- **Nach Zertifikatserneuerung:** Abschnitt 1 pruefen.
- **Nach Manifest-Aenderungen:** Abschnitt 2 pruefen.
- **Nach Push-Aenderungen:** Abschnitt 5 pruefen.
