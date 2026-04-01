# Personal Assistant – DualMind

Zwei persönliche KI-Assistenten via Telegram. Jeder Bot hat eine eigene Persönlichkeit, ein gemeinsames Gedächtnis-System und lernt kontinuierlich aus Gesprächen.

---

## Features

| Feature | Beschreibung |
|---|---|
| **Zwei Bots** | TaakeBot + NinaBot, eigene Tokens, eigene Persönlichkeit |
| **Natürliche Sprache** | Kein Befehlssystem – einfach frei schreiben |
| **Voice-Input** | Sprachnachrichten via Groq Whisper Large v3 |
| **Langzeitgedächtnis** | Lernt aus Gesprächen (mem0 + Konfidenz-Tracking) |
| **Google Calendar** | Termine lesen, erstellen, erinnern |
| **Task-Management** | Aufgaben mit Priorität, Cross-Bot-Zuweisung |
| **Timer / Pomodoro** | "Timer 25 Minuten" – sofort, kein Klick nötig |
| **Trust-System** | Konfigurierbar: was direkt ausgeführt wird vs. Bestätigung |
| **Tabellen & Präsentationen** | .xlsx und .pptx per KI generiert und gesendet |
| **Web-Suche** | Wetter, Nachrichten, Preise automatisch gesucht |
| **Foto-Analyse** | Bilder & Screenshots analysieren, Intent erkennen (Vision) |
| **Fokus-Modus** | `/fokus 90` – Nachrichten + Proaktiv-Meldungen zurückhalten |
| **Tagesplanung** | Zeitgeblockte Tagesplanung im Morgen-Briefing |
| **Spotify** | Musik per Sprache steuern (Play, Pause, Skip, Suche) |
| **Smart Home** | Home Assistant Steuerung (Licht, Heizung, Rollos) |
| **Voice Output (TTS)** | `/tts` – Bot antwortet zusätzlich als Sprachnachricht |
| **Cross-User Sync** | `/gemeinsam` – Gemeinsamer Kalender + Konflikt-Erkennung |
| **Proaktives Briefing** | Täglich um 08:00 Uhr |
| **Quiet Hours** | Keine Nachrichten in der Ruhezeit |
| **Wochenrückblick** | Sonntags automatisch |
| **Einkaufsliste** | Artikel hinzufügen/abhaken, automatische Kategorien, Chefkoch-Rezept → Zutaten |
| **E-Mail (Gmail)** | Posteingang lesen, KI-Aktionen erkennen, Entwürfe erstellen |
| **Google Drive** | Dateien hochladen, durchsuchen, als Datei-Eingang nutzen |
| **Dokument-Scanner** | Foto → OCR → durchsuchbares PDF → Drive-Upload → KI-Aktionen per Proposal |
| **Mobilität** | Fahrzeit berechnen, Abfahrtszeit rückwärts (OpenRouteService) |
| **REST API** | FastAPI auf Port 8000 – alle Services als JSON-Endpunkte (JWT-Auth) |
| **Flutter App** | Native iOS/Android App: Dashboard, Einkauf, Rezepte, Chat, Profil |

---

## Befehle

| Befehl | Funktion |
|---|---|
| `/start` | Onboarding starten |
| `/hilfe` | Alle Befehle |
| `/kalender` | Kommende Termine |
| `/neu_termin` | Neuen Termin erstellen |
| `/notiz` | Notiz speichern |
| `/notizen` | Alle Notizen anzeigen |
| `/erinnerung` | Erinnerung setzen |
| `/erinnerungen` | Aktive Erinnerungen |
| `/tasks` | Offene Aufgaben |
| `/done <Nr>` | Aufgabe abhaken |
| `/briefing` | Morgen-Briefing jetzt |
| `/gedaechtnis` | Gespeicherte Fakten mit Konfidenz |
| `/autonomie` | Trust-Level konfigurieren |
| `/profil` | Persönlichkeitsprofil anzeigen/bearbeiten |
| `/fokus` | Fokus-Modus aktivieren (Minuten oder Uhrzeit) |
| `/fokus_ende` | Fokus-Modus vorzeitig beenden |
| `/gemeinsam` | Gemeinsamer Kalender + Terminüberschneidungen |
| `/tts` | Sprachantworten an/aus |
| `/spotify` | Spotify verbinden und steuern |
| `/smarthome` | Smart Home Status und Steuerung |
| `/vorschlaege` | Offene Vorschläge anzeigen |
| `/tabelle` | Tabelle als Chat oder Excel-Datei |
| `/praesentation` | PowerPoint-Präsentation erstellen |
| `/drive` | Google Drive Dateien anzeigen |
| `/einkaufsliste` | Einkaufsliste anzeigen |
| `/einkauf <Artikel>` | Artikel zur Einkaufsliste hinzufügen |
| `/rezept <Name>` | Rezept suchen + Zutaten zur Einkaufsliste hinzufügen |
| `/email` | Posteingang lesen (Gmail) |
| `/email_connect` | Gmail verbinden (OAuth2) |
| `/email_aktionen` | KI-Aktionen aus E-Mails als Vorschläge |
| `/fahrzeit <Ziel>` | Fahrzeit und Route berechnen |
| `/scan` | Anleitung zum Dokument scannen |
| `/dokumente` | Letzte 10 gescannte Dokumente |

