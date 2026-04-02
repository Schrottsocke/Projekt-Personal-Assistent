# AGENTS.md — Projektkontext für Claude Code

Diese Datei wird von Claude Code beim Start automatisch gelesen.
Sie definiert die Umsetzungsreihenfolge der offenen UX-Issues sowie technische Leitplanken, die für alle Sessions gelten.

---

## UX-Roadmap — Reihenfolge einhalten

Die Reihenfolge ist durch technische Abhängigkeiten vorgegeben.
Issue #439 legt das Preferences-Datenmodell an, das alle nachfolgenden Issues nutzen.

1. **#439** `feat(profile)` — Profil / Preferences-Layer  
   _Zuerst umsetzen. Alle anderen Issues nutzen dasselbe serverseitige Preferences-Modell._

2. **#435** `feat(app)` — Konfigurierbare Navigation  
   _Baut direkt auf dem Preferences-Modell aus #439 auf._

3. **#434** `feat(app)` — Konfigurierbares Dashboard  
   _Nutzt Preferences und die neue Navigation._

4. **#436** `feat(app)` — Tasks & Kalender  
   _Eigenständige Screens, keine harten Voraussetzungen aus den oberen Issues._

5. **#437** `feat(chat)` — Chat (P1-high)  
   _Keine strukturellen Voraussetzungen, aber hohe Priorität._

6. **#438** `feat(meal-plan)` — Meal Plan  
   _Schließt den Flow Rezepte → Wochenplan → Einkauf ab._

---

## Technische Leitplanken

### Allgemein
- **Preferences-Modell**: Das in #439 definierte serverseitige Preferences-Modell wiederverwenden — nicht neu erfinden
- **Riverpod**: Bestehende Provider-Struktur beibehalten, keine Migration auf andere State-Management-Lösungen
- **Plattformkompatibilität**: Alle Screens müssen auf WebApp, iOS und Android funktionieren — kein Web-Only-Code
- **API-Erweiterungen**: Erlaubt, wenn sauber und wiederverwendbar modelliert

### Preferences
- Serverseitig speichern als Primärspeicher
- Lokal cachen als Fallback — nicht als Primärquelle
- Dasselbe Modell für Dashboard-Widgets, Navigation-Tabs und Profil-Settings verwenden

### UI-Qualität (Pflicht bei jedem Screen)
- **Skeleton Loader** während Daten laden
- **Empty State** mit beschreibendem Text und primärer Aktion
- **Error State** mit Retry-Möglichkeit
- **Offline-Indikator** bei fehlender API-Verbindung

---

## Arbeitsweise

- Pro Session **ein Issue** vollständig abarbeiten
- Akzeptanzkriterien im Issue als Checkliste verwenden und abhaken
- Keine übergreifenden Refactorings ohne Rückfrage beim Nutzer
- Wenn ein Issue Backend-Erweiterungen erfordert, diese im selben Branch umsetzen
- Kein Feature als "fertig" markieren, solange Skeleton/Empty/Error States fehlen

---

## Projektstruktur (Kurzreferenz)

```
/app          → Flutter WebApp (Screens, Widgets, Provider, Services, Models)
/api          → FastAPI Backend (Router, Services, Models)
/bot          → Telegram Bot
/config       → Konfigurationsdateien
/docs         → Dokumentation
```

### Relevante API-Endpunkte für die UX-Roadmap

| Bereich | Endpunkte |
|---|---|
| Dashboard | `GET /dashboard/today` |
| Tasks | `GET/POST/PATCH/DELETE /tasks` |
| Kalender | `GET /calendar/today`, `GET /calendar/week`, `POST /calendar/events` |
| Shopping | `GET/POST/DELETE /shopping/items` |
| Rezepte | `GET /recipes/search`, `GET /recipes/saved` |
| Meal Plan | `GET /meal-plan/week`, `POST /meal-plan/entries` |
| Chat | `POST /chat/message` |
| Preferences | Ggf. neu anlegen als Teil von #439 |
