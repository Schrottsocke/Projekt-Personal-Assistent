"""
DualMind REST API – FastAPI App.
Läuft auf Port 8000, getrennt vom Telegram-Bot.
"""

import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

import subprocess as _sp
import datetime as _dt

from config.settings import settings
from api import dependencies
from api.routers import (
    auth,
    dashboard,
    chat,
    tasks,
    calendar,
    shopping,
    recipes,
    mealplan,
    drive,
    features,
    github,
    notifications,
    shifts,
    status,
    search,
    preferences,
    contacts,
    followups,
    weather,
    mobility,
    sync,
    suggestions,
    memories,
    templates,
    automation,
    inbox,
)

logger = structlog.get_logger(__name__)

_COMMIT_HASH = (
    _sp.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    ).stdout.strip()
    or "dev"
)
_STARTUP_TIME = _dt.datetime.utcnow().isoformat() + "Z"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Erzeugt eine Request-ID pro Anfrage und bindet sie an structlog contextvars."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
        )

        t0 = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((time.monotonic() - t0) * 1000, 1)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        logger.info(
            "request_finished",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        if duration_ms > 5000:
            logger.warning(
                "slow_request",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

        structlog.contextvars.clear_contextvars()
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Services beim Start initialisieren, beim Stop aufräumen."""
    logger.info("DualMind API startet…")

    # Frühzeitige API_SECRET_KEY-Validierung: Platzhalter und zu kurze Keys ablehnen
    _placeholder_patterns = {
        "change-me",
        "your-secret-key",
        "placeholder",
        "xxx",
        "test",
        "change-me-in-production-please",
        "change-me-generate-with-secrets-token-hex",
        "CHANGE_ME_USE_python_c_import_secrets_print_secrets_token_hex_32",
    }
    secret = settings.API_SECRET_KEY.strip()
    if not secret or secret.lower() in _placeholder_patterns or len(secret) < 32:
        reason = (
            "nicht gesetzt"
            if not secret
            else (
                "Platzhalter-Wert"
                if secret.lower() in _placeholder_patterns
                else f"zu kurz ({len(secret)} Zeichen, min. 32)"
            )
        )
        logger.critical(
            "API_SECRET_KEY ist ungueltig (%s). "
            'Generiere ein Secret: python -c "import secrets; print(secrets.token_hex(32))"',
            reason,
        )
        sys.exit(1)

    # Weitere kritische Settings validieren
    config_errors = settings.validate()
    jwt_errors = [e for e in config_errors if "API_SECRET_KEY" in e]
    if jwt_errors:
        for err in jwt_errors:
            logger.critical(err)
        raise SystemExit("API-Start abgebrochen: unsicheres API_SECRET_KEY. Siehe Logs.")

    # Sentry Observability (nur wenn DSN konfiguriert)
    if settings.SENTRY_DSN and sentry_sdk is not None:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,
        )
        logger.info("Sentry initialisiert (env=%s)", settings.SENTRY_ENVIRONMENT)

    await dependencies.startup()
    logger.info("DualMind API bereit auf Port %s.", settings.API_PORT)
    yield
    logger.info("DualMind API wird beendet.")


_LANDING_PAGE_HTML = """\
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DualMind – Dein Tag. Auf einen Blick.</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
background:#121212;color:#e0e0e0;min-height:100vh;padding:0}
.hero{min-height:80vh;display:flex;flex-direction:column;align-items:center;
justify-content:center;text-align:center;padding:40px 20px}
h1{font-size:2.8rem;font-weight:800;color:#e0e0e0;margin-bottom:12px;letter-spacing:-1px}
h1 span{color:#7c4dff}
.sub{font-size:1.15rem;color:#a0a0a0;max-width:480px;margin-bottom:36px;line-height:1.7}
.cta{display:inline-block;padding:14px 40px;background:#7c4dff;color:#fff;
text-decoration:none;border-radius:10px;font-size:1rem;font-weight:600;
transition:background .2s}
.cta:hover{background:#651fff}
.scenes{max-width:560px;margin:0 auto;padding:0 20px 60px}
.scenes h2{font-size:1.1rem;font-weight:700;color:#7c4dff;margin-bottom:24px;
text-transform:uppercase;letter-spacing:1px;text-align:center}
.scene{margin-bottom:28px;padding:20px;background:#1e1e1e;border-radius:12px;
border-left:3px solid #7c4dff}
.scene-time{font-size:.8rem;font-weight:600;color:#7c4dff;margin-bottom:6px;
text-transform:uppercase;letter-spacing:.5px}
.scene p{font-size:.95rem;color:#b0b0b0;line-height:1.6}
.cta2{text-align:center;padding:0 20px 60px}
footer{text-align:center;padding:20px;font-size:.8rem;color:#666}
footer a{color:#7c4dff;text-decoration:none}
footer a:hover{text-decoration:underline}
</style>
</head>
<body>
<div class="hero">
  <h1>Dein Tag. <span>Auf einen Blick.</span></h1>
  <p class="sub">DualMind buendelt Termine, Aufgaben, Einkauf und Kochen
  in einem persoenlichen Assistenten &ndash; damit du den Kopf frei hast.</p>
  <a href="/app" class="cta">App oeffnen &rarr;</a>
</div>

<div class="scenes">
  <h2>Ein Tag mit DualMind</h2>
  <div class="scene">
    <div class="scene-time">Morgens</div>
    <p>Du oeffnest DualMind und siehst: Fruehschicht ab 6:00, 14&deg;C mit Regen,
    2 offene Aufgaben. Ein Satz, kein Scrollen.</p>
  </div>
  <div class="scene">
    <div class="scene-time">Mittags</div>
    <p>Du fragst den Assistenten: &bdquo;Was koche ich heute Abend?&ldquo; &ndash;
    er schlaegt ein Rezept vor und setzt die Zutaten auf die Einkaufsliste.</p>
  </div>
  <div class="scene">
    <div class="scene-time">Abends</div>
    <p>Du hakst den Einkauf ab, checkst morgen kurz ab und legst das Handy weg. Fertig.</p>
  </div>
</div>

<div class="cta2">
  <a href="/app" class="cta">App oeffnen &rarr;</a>
</div>

<footer><a href="/docs">API-Dokumentation</a></footer>
</body>
</html>
"""

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])

app = FastAPI(
    title="DualMind Personal Assistant API",
    version="1.0.0",
    description="REST API für TaakeBot & NinaBot. Telegram-Bot bleibt unverändert.",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Fängt unbehandelte Exceptions ab – keine Stack-Traces an Clients."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.error(
        "unhandled_exception",
        exc_type=type(exc).__name__,
        exc_msg=str(exc),
        path=request.url.path,
        method=request.method,
        request_id=request_id,
        exc_info=exc,
    )
    if sentry_sdk is not None:
        try:
            sentry_sdk.capture_exception(exc)
        except Exception:
            pass
    return JSONResponse(
        status_code=500,
        content={"detail": "Interner Serverfehler", "request_id": request_id},
    )


# CORS – Flutter App darf zugreifen
origins = settings.API_CORS_ORIGINS
if not origins:
    logger.warning("API_CORS_ORIGINS ist nicht gesetzt – CORS blockiert alle Origins.")
    origins = []
elif "*" in origins:
    logger.warning(
        "API_CORS_ORIGINS enthält Wildcard '*' – alle Origins erlaubt. In Produktion explizite Origins setzen!"
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Request-ID-Tracking
app.add_middleware(RequestIDMiddleware)

# Router einbinden
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
app.include_router(calendar.router, prefix="/calendar", tags=["Kalender"])
app.include_router(shopping.router, prefix="/shopping", tags=["Einkauf"])
app.include_router(recipes.router, prefix="/recipes", tags=["Rezepte"])
app.include_router(mealplan.router, prefix="/meal-plan", tags=["Wochenplan"])
app.include_router(drive.router, prefix="/drive", tags=["Drive"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
app.include_router(shifts.router, prefix="/shifts", tags=["Dienstplan"])
app.include_router(features.router)
app.include_router(github.router, prefix="/github", tags=["GitHub"])
app.include_router(search.router, prefix="/search", tags=["Suche"])
app.include_router(preferences.router, prefix="/preferences", tags=["Preferences"])
app.include_router(contacts.router, prefix="/contacts", tags=["Kontakte"])
app.include_router(followups.router, prefix="/followups", tags=["Follow-ups"])
app.include_router(weather.router, prefix="/weather", tags=["Wetter"])
app.include_router(mobility.router, prefix="/mobility", tags=["Mobilität"])
app.include_router(sync.router, prefix="/sync", tags=["Sync"])
app.include_router(suggestions.router, prefix="/suggestions", tags=["Suggestions"])
app.include_router(memories.router, prefix="/memories", tags=["Memories"])
app.include_router(templates.router, prefix="/templates", tags=["Vorlagen"])
app.include_router(automation.router, prefix="/automation", tags=["Automation"])
app.include_router(inbox.router, prefix="/inbox", tags=["Inbox"])
app.include_router(status.router)


# Static files (CSS, JS for web app)
_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def homepage():
    """Oeffentliche Landing Page."""
    return HTMLResponse(_LANDING_PAGE_HTML, headers={"Cache-Control": "no-cache, must-revalidate"})


@app.get("/app/sw.js", include_in_schema=False)
async def service_worker():
    """ServiceWorker mit erweitertem Scope-Header ausliefern."""
    sw_path = Path(__file__).parent / "static" / "sw.js"
    return FileResponse(str(sw_path), media_type="application/javascript", headers={"Service-Worker-Allowed": "/app"})


@app.get("/app", include_in_schema=False)
async def web_app_root():
    """SPA-Shell fuer die Web-App."""
    html = (_static_dir / "app.html").read_text()
    html = html.replace("__CACHE_VERSION__", _COMMIT_HASH)
    return HTMLResponse(html, headers={"Cache-Control": "no-cache, must-revalidate"})


@app.get("/app/{path:path}", include_in_schema=False)
async def web_app_catchall(path: str):
    """SPA Catch-All fuer Deep-Links."""
    html = (_static_dir / "app.html").read_text()
    html = html.replace("__CACHE_VERSION__", _COMMIT_HASH)
    return HTMLResponse(html, headers={"Cache-Control": "no-cache, must-revalidate"})


@app.get("/health", tags=["Status"])
async def health():
    """Echter Health-Check: prüft DB-Verbindung und kritische Services."""
    import sqlalchemy
    from src.services.database import _engine

    checks = {}
    overall_healthy = True

    # 1. Datenbank-Check
    try:
        if _engine is None:
            checks["database"] = "not_initialized"
            overall_healthy = False
        else:
            with _engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        overall_healthy = False

    # 2. Sentry-Check
    if settings.SENTRY_DSN:
        checks["sentry"] = "configured"
    else:
        checks["sentry"] = "disabled"

    # 3. Kritische Services prüfen (AI muss laufen, Memory/Calendar optional)
    for name in ("ai",):
        svc = dependencies._svc.get(name)
        if svc is None:
            checks[name] = "not_initialized"
            overall_healthy = False
        elif hasattr(svc, "initialized") and not svc.initialized:
            checks[name] = "init_failed"
            overall_healthy = False
        else:
            checks[name] = "ok"

    for name in ("memory", "calendar"):
        svc = dependencies._svc.get(name)
        if svc is None:
            checks[name] = "not_initialized"
        elif hasattr(svc, "initialized") and not svc.initialized:
            checks[name] = "init_failed"
        else:
            checks[name] = "ok"

    status_str = "healthy" if overall_healthy else "unhealthy"
    status_code = 200 if overall_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": status_str, "commit": _COMMIT_HASH, "deployed_at": _STARTUP_TIME, "services": checks},
    )
