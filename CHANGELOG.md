# Changelog

## [Unreleased] - Debugging Session

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
   - `from tenacity import ... retry_if_not_exception_type` hinzugefuegt

2. **NVIDIA NIM Fallback Client (in `__init__`):**
   - Neuer `AsyncOpenAI` Client fuer NVIDIA NIM API
   - `base_url=settings.NVIDIA_BASE_URL`
   - `http_client=httpx.AsyncClient(timeout=httpx.Timeout(20.0))`
   - `max_retries=0` (kein automatisches Retry bei Rate Limits)
   - Modell: `moonshotai/kimi-k2.5` (NVIDIA NIM)

3. **`@retry` Decorator Optimierung:**
   - `stop_after_attempt(2)` -> `stop_after_attempt(1)`
   - `wait_exponential(min=2, max=10)` -> `wait_exponential(min=1, max=3)`
   - `retry_if_exception_type(Exception)` -> `retry_if_not_exception_type((RateLimitError, APITimeoutError))`

4. **Linearer Fallback-Loop in `_complete()` (statt Rekursion):**
   - `models = [self._model, self._fallback_model]`
   - `for i, m in enumerate(models[start:], start=start):`
   - Spezialbehandlung: `if m == 'nvidia_fallback' and self._nvidia_client:`
   - Bei Fehler: naechstes Modell versuchen (kein rekursiver Aufruf)
   - `kwargs_base['response_format']` statt `kwargs['response_format']`

---

#### `config/settings.py`

- `AI_MODEL_FALLBACK` Default von `mistralai/mistral-7b-instruct:free` auf `nvidia_fallback` geaendert
- Neue Umgebungsvariablen:
  - `NVIDIA_API_KEY` (aus `.env`, nicht in Git)
  - `NVIDIA_BASE_URL` (Default: `https://integrate.api.nvidia.com/v1`)
  - `NVIDIA_MODEL` (Default: `moonshotai/kimi-k2.5`)

---

#### `.env.example`

Aktualisiert mit allen neuen Variablen (ohne echte Keys). Echte Keys bleiben nur auf dem Server in der `.env` Datei.

---

#### `src/services/memory_service.py` (Neu)

Neuer Dienst fuer Gespraechsgedaechtnis des Bots.

---

### Frueheres Debugging (selbe Session)

#### Problem: Google Calendar OAuth
- `google_credentials.json` und Tokens fehlten
- Neue OAuth-App erstellt (Client-ID: `329052872805-ctuk...`)
- `google_token_taake.json` via manuellen OAuth-Flow erstellt
- Nina's Google-Account fuer spaeter vorgemerkt

#### Problem: Falsche Modellnamen
- `llama-3.3-70b:free` -> Rate Limit
- `mistral-7b-instruct:free` -> Not Found
- Behoben: `mistralai/mistral-small-3.1-24b-instruct:free` als Fallback

---

### Deployment-Hinweis

Um den aktuellen Server-Code nach GitHub zu pushen:
```bash
# Auf dem Server:
git remote set-url origin git@github.com:Schrottsocke/Projekt-Personal-Assistent.git
git push origin claude/dual-personal-assistants-0Uqna
```
Voraussetzung: SSH-Key des Servers in GitHub-Settings hinterlegen.
