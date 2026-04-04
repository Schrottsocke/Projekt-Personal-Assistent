# Paritaets-Audit: Flutter-App vs. Web-App

**Datum:** 2026-04-04
**Scope:** Funktionale Paritaet, UX-Unterschiede, fehlende Integrationen

## Kontext

Das DualMind-Projekt hat ein FastAPI-Backend mit 100+ Endpoints und 28 Routern.
Zwei Frontends konsumieren es:
- **Flutter-App** (`app/`): 8 Screens, Riverpod, Offline-Support
- **Web-App** (`api/static/`): 23+ Views, Vanilla JS (IIFE), PWA mit Service Worker

Die Web-App ist der Flutter-App funktional weit voraus.

---

## 1. Vergleichsmatrix

| Feature-Bereich | Flutter | Web | Bemerkung |
|---|---|---|---|
| **Login/Auth** | vollstaendig | vollstaendig | Beide: JWT + Auto-Refresh, User-Auswahl |
| **Dashboard** | vollstaendig | vollstaendig | Web hat mehr Widgets (Wetter, Schichten, Dateien, Wochenvorschau) |
| **Tasks** | vollstaendig | vollstaendig | Web zusaetzlich: Recurring Tasks, Status-Workflow (open/in_progress/done), Inline-Edit |
| **Shopping** | vollstaendig | vollstaendig | Web zusaetzlich: Smart Parsing ("2x Milch"), Swipe-to-Delete mit Undo, Inline-Edit |
| **Rezepte** | vollstaendig | vollstaendig | Web zusaetzlich: Quick-Filter-Chips, Session-State-Cache |
| **Kalender** | vollstaendig | vollstaendig | Vergleichbar, Web zeigt Connection-Status |
| **Chat** | teilweise | vollstaendig | Flutter fehlt: Streaming (SSE), Voice-Input, Quick-Action-Chips, Suggestions |
| **Profil/Settings** | vollstaendig | vollstaendig | Web zusaetzlich: Theme-Toggle (Dark/Light), Danger Zone |
| **Wochenplan (Meal Plan)** | nur Model | vollstaendig | Flutter: Model `MealPlanEntry` existiert, kein Screen |
| **Drive/Dateien** | nur Config | vollstaendig | Flutter: Endpoints in ApiConfig, kein Screen |
| **Schichten (Shifts)** | nicht vorhanden | vollstaendig | Web: Schichttypen-CRUD, Monatskalender |
| **Benachrichtigungen** | nicht vorhanden | vollstaendig | Web: Typ/Status-Filter, Quick Actions, Unread-Badge |
| **Fokus-Modus** | nicht vorhanden | vollstaendig | Web: Reduzierte Tagesansicht (max 5 Items) |
| **Vorlagen (Templates)** | nicht vorhanden | vollstaendig | Web: CRUD fuer Shopping/Task/Checklist/Routine/Mealplan/Message |
| **Dokumente (Scanner)** | nicht vorhanden | vollstaendig | Web: Kamera/Datei-Upload, Multi-Upload, OCR |
| **Kontakte** | nicht vorhanden | vollstaendig | Web: Liste, Suche, Detail, CRUD |
| **Follow-ups** | nicht vorhanden | vollstaendig | Web: Status-Filter, Faelligkeitsanzeige |
| **Wetter** | nicht vorhanden | vollstaendig | Web: Standortsuche, Aktuell + Vorhersage |
| **Mobilitaet** | nicht vorhanden | vollstaendig | Web: Tagesfluss-Timeline, Fahrzeit-Rechner |
| **Automation** | nicht vorhanden | vollstaendig | Web: If-Then-Regeln, Trigger/Actions, Test-Modus |
| **Inbox** | nicht vorhanden | vollstaendig | Web: Proposals, Approvals, Snooze |
| **Gedaechtnis (Memory)** | nicht vorhanden | vollstaendig | Web: Semantische Suche, Pagination, Loeschen |
| **GitHub Issues** | nicht vorhanden | vollstaendig | Web: Liste, Erstellen, Labels |
| **Globale Suche** | nicht vorhanden | vollstaendig | Web: Command Palette (Ctrl+K), Fuzzy-Match |
| **Quick Capture** | nicht vorhanden | vollstaendig | Web: FAB + Auto-Klassifikation |
| **Theme Toggle** | nicht vorhanden | vollstaendig | Web: Dark/Light umschaltbar |

---

## 2. Zusammenfassung der Luecken

### Kategorie A: Feature komplett fehlend in Flutter (15 Bereiche)
Shifts, Notifications, Focus, Templates, Documents, Contacts, Follow-ups, Weather, Mobility, Automation, Inbox, Memory, GitHub Issues, Global Search, Quick Capture

### Kategorie B: Feature teilweise vorhanden (3 Bereiche)
- **Meal Plan**: Model `MealPlanEntry` + Endpoints vorhanden, Screen fehlt
- **Drive**: Endpoints in `ApiConfig` definiert, Screen fehlt
- **Chat**: Basis-Chat vorhanden, Streaming/Voice/Suggestions fehlen

