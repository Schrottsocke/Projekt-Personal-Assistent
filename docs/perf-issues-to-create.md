# Performance-Issues zum Anlegen auf GitHub

Diese Issues wurden im Chat-Bot Performance-Audit identifiziert.
Bitte auf GitHub anlegen (manuell oder via `/new-issue` in naechster Session mit MCP-Zugriff).

---

## Issue 1: Intent-Detection-LLM-Call fuer einfache Chat-Nachrichten eliminieren

**Labels:** `P1-high`, `performance`, `backend`

**Beschreibung:**

### Problem
Jede Chat-Nachricht loest einen separaten LLM-Call zur Intent-Klassifikation aus (`ai_service.py:_detect_intent()`, Zeile 266-412), bevor der eigentliche Chat-Response generiert wird. Das bedeutet **zwei serielle LLM-Calls pro Nachricht** — der groesste einzelne Latenz-Faktor.

### Beobachtung
- Intent-Detection dauert typisch 3-30s (Free-Tier OpenRouter)
- Auch offensichtliche Chat-Nachrichten ("Hallo", "Wie geht's?", "Danke") durchlaufen den vollen LLM-Classifier mit 25+ Intent-Definitionen
- Die Mehrheit der Nachrichten in einer Chat-Session sind normaler Chat, kein strukturierter Intent

### Vermutete Ursache
Kein Pre-Filter — alle Nachrichten werden identisch behandelt, unabhaengig von ihrer Komplexitaet.

### Optimierungsidee
1. **Keyword/Regex-basierter Vor-Filter** fuer offensichtliche Chat-Nachrichten (Greetings, kurze Fragen, Smalltalk)
2. Nur bei Verdacht auf strukturierte Intents (Kalender-Keywords, Aufgaben-Keywords, etc.) den LLM-Classifier aufrufen
3. Alternativ: leichtgewichtiges lokales Modell oder Embedding-basierte Klassifikation

### Betroffene Dateien
- `src/services/ai_service.py` (Zeilen 217-264, 266-412)

### Akzeptanzkriterien
- [ ] Einfache Chat-Nachrichten ueberspringen Intent-Detection-LLM-Call
- [ ] Strukturierte Intents (Kalender, Tasks, etc.) werden weiterhin korrekt erkannt
- [ ] Chat-Latenz fuer Standardnachrichten halbiert sich messbar (sichtbar in `perf | phase=intent_detection` Logs)
- [ ] Keine Regression bei Intent-Erkennung

---

## Issue 2: Schnelleres Modell oder bezahlten Tier evaluieren

**Labels:** `P1-high`, `performance`, `backend`

**Beschreibung:**

### Problem
Das primaere Modell `meta-llama/llama-3.3-70b-instruct:free` auf OpenRouter hat unvorhersagbare Latenz (3-30s+), da der kostenlose Tier stark gedrosselt ist und niedrige Prioritaet hat.

### Beobachtung
- Free-Tier-Latenz schwankt stark je nach Tageszeit und Auslastung
- Worst Case: 90s Timeout + 3 Retries mit Backoff = potenziell minutenlange Wartezeit
- Fallback auf NVIDIA (`moonshotai/kimi-k2.5`) hat nur 20s Timeout, ist aber ebenfalls nicht zuverlaessig schnell

### Vermutete Ursache
Kostenloser Tier hat niedrige Prioritaet bei OpenRouter. Hohe Auslastung fuehrt zu Queuing.

### Optimierungsidee
1. **Bezahlten OpenRouter-Tier** testen (oft 2-5x schneller bei gleichen Modellen)
2. **Schnelleres/kleineres Modell** fuer Intent-Detection (z.B. Llama 3.1 8B oder Gemma)
3. **Groesseres/besseres Modell nur fuer Chat-Completion** (Qualitaet beibehalten)
4. Kosten-Nutzen-Analyse erstellen

### Betroffene Dateien
- `config/settings.py` (Zeile 51: `AI_MODEL`)
- `src/services/ai_service.py` (Zeilen 59-87: Client-Konfiguration)
- `.env` (Modell-Konfiguration)

### Akzeptanzkriterien
- [ ] Modell-Latenz messbar unter 5s (P95) — verifizierbar via `perf` Logs
- [ ] Antwortqualitaet bleibt akzeptabel (subjektiver Test mit 10+ typischen Nachrichten)
- [ ] Kosten pro Nachricht dokumentiert
- [ ] Konfigurierbar via `.env` (kein Hardcode)

