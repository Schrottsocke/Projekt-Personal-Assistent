"""
DualMind REST API – FastAPI App.
Läuft auf Port 8000, getrennt vom Telegram-Bot.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


app = FastAPI(
    title="DualMind Personal Assistant API",
    version="1.0.0",
    description="REST API für TaakeBot & NinaBot. Telegram-Bot bleibt unverändert.",
    lifespan=lifespan,
)

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
    return {"status": "healthy"}
