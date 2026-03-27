# Changelog

## [Unreleased] - Session 3 Bugfix (2026-03-27)

### Bug Fixes

- **fix(ai_service): NameError in _detect_intent behoben (L248)**
  Die Variable fuer den Intent-Classifier-Prompt hiess `prompt`, wurde aber als `system_prompt` in der OpenAI-Message referenziert (L285). Das fuehrte zu einem `NameError` bei JEDER eingehenden Nachricht. Fix: Variable von `prompt` auf `system_prompt` umbenannt.

- **fix(settings): get_system_prompt() Methode ergaenzt**
  `ai_service.py` rief `settings.get_system_prompt(user_key)` auf, aber die Methode existierte nicht in der `Settings`-Klasse. Das fuehrte zu einem `AttributeError` bei jeder Chat-Antwort. Fix: Neue Instanzmethode `get_system_prompt(user_key)` in `config/settings.py` ergaenzt, die personalisierte System-Prompts pro User (taake/nina) zurueckgibt.

### Betroffene Dateien

- `src/services/ai_service.py` (Zeile 248: prompt -> system_prompt)
- `config/settings.py` (Neue Methode: get_system_prompt)

### Verifizierung

- Syntax-Check: beide Dateien OK (ast.parse)
- Funktionstest: settings.get_system_prompt() gibt korrekte Prompts fuer taake, nina, None und unbekannte Keys zurueck



## [Unreleased] - Session 2 (2026-03-26)

### Neue Features

#### `src/services/weather_service.py` (NEU)

