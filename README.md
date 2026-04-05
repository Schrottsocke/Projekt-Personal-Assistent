# DualMind – Persönlicher Haushaltsassistent

**DualMind** ist eine Progressive Web App (PWA) für die vollständige digitale Verwaltung eines Haushalts. Finanzen, Dokumente, Inventar, Familie, Aufgaben und mehr – in einer modernen, DSGVO-konformen Anwendung.

> 🚧 Aktuell in der **Beta-Phase** – erster Testerkreis läuft.

---

## Funktionsbereiche

| Bereich | Features |
|---|---|
| **Dashboard** | Tagesübersicht: Finanzen, offene Aufgaben, Benachrichtigungen, Kalender |
| **Finanzen** | Transaktionen, Budgets, Verträge, Rechnungen, Kategorien, Statistiken |
| **Dokumente** | Kamera-Scan, OCR-Texterkennung, Kategorisierung, Volltextsuche |
| **Inventar** | Gegenstände mit Foto, Raumzuordnung, Garantie-Tracking, Suche |
| **Familie** | Haushaltsmitglieder, Rollen, Aufgaben mit Zuweisung, Einkaufsliste, Routinen |
| **Kalender** | Termine, Deadlines, Scheduler-Jobs, Erinnerungen |
| **Benachrichtigungen** | Push (PWA), Telegram, Deadline-Alerts, VAPID-Keys |
| **Suche** | Globale Volltextsuche über alle Bereiche |
| **DSGVO** | Datenexport, Datenlöschung, Datenschutz-Center |
| **Onboarding** | 6-schrittiger geführter Einstieg für neue Nutzer |
| **Beta-Feedback** | Bug-Reports, UX-Bewertung (1–5), Triage-Status im Admin |
| **Admin** | Testuser-Einladungen, Invite-Links, Resend, Widerruf |

---

## Technologie-Stack

### Backend
- **FastAPI** (Python 3.11) – 35 Router, vollständige Pydantic v2 Schemas
- **SQLAlchemy** + **Alembic** – Datenbankmigrationen
- **APScheduler** – Deadline-Alerts, Scheduler-Jobs
- **Tesseract OCR** + Vision-Fallback – Dokumentenscanning
- **Jinja2** – E-Mail-Templates (HTML + Plaintext)
- **JWT-Auth** – Access + Refresh Token

### Frontend / PWA
- Progressive Web App – installierbar auf iOS & Android
- Service Worker, Offline-Fallback, Web Manifest
- Kamera-Zugriff (`getUserMedia`) für Dokumentenscans
- Web Push Notifications (VAPID)

### Infrastruktur
- **Docker** + **Docker Compose** (local & staging)
- **GitHub Actions** – CI/CD Pipeline (Lint → Test → Build → Deploy)
- **Hostinger VPS** (Ubuntu 22.04)
- **Let's Encrypt** – HTTPS auf Staging & Produktion
- **Mailpit** (lokal) / **Resend** oder **Brevo** (Produktion) – E-Mail

---

## Lokale Entwicklung

```bash
git clone https://github.com/Schrottsocke/Projekt-Personal-Assistent.git
cd Projekt-Personal-Assistent

# Backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env mit eigenen Werten befüllen

# Datenbank initialisieren
alembic upgrade head

# Optionale Demo-Daten
python scripts/seed_demo_household.py

# Starten
uvicorn api.main:app --reload --port 8000
```

API-Dokumentation (Swagger UI): `http://localhost:8000/docs`

### Lokales E-Mail-Testing (Mailpit)

```bash
docker compose up mailpit -d
# Mails abfangen unter: http://localhost:8025
```

---

## Staging-Deployment

```bash
# Push auf staging-Branch → CI/CD deployt automatisch
git push origin main:staging

# Oder manuell:
docker compose -f docker-compose.staging.yml up -d
docker compose -f docker-compose.staging.yml exec app alembic upgrade head
```

### Benötigte GitHub Secrets

| Secret | Beschreibung |
|---|---|
| `STAGING_SSH_KEY` | SSH Private Key für Staging-VPS |
| `STAGING_HOST` | Staging-Server IP/Hostname |
| `STAGING_USER` | SSH-User auf dem Staging-Server |
| `STAGING_HEALTH_URL` | Health-Check URL |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | E-Mail-Konfiguration |

---

