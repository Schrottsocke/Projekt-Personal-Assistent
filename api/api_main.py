"""
Standalone-Startpunkt für die FastAPI REST API.
Separat vom Telegram-Bot (main.py).

Verwendung:
    python api/api_main.py
    # oder:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
import sys
from pathlib import Path

# Projekt-Root zum Suchpfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )
