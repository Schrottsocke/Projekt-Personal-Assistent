# Personal Assistant – DualMind

Zwei persönliche KI-Assistenten via Telegram, basierend auf dem JARVIS-Konzept.

## Features

- **Zwei unabhängige Bots** – jeder mit eigenem Token, eigener Persönlichkeit
- **Natürliche Sprache** – kein starres Befehlssystem nötig
- **Langzeitgedächtnis** – lernt über Gespräche hinweg (mem0)
- **Google Calendar** – Termine lesen, erstellen, erinnern
- **Proaktives Briefing** – täglich automatisch um 08:00 Uhr
- **Erinnerungen** – mit natürlichen Zeitangaben setzen
- **Notizen** – privat oder geteilt

## Setup

### 1. Voraussetzungen

- Python 3.11+
- Telegram Bot Tokens (via [@BotFather](https://t.me/BotFather))
- OpenRouter API Key
- Google Cloud Console Projekt mit Calendar API

### 2. Installation

```bash
git clone <repo>
cd Projekt-Personal-Assistent
pip install -r requirements.txt
cp .env.example .env
```

### 3. .env ausfüllen

```env
BOT_TOKEN_TAAKE=...
BOT_TOKEN_NINA=...
TELEGRAM_USER_ID_TAAKE=...
TELEGRAM_USER_ID_NINA=...
OPENROUTER_API_KEY=...
```

### 4. Google Calendar (optional)

1. Google Cloud Console → neues Projekt
2. Calendar API aktivieren
3. OAuth2 Desktop-Client erstellen
4. `credentials.json` in `config/` ablegen
5. Beim ersten `/start` im Bot verbinden

### 5. Starten

**Lokal:**
```bash
python main.py
```

**Docker:**
```bash
docker-compose up -d
docker-compose logs -f
```

## Architektur

```
main.py
├── TaakeBot / NinaBot (eigene Telegram-Apps)
├── AIService (OpenRouter, Intent-Erkennung)
├── MemoryService (mem0, Langzeitgedächtnis)
├── CalendarService (Google Calendar API)
├── NotesService (SQLite)
├── ReminderService (SQLite + Scheduler)
└── AssistantScheduler (APScheduler, proaktiv)
```

## Befehle

| Befehl | Funktion |
|---|---|
| `/start` | Onboarding / Bot starten |
| `/hilfe` | Alle Befehle |
| `/kalender` | Termine anzeigen |
| `/neu_termin` | Termin erstellen |
| `/notiz` | Notiz speichern |
| `/erinnerung` | Erinnerung setzen |
| `/briefing` | Morgen-Briefing jetzt |
| `/gedaechtnis` | Gespeichertes anzeigen |

Oder einfach frei schreiben – der Bot versteht natürliche Sprache!