## Umgebungsvariablen

Alle Variablen sind in `.env.example` vollständig dokumentiert. Wichtigste Einträge:

```env
# Datenbank
DATABASE_URL=sqlite:///data/dualmind.db

# Auth
SECRET_KEY=                    # python -c "import secrets; print(secrets.token_hex(32))"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# E-Mail (SMTP)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@dualmind.app
SMTP_PASSWORD=

# Push Notifications (VAPID)
VAPID_PRIVATE_KEY=
VAPID_PUBLIC_KEY=
VAPID_SUBJECT=mailto:admin@dualmind.app

# OCR
TESSERACT_CMD=tesseract
```

---

## Tests & Coverage

```bash
pip install -r requirements-dev.txt

# Alle Tests
pytest tests/ -v

# Mit Coverage-Report
pytest tests/ --cov=app --cov=api --cov-report=term-missing --cov-report=html

# Nur Integrationstests
pytest tests/integration/ -v
```

Ziel: ≥ 80 % Coverage für alle Module, ≥ 90 % für OCR, Finance, Scheduler.

---

## Architektur

```
api/
├── main.py                  FastAPI App, Router-Registrierung, CORS, Lifespan
├── dependencies.py          get_current_user, get_db, Service-Singletons
├── routers/                 35 Router (finance, inventory, family, documents, ...)
├── schemas/                 Pydantic v2 Request/Response-Modelle
├── auth/                    JWT-Auth, Login, Refresh
└── templates/email/         Jinja2 E-Mail-Templates (DE, HTML + Plaintext)

app/
├── models/                  SQLAlchemy ORM-Modelle
├── services/                Business-Logik (OCR, Finance, Email, Notifications, ...)
└── scheduler/               APScheduler Jobs (Deadline-Alerts, Cleanup)

src/                         Shared Utilities, Settings, DB-Session
alembic/                     Datenbank-Migrationen
tests/
├── unit/                    Unit-Tests pro Service
└── integration/             End-to-End API-Tests
scripts/
└── seed_demo_household.py   Demo-Haushalt für Tester
docs/
└── beta/                    Beta-Testplan, PWA-Produktionscheck-Protokoll
```

---

## API-Überblick

Die vollständige OpenAPI-Dokumentation ist unter `/docs` verfügbar. Kernbereiche:

| Prefix | Router | Beschreibung |
|---|---|---|
| `/auth` | auth.py | Login, Refresh, Passwort-Reset |
| `/api/finance` | finance_router.py | Transaktionen, Budgets, Verträge, Rechnungen |
| `/api/inventory` | inventory_router.py | Gegenstände, Räume, Garantien, Fotos |
| `/api/family` | family_router.py | Haushalt, Mitglieder, Aufgaben, Routinen |
| `/api/documents` | documents.py | Upload, OCR, Kategorien, Suche |
| `/api/notifications` | notifications_router.py | Push-Subscriptions, VAPID, Alerts |
| `/api/gdpr` | gdpr_router.py | Export, Löschung, Datenschutz-Center |
| `/api/onboarding` | onboarding_router.py | Onboarding-Steps, Fortschritt |
| `/api/feedback` | feedback_router.py | Bug-Reports, UX-Bewertungen, Triage |
| `/api/test-users` | test_users.py | Invite-Links, Einladungsverwaltung |
| `/api/monitoring` | monitoring_router.py | Beta-KPIs, Invite-Funnel, Error-Events |
| `/api/dashboard` | dashboard.py | Tagesübersicht, Aggregations |
| `/api/search` | search.py | Globale Volltextsuche |
| `/api/calendar` | calendar.py | Termine, Deadlines |
| `/status` | status.py | Health-Check, System-Status |

---

## Bekannte Einschränkungen (Beta)

- Push Notifications auf iOS nur aus installierter PWA (Homescreen-Install erforderlich)
- Kamera-Zugriff erfordert HTTPS (lokal via `localhost` funktioniert)
- OCR-Qualität abhängig von Bildqualität und Tesseract-Installation

---

## Mitmachen / Beta testen

Beta-Zugang nur auf Einladung. Interesse? Kontakt über GitHub Issues oder direkt per E-Mail an die im Profil hinterlegte Adresse.

Bug-Reports bitte als GitHub Issue mit dem Label `bug` oder direkt über den In-App-Feedback-Button.