Oder einfach **frei schreiben oder eine Sprachnachricht schicken** – der Bot versteht natürliche Sprache.

---

## REST API + Flutter App

### API-Endpunkte (FastAPI auf Port 8000)

| Endpunkt | Methode | Beschreibung |
|---|---|---|
| `/auth/login` | POST | Login mit username + password → JWT |
| `/auth/refresh` | POST | Neues Access-Token mit Refresh-Token |
| `/dashboard/today` | GET | Termine, Tasks, Shopping, E-Mails im Überblick |
| `/chat/message` | POST | Chat-Nachricht senden → KI-Antwort |
| `/chat/history` | GET | Gesprächshistorie |
| `/tasks` | GET/POST/PATCH/DELETE | Task-Verwaltung |
| `/calendar/today` | GET | Heutige Termine |
| `/calendar/week` | GET | Wochenübersicht |
| `/calendar/events` | POST | Neuen Termin anlegen |
| `/shopping/items` | GET/POST/PATCH/DELETE | Einkaufsliste |
| `/shopping/from-recipe/{id}` | POST | Rezept-Zutaten zur Liste hinzufügen |
| `/recipes/search` | GET | Chefkoch-Rezepte suchen |
| `/recipes/saved` | GET/POST/DELETE | Gespeicherte Rezepte |
| `/recipes/{id}/to-shopping` | POST | Zutaten mit Portionsskalierung übernehmen |
| `/meal-plan/week` | GET/POST/DELETE | Wochenplan |
| `/drive/files` | GET | Drive-Dateien auflisten |
| `/drive/upload` | POST | Datei hochladen |

### Flutter App starten (Entwicklung)

```bash
cd app
flutter pub get
# API-URL in lib/config/api_config.dart anpassen
flutter run
```

---

## Deployment auf Hostinger VPS

### Voraussetzungen
- Hostinger VPS mit **Ubuntu 22.04**, mind. **2 GB RAM** (KVM 2 empfohlen)
- Root-SSH-Zugang
- API-Keys bereit: Telegram (@BotFather), OpenRouter, Groq
- Google Cloud Console Projekt mit aktivierter Calendar API + credentials.json

---

### Schritt 1 – Server-Setup (einmalig, als root)

```bash
ssh root@DEINE_IP

# Setup-Skript ausführen (installiert Python, legt Benutzer an, richtet systemd ein)
git clone https://github.com/schrottsocke/projekt-personal-assistent.git /tmp/pa
bash /tmp/pa/deploy/setup_server.sh
```

Das Skript erledigt automatisch:
- System-Update + Python 3.11 + Build-Tools installieren
- Benutzer `assistant` anlegen
- Repo nach `/home/assistant/projekt-personal-assistent` klonen
- Virtualenv + alle Dependencies installieren
- Systemd-Service einrichten (Autostart bei Reboot)

Für den Dokument-Scanner zusätzlich:
```bash
apt install -y tesseract-ocr tesseract-ocr-deu
```

---

### Schritt 2 – .env befüllen

```bash
nano /home/assistant/projekt-personal-assistent/.env
```