---

## Issue 3: SSE-Streaming fuer Chat-Responses implementieren

**Labels:** `P2-medium`, `performance`, `frontend`, `backend`

**Beschreibung:**

### Problem
Der User wartet auf die komplette Antwort (bis zu 30s+) und sieht nur "Denkt nach..." — kein progressives Feedback. Die gefuehlte Latenz ist deutlich schlechter als die tatsaechliche.

### Beobachtung
- `api/routers/chat.py`: Endpoint wartet auf vollstaendige `_complete()` Response
- `api/static/js/views/chat.js`: `await Api.sendMessage()` blockiert bis Response komplett
- Kein `EventSource`, kein `ReadableStream`, kein chunked Transfer
- OpenRouter unterstuetzt `stream=True` in der Chat Completions API

### Vermutete Ursache
Architekturentscheidung — Streaming wurde nicht implementiert.

### Optimierungsidee
1. **Neuer SSE-Endpoint** `POST /chat/message/stream` mit `StreamingResponse`
2. **OpenRouter stream=True** in `_complete()` nutzen
3. **Frontend EventSource/fetch+ReadableStream** fuer inkrementelle Anzeige
4. History-Speicherung nach komplettem Stream
5. Fallback auf non-streaming Endpoint bei Fehler

### Betroffene Dateien
- `api/routers/chat.py` (neuer Streaming-Endpoint)
- `src/services/ai_service.py` (`_complete()` um Streaming erweitern)
- `src/services/intelligence.py` (`process_with_memory()` Streaming-Variante)
- `api/static/js/views/chat.js` (Streaming-Rendering)
- `api/static/js/api.js` (Streaming-Request-Methode)

### Akzeptanzkriterien
- [ ] Erstes Token erscheint nach <3s (bei funktionierendem Modell)
- [ ] Vollstaendige Antwort wird korrekt zusammengesetzt und angezeigt
- [ ] History-Speicherung erfolgt nach komplettem Stream
- [ ] Non-streaming Fallback funktioniert
- [ ] Bestehendes Chat-Verhalten nicht beeintraechtigt

---

## Issue 4: Memory-Search-Caching mit TTL implementieren

**Labels:** `P2-medium`, `performance`, `backend`

**Beschreibung:**

### Problem
Jede Chat-Nachricht loest eine neue semantische Suche ueber mem0/ChromaDB aus, inklusive eines Embedding-API-Calls via OpenRouter. Memories aendern sich aber selten innerhalb einer Session.

### Beobachtung
- `base_memory_service.py:search_memories()` (Zeile 119-132): Jeder Call geht an `asyncio.to_thread(self._memory.search, ...)`
- mem0 im lokalen Modus nutzt `text-embedding-3-small` via OpenRouter fuer Embeddings — das ist ein zusaetzlicher API-Call pro Suche
- Bei schnellen Nachrichten-Folgen werden identische oder sehr aehnliche Suchen wiederholt
- Aktuell messbar ~1-5s pro Memory-Search (sichtbar in neuen `perf` Logs)

### Vermutete Ursache
Kein Cache — jede Suche ist ein vollstaendiger API-Round-Trip.

### Optimierungsidee
1. **In-Memory TTL-Cache** (5 Minuten) fuer Memory-Search-Ergebnisse pro User
2. Cache-Key: `(user_key, query_hash)` oder einfacher `(user_key)` mit festen Top-N Ergebnissen
3. **Cache-Invalidierung** bei Memory-Writes (`add_memory`, `add_messages`)
4. Optional: Eager-Refresh im Hintergrund bei Cache-Miss

### Betroffene Dateien
- `src/memory/base_memory_service.py` (Zeilen 119-132: `search_memories()`)
- Evtl. `src/services/intelligence.py` (Cache-Nutzung)

### Akzeptanzkriterien
- [ ] Wiederholte Anfragen innerhalb von 5 Min nutzen Cache (kein API-Call)
- [ ] Cache wird bei Memory-Writes invalidiert
- [ ] Messbare Reduktion der Memory-Search-Latenz in `perf` Logs
- [ ] Keine veralteten Memories nach explizitem Memory-Write
