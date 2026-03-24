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
| **Proaktives Briefing** | Täglich um 08:00 Uhr |
| **Quiet Hours** | Keine Nachrichten in der Ruhezeit |
| **Wochenrückblick** | Sonntags automatisch |

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
| `/vorschlaege` | Offene Vorschläge anzeigen |
| `/tabelle` | Tabelle als Chat oder Excel-Datei |
| `/praesentation` | PowerPoint-Präsentation erstellen |

Oder einfach **frei schreiben oder eine Sprachnachricht schicken** – der Bot versteht natürliche Sprache.

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
```

---

### Schritt 3 – Google Calendar OAuth

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

> **Ohne Google Calendar** funktioniert alles außer Kalender-Features. Bot startet trotzdem.

---

### Schritt 4 – Bots starten

```bash
# Als root auf dem Server:
systemctl start personal-assistant

# Live-Logs anzeigen:
journalctl -u personal-assistant -f
```

Erfolgreich wenn du siehst:
```
Beide Bots laufen! Drücke Ctrl+C zum Beenden.
```

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

---

## Lokale Entwicklung

```bash
git clone https://github.com/schrottsocke/projekt-personal-assistent.git
cd projekt-personal-assistent
git checkout claude/dual-personal-assistants-0Uqna

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
main.py
├── TaakeBot / NinaBot       (Telegram Applications)
├── AIService                (OpenRouter + Groq Whisper)
│   ├── Intent-Erkennung     (calendar, task, timer, table, ...)
│   ├── Web-Suche            (Search-First Pattern)
│   └── Verification-Loop    (JSON-Validierung + Retry)
├── MemoryService            (mem0 + Konfidenz-Tracking)
├── CalendarService          (Google Calendar API)
├── TaskService              (SQLite, Cross-Bot-Zuweisung)
├── ReminderService          (SQLite + Startup-Delivery)
├── DocumentService          (python-pptx + openpyxl)
├── ProposalService          (Human-in-the-Loop + Auto-Approve)
└── AssistantScheduler       (APScheduler, Briefing, Quiet Hours, Fokus-Modus)
```

---

## Benötigte API-Keys

| Service | Wo holen | Kosten |
|---|---|---|
| Telegram Bot Token | @BotFather | Kostenlos |
| OpenRouter | openrouter.ai/keys | Kostenlos (free Modelle) |
| Groq (Whisper) | console.groq.com | Kostenlos (7.200 Sek./Tag) |
| Google Calendar | console.cloud.google.com | Kostenlos |
| Tavily (Web-Suche) | tavily.com | Kostenlos (1.000 Suchen/Monat) |
| OpenRouter Vision | openrouter.ai (Gemini Flash) | Kostenlos |