```env
# Telegram
BOT_TOKEN_TAAKE=          # Von @BotFather
BOT_TOKEN_NINA=           # Von @BotFather
TELEGRAM_USER_ID_TAAKE=   # Deine ID: @userinfobot im Telegram fragen
TELEGRAM_USER_ID_NINA=    # Ninas ID

# AI
OPENROUTER_API_KEY=       # openrouter.ai/keys
AI_MODEL=meta-llama/llama-3.3-70b-instruct:free
AI_MODEL_FALLBACK=mistralai/mistral-7b-instruct:free

# Voice
GROQ_API_KEY=             # console.groq.com (kostenlos, 7.200 Sek./Tag)

# Einstellungen
MEMORY_MODE=local
TIMEZONE=Europe/Berlin
DATABASE_URL=sqlite:///data/assistant.db
LOG_LEVEL=INFO

# Mobilität (optional)
OPENROUTE_API_KEY=        # openrouteservice.org – kostenlos bis 2.000 Req/Tag
HOME_ADDRESS=             # z.B. "Musterstraße 1, Berlin" für Fahrzeitberechnung

# Dokument-Scanner (optional)
DRIVE_DOCUMENTS_FOLDER_ID=   # Google Drive Ordner-ID (leer = "Personal Assistant" Ordner)
OCR_CONFIDENCE_THRESHOLD=70  # Unter diesem Wert → Vision-API Fallback
SCAN_SAVE_LOCAL=true         # Lokale Kopie in data/scans/ behalten

# REST API (Flutter App)
API_SECRET_KEY=              # python -c "import secrets; print(secrets.token_hex(32))"
API_PASSWORD_TAAKE=          # App-Passwort für Taake
API_PASSWORD_NINA=           # App-Passwort für Nina
API_PORT=8000
API_CORS_ORIGINS=*
API_TOKEN_EXPIRE_DAYS=30
```

---

### Schritt 3 – Google API verbinden

Die **gleichen** `google_credentials.json` gelten für Calendar, Drive und Gmail. In der Google Cloud Console müssen alle drei APIs aktiviert sein:

- Google Calendar API
- Google Drive API
- Gmail API

Google OAuth benötigt einen Browser. **Lokal auf deinem PC** ausführen, Tokens dann hochladen.

```bash
# Lokal auf deinem PC:
pip install google-auth-oauthlib google-api-python-client
python deploy/google_auth_local.py
```

Das Skript öffnet den Browser, du meldest dich mit deinem Google-Account an und Tokens werden gespeichert. Am Ende werden die `scp`-Befehle zum Hochladen angezeigt:

```bash
scp config/google_credentials.json  assistant@IP:~/projekt-personal-assistent/config/
scp data/google_token_taake.json    assistant@IP:~/projekt-personal-assistent/data/
scp data/google_token_nina.json     assistant@IP:~/projekt-personal-assistent/data/
```

Drive und Gmail werden beim ersten Benutzen im Chat verbunden (`/email_connect`, `/drive`).

> **Ohne Google** funktioniert alles außer Kalender/Drive/Gmail-Features. Bot startet trotzdem.

---

### Schritt 4 – Bots und API starten

```bash
# Als root auf dem Server:
systemctl start personal-assistant
systemctl start personal-assistant-api

# Live-Logs anzeigen:
journalctl -u personal-assistant -f
journalctl -u personal-assistant-api -f
```

Erfolgreich wenn du siehst:
```
Beide Bots laufen! Drücke Ctrl+C zum Beenden.
```

API erreichbar unter: `http://DEINE_IP:8000/docs` (Swagger UI)

---

### Schritt 5 – Updates einspielen

```bash
# Nach Code-Änderungen: einzeiliges Update-Skript
bash /home/assistant/projekt-personal-assistent/deploy/update.sh
```

---

### Monitoring

```bash
# Status
systemctl status personal-assistant

# Letzte 100 Log-Zeilen
journalctl -u personal-assistant -n 100

# Live-Logs
journalctl -u personal-assistant -f

# Neustart
systemctl restart personal-assistant

# Stoppen
systemctl stop personal-assistant
```

---

### Bekannte Tücken

| Problem | Lösung |
|---|---|
| `pip install` schlägt bei ChromaDB fehl | `apt install -y cmake` und erneut versuchen |
| RAM zu knapp (< 2 GB) | `MEMORY_MODE=cloud` in .env + mem0-API-Key |
| Google Token läuft nach 7 Tagen ab | In Google Cloud Console Offline-Zugriff aktivieren |
| Bot startet nach Reboot nicht | `systemctl enable personal-assistant` ausführen |
| Port bereits belegt | Kein Port nötig – Bot nutzt Telegram-Polling |
| Tesseract nicht installiert | `apt install -y tesseract-ocr tesseract-ocr-deu` – OCR fällt automatisch auf Vision-API zurück |
| Drive/Gmail-Scopes fehlen | In Google Cloud Console alle drei APIs aktivieren, `credentials.json` neu herunterladen |
| API startet nicht | `API_SECRET_KEY` und `API_PASSWORD_*` in .env setzen; Port 8000 in Firewall freigeben |
| Flutter 401-Fehler | Token abgelaufen → App-Neustart oder `API_TOKEN_EXPIRE_DAYS` erhöhen |

---

## Lokale Entwicklung

```bash
git clone https://github.com/schrottsocke/projekt-personal-assistent.git
cd projekt-personal-assistent

python3.11 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env ausfüllen

python main.py
```

---

## Architektur

```
main.py                      (Telegram Bots)
├── TaakeBot / NinaBot       (Telegram Applications)
├── AIService                (OpenRouter + Groq Whisper)
│   ├── Intent-Erkennung     (calendar, task, timer, table, shopping, email, ...)
│   ├── Web-Suche            (Search-First Pattern)
│   └── Verification-Loop    (JSON-Validierung + Retry)
├── MemoryService            (mem0 + Konfidenz-Tracking)
├── CalendarService          (Google Calendar API)
├── TaskService              (SQLite, Cross-Bot-Zuweisung)
├── ReminderService          (SQLite + Startup-Delivery)
├── DocumentService          (python-pptx + openpyxl)
├── ProposalService          (Human-in-the-Loop + Auto-Approve)
├── ShoppingService          (SQLite, Kategorien, Chefkoch-API)
├── EmailService             (Gmail OAuth2, Aktionserkennung)
├── DriveService             (Google Drive API, Typen-Ordner)
├── OcrService               (pytesseract + Vision-API Fallback)
├── PdfService               (img2pdf + reportlab + pypdf, searchable PDF)
├── MobilityService          (OpenRouteService, Geocoding + Routing)
└── AssistantScheduler       (APScheduler, Briefing, Quiet Hours, E-Mail-Check)

api/api_main.py              (FastAPI REST-API, Port 8000)
├── api/auth/                (JWT Auth, Login + Refresh)
├── api/routers/             (9 Router: dashboard, chat, tasks, calendar, shopping, recipes, mealplan, drive, auth)
├── api/schemas/             (Pydantic Request/Response-Models)
├── api/dependencies.py      (Service-Singletons, get_current_user)
└── api/bot_shim.py          (ApiBotShim – AIService-Proxy ohne Telegram)

app/                         (Flutter Mobile App)
├── lib/screens/             (Login, Home, Shopping, Recipes, Chat, Profile)
├── lib/providers/           (Riverpod AsyncNotifierProviders)
├── lib/services/            (ApiService mit JWT-Interceptor, Auth, Chat, Tasks, Shopping, Recipes)
├── lib/models/              (Task, CalendarEvent, ShoppingItem, Recipe, MealPlanEntry, ChatMessage)
└── lib/widgets/             (EventCard, TaskCard, ShoppingItemTile, RecipeCard, ChatBubble)
```

---

## Benötigte API-Keys

| Service | Wo holen | Kosten |
|---|---|---|
| Telegram Bot Token | @BotFather | Kostenlos |
| OpenRouter | openrouter.ai/keys | Kostenlos (free Modelle) |
| Groq (Whisper) | console.groq.com | Kostenlos (7.200 Sek./Tag) |
| Google Calendar | console.cloud.google.com | Kostenlos |
| Google Drive | console.cloud.google.com (Drive API aktivieren) | Kostenlos |
| Google Gmail | console.cloud.google.com (Gmail API aktivieren) | Kostenlos |
| Tavily (Web-Suche) | tavily.com | Kostenlos (1.000 Suchen/Monat) |
| OpenRouter Vision | openrouter.ai (Gemini Flash) | Kostenlos |
| OpenRouteService | openrouteservice.org | Kostenlos (2.000 Req/Tag) |
| Spotify | developer.spotify.com/dashboard | Kostenlos (Premium für Steuerung) |
| Home Assistant | homeassistant.local (self-hosted) | Kostenlos |
