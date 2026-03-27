"""
DualMind REST API – FastAPI App.
Läuft auf Port 8000, getrennt vom Telegram-Bot.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config.settings import settings
from api import dependencies
from api.routers import auth, dashboard, chat, tasks, calendar, shopping, recipes, mealplan, drive, features, status

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Services beim Start initialisieren, beim Stop aufräumen."""
    logger.info("DualMind API startet…")

    # JWT-Secret und andere kritische Settings validieren
    config_errors = settings.validate()
    jwt_errors = [e for e in config_errors if "API_SECRET_KEY" in e]
    if jwt_errors:
        for err in jwt_errors:
            logger.critical(err)
        raise SystemExit("API-Start abgebrochen: unsicheres API_SECRET_KEY. Siehe Logs.")

    await dependencies.startup()
    logger.info("DualMind API bereit auf Port %s.", settings.API_PORT)
    yield
    logger.info("DualMind API wird beendet.")


limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])

app = FastAPI(
    title="DualMind Personal Assistant API",
    version="1.0.0",
    description="REST API für TaakeBot & NinaBot. Telegram-Bot bleibt unverändert.",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS – Flutter App darf zugreifen
origins = settings.API_CORS_ORIGINS
if not origins:
    logger.warning("API_CORS_ORIGINS ist nicht gesetzt – CORS blockiert alle Origins.")
    origins = []
elif "*" in origins:
    logger.warning(
        "API_CORS_ORIGINS enthält Wildcard '*' – alle Origins erlaubt. "
        "In Produktion explizite Origins setzen!"
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(features.router)
app.include_router(status.router)


@app.get("/", tags=["Status"])
async def root():
    return {"status": "ok", "service": "DualMind API", "version": "1.0.0"}


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

    # 2. Kritische Services prüfen (AI, Memory)
    for name in ("ai", "memory", "calendar"):
        svc = dependencies._svc.get(name)
        if svc is None:
            checks[name] = "not_initialized"
            overall_healthy = False
        else:
            checks[name] = "ok"

    status_str = "healthy" if overall_healthy else "unhealthy"
    status_code = 200 if overall_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": status_str, "services": checks},
    )