### Kategorie C: UX-Unterschiede bei vorhandenen Features (4 Bereiche)
- **Tasks**: Kein Recurring, kein `in_progress`-Status, kein Inline-Edit
- **Shopping**: Kein Smart Parsing, kein Swipe-Undo, kein Inline-Edit
- **Dashboard**: Weniger Widget-Typen (kein Wetter, keine Schichten, keine Dateien)
- **Profile**: Kein Theme-Toggle

---

## 3. Priorisierte Gap-Liste

| # | Luecke | Nutzwert | Aufwand | API ready? |
|---|---|---|---|---|
| 1 | Chat Streaming + Voice + Suggestions | hoch | M | ja |
| 2 | Meal Plan Screen | hoch | S | ja |
| 3 | Notifications View | hoch | S-M | ja |
| 4 | Wetter View | mittel | S | ja |
| 5 | Drive Screen | mittel | S | ja |
| 6 | Schichten (Shifts) | mittel | M | ja |
| 7 | Kontakte | mittel | S-M | ja |
| 8 | Follow-ups | mittel | S | ja |
| 9 | Dokumente (Scanner) | mittel | L | ja |
| 10 | Templates | niedrig-mittel | M | ja |
| 11 | Automation | niedrig-mittel | M-L | ja |
| 12 | Inbox | niedrig-mittel | S-M | ja |
| 13 | Memory | niedrig | S | ja |
| 14 | Mobilitaet | niedrig | S-M | ja |
| 15 | Focus-Modus | niedrig | S | ja |
| 16 | Globale Suche | mittel | M | ja |
| 17 | Quick Capture | mittel | S-M | nein (Client) |
| 18 | GitHub Issues | niedrig | S | ja |
| 19 | Theme Toggle | niedrig | S | nein (Client) |
| 20 | Task Recurring/Inline-Edit | mittel | S | ja |

---

## 4. Top-5-Empfehlungen

### 1. Chat Streaming + Voice + Suggestions (Aufwand: M)
**Warum:** Chat ist das Kern-Interface. Streaming macht Antworten gefuehlt schneller. Voice ist auf Mobil besonders wertvoll.
**API-Endpoints:** `POST /chat/message/stream` (SSE), `POST /chat/voice`, `GET /suggestions/chat`
**Dateien:** `app/lib/screens/chat_screen.dart`, `app/lib/services/chat_service.dart`, `app/lib/providers/chat_provider.dart`

### 2. Meal Plan Screen (Aufwand: S)
**Warum:** Model existiert bereits (`app/lib/models/meal_plan_entry.dart`). Endpoints in ApiConfig. Bestes Aufwand/Nutzen-Verhaeltnis.
**API-Endpoints:** `GET /meal-plan/week`, `POST /meal-plan`, `DELETE /meal-plan/{id}`, `POST /meal-plan/week/to-shopping`
**Neu:** Screen, Service, Provider

### 3. Notifications View (Aufwand: S-M)
**Warum:** Zentral fuer Assistenten-App. Unread-Badge im Nav erhoeht Engagement.
**API-Endpoints:** `GET /notifications`, `GET /notifications/count`, `PATCH /notifications/{id}`, `POST /notifications/mark-all-read`
**Neu:** Screen, Service, Provider, Model, Badge-Integration

### 4. Wetter View (Aufwand: S)
**Warum:** Einfach umzusetzen, hoher Alltagsnutzen. API liefert alles fertig.
**API-Endpoints:** `GET /weather/current`, `GET /weather/forecast`
**Neu:** Screen, Service

### 5. Drive Screen (Aufwand: S)
**Warum:** Endpoints bereits in ApiConfig definiert. File-Picker fuer Upload.
**API-Endpoints:** `GET /drive/files`, `POST /drive/upload`
**Neu:** Screen, Service

---

## 5. Codebelege

### Flutter-App (8 Screens)
- Routing: `app/lib/main.dart` (Zeilen 137-163, GoRouter)
- Screens: `app/lib/screens/` (home, login, tasks, shopping, recipes, calendar, chat, profile)
- Services: `app/lib/services/` (api, auth, task, shopping, recipe, calendar, chat, offline, sync)
- Models: `app/lib/models/` (task, shopping_item, recipe, calendar_event, chat_message, meal_plan_entry)
- Providers: `app/lib/providers/` (auth, task, shopping, recipe, calendar, chat, dashboard, features, preferences)
- NavAreas: `app/lib/main.dart` - `allNavAreas` Liste mit 7 Bereichen

### Web-App (23+ Views)
- Routing: `api/static/js/app.js` (Zeilen 12-33, 23 Router.register Aufrufe)
- Views: `api/static/js/views/` (25 JS-Dateien)
- API-Client: `api/static/js/api.js` (JWT, Auto-Refresh, Offline-Flag)
- Router: `api/static/js/router.js` (Hash-basiert, Auth-Guard)
- Offline: `api/static/js/offlineQueue.js` (Queue + Auto-Sync)
- PWA: `api/static/sw.js` (Cache v5), `api/static/manifest.json`
- NavMetadata: `api/static/js/app.js` (Zeilen 46-68, 19 pinnable Items)

### Backend-API (28 Router, 100+ Endpoints)
- Hauptdatei: `api/api_main.py`
- Auth: JWT HS256, `/auth/login`, `/auth/refresh`
- Alle Endpoints fuer beide Frontends verfuegbar