**Neuer dedizierter Wetter-Service** basierend auf [wttr.in](https://wttr.in) (kostenlos, kein API-Key erforderlich).

**Funktionen:**
- `get_weather(location, lang)`: Ruft aktuelles Wetter + 2-Tage-Vorhersage als formatierte Nachricht ab (JSON-API)
- `get_weather_simple(location)`: Einfaches Wetter-Format als Fallback
- Liefert: Temperatur, Gefuehlte Temperatur, Min/Max, Wetterbeschreibung, Luftfeuchtigkeit, Wind
- Unterstuetzt deutsche Sprachausgabe (`lang=de`)

**Warum:** DuckDuckGo blockiert VPS-IPs mit HTTP 202 Rate Limit, weshalb Wetteranfragen nie Ergebnisse lieferten. wttr.in funktioniert zuverlaessig ohne API-Key.

---

#### `/marketplace` Befehl (NEU)

**Neuer Telegram-Befehl** `/marketplace` zeigt alle verfuegbaren Features und deren Konfigurationsstatus.

**Geaenderte Dateien:**
- `src/handlers/command_handlers.py`: Neue Funktion `cmd_marketplace()` am Ende der Datei hinzugefuegt
- `src/bots/base_bot.py`: `BotCommand("marketplace", "Feature-Marktplatz - verfuegbare Funktionen")` in `set_commands()` eingetragen

**Features im Marketplace (11 gesamt):**
| Feature | Befehl | Aktivierung via |
|---|---|---|
| Google Kalender | `/kalender` | `GOOGLE_CALENDAR_ENABLED` |
| Google Drive | `/drive` | `GOOGLE_DRIVE_ENABLED` |
| Spotify | `/spotify` | `SPOTIFY_CLIENT_ID` |
| Smart Home | `/smarthome` | `HOMEASSISTANT_URL` |
| E-Mail | `/email` | `GMAIL_CREDENTIALS_FILE` |
| Wetter | `/wetter` | `WEATHER_ENABLED` |
| Websuche | `/suche` | `WEB_SEARCH_ENABLED` |
| TTS / Sprachantwort | `/tts` | `GROQ_API_KEY` |
| Google Rezepte | `/rezept` | `RECIPE_ENABLED` |
| Fahrzeit | `/fahrzeit` | `OPENROUTE_API_KEY` |
| Gemeinsamer Kalender | `/gemeinsam` | `PARTNER_BOT_TOKEN` |

---

### Bugfixes & Aenderungen

#### `src/services/ai_service.py`

**Wetter-Routing hinzugefuegt:**
- Neue `weather_service` Property (Lazy Init) fuer `WeatherService`
- In `_handle_web_search()`: Bei Wetter-Keywords (`wetter`, `weather`, `temperatur`, `regen`, `sonne`, `grad`, `forecast`, `vorhersage`) wird jetzt zuerst der `WeatherService` aufgerufen statt DuckDuckGo
- Standort-Erkennung via Regex aus der Nachricht, Fallback: Schwerin
- Erst wenn WeatherService kein Ergebnis liefert, wird WebSearch als Fallback genutzt
- `self._weather = None` in `__init__` als Lazy-Init-Variable hinzugefuegt

**AI-Modell geaendert (`.env` auf Server):**
- `AI_MODEL` von `openrouter/free` auf `nvidia_fallback` geaendert
- Grund: OpenRouter haengte Anfragen ohne Timeout-Fehler → Bot blockierte dauerhaft
- NVIDIA NIM (meta/llama-3.3-70b-instruct) laeuft stabil und kostenlos

#### `src/services/web_search.py` / Abhaengigkeiten

**Fehlende Pakete installiert:**
- `duckduckgo-search==6.3.7` war in `requirements.txt` gelistet aber nicht in der venv installiert
- `tavily-python==0.5.0` ebenfalls nachinstalliert
- Beide Pakete via `venv/bin/pip install` in die venv des `assistant`-Users installiert
- **Hinweis:** DuckDuckGo liefert auf VPS-IPs Rate Limit (HTTP 202) → fuer Websuche ggf. Tavily API Key empfohlen

---

### Infrastruktur

**Service-Neustart-Sequenz dieser Session:**
1. `systemctl restart personal-assistant personal-assistant-api` (nach NVIDIA-Fix aus Session 1)
2. Neustart nach `duckduckgo-search` Installation
3. Neustart nach WeatherService-Integration
4. Neustart nach Marketplace-Implementierung

**Ergebnis:** Beide Bots (`personal-assistant`, `personal-assistant-api`) laufen stabil mit `active (running)` Status.

---

## [Unreleased] - Session 1 - Debugging Session

### Hinweis zur Code-Synchronisation
Die folgenden Aenderungen wurden direkt auf dem Hostinger VPS Server vorgenommen und sind lokal per `git commit` gespeichert. Ein `git push` erfordert einen GitHub Personal Access Token oder SSH-Key. Die aenderten Dateien auf dem Server sind aktueller als diese GitHub-Version.

---

### Geaenderte Dateien

#### `src/services/ai_service.py` (Hauptaenderung)

**Problem:** Rekursiver Fallback-Loop verursachte maximale Rekursionstiefe bei Rate Limits.

**Loesungen:**

1. **Neue Imports:**
   - `import httpx` hinzugefuegt
   - `from openai import AsyncOpenAI, RateLimitError, APITimeoutError`
   - `from tenacity import retry, stop_after_attempt, wait_exponential`

2. **Neue Konstanten:**
   - `INTENT_WEB_SEARCH = "web_search"` fuer explizite Intent-Erkennung
   - `NVIDIA_MODELS` Liste mit NVIDIA NIM Modellen als Fallback

3. **Neue/Geaenderte Methoden:**
   - `_complete()`: Entfernung des rekursiven Fallback-Mechanismus, stattdessen lineare Iteration ueber Modell-Liste
   - `_handle_web_search()`: Neue Methode fuer Web-Such-Intents mit DuckDuckGo/Tavily
   - `web_search` Property: Lazy Initialization des WebSearch-Service
   - NVIDIA NIM Konfiguration als eigenstaendiger Provider

4. **System-Prompt Erweiterung:**
   - Explizite Anweisung zur `web_search` Intent-Nutzung bei Wetter, News, aktuellen Infos

#### `src/handlers/oauth_handlers.py`

**Problem:** OAuth-Flow fuer Google Calendar schlug fehl.

**Loesungen:**
- Korrektur des Redirect-URI Handlings
- Verbesserung der Fehlerbehandlung bei abgelaufenen Tokens
- Logging-Verbesserungen fuer Debugging

#### `config/settings.py`

**Neu hinzugefuegte Umgebungsvariablen:**
- `NVIDIA_API_KEY`: API Key fuer NVIDIA NIM
- `NVIDIA_BASE_URL`: Basis-URL fuer NVIDIA NIM API (`https://integrate.api.nvidia.com/v1`)
- `NVIDIA_MODEL`: Bevorzugtes NVIDIA Modell (`meta/llama-3.3-70b-instruct`)

#### `.env.example`

**Neue Eintraege:**
```
NVIDIA_API_KEY=your_nvidia_api_key_here
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=meta/llama-3.3-70b-instruct
```
