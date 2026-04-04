"""
Status-Endpunkt – zweistufig:
- /status (public): Nur allgemeiner Health-Check (api ok, uptime, timestamp)
- /status/detail (auth): Git-Details, Service-Status und Logs
"""

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import get_current_user

router = APIRouter(tags=["Status"])

_start_time = time.time()
PROJ_DIR = Path(__file__).parent.parent.parent


def _git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(PROJ_DIR),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _service_active(name: str) -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def _last_log_lines(service: str, n: int = 5) -> list[str]:
    try:
        result = subprocess.run(
            ["journalctl", "-u", service, "-n", str(n), "--no-pager", "-o", "short"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip().splitlines() if result.returncode == 0 else []
    except Exception:
        return []


def _uptime_str() -> str:
    uptime_seconds = int(time.time() - _start_time)
    h, rem = divmod(uptime_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s"


@router.get("/status")
async def status():
    """
    Oeffentlicher Health-Check: API-Status, Uptime, Timestamp.
    Keine sensiblen Daten – sicher ohne Auth.
    """
    return {
        "api": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": _uptime_str(),
    }


@router.get("/status/health")
async def status_health():
    """
    Oeffentlicher Health-Check mit Service-Status.
    Prueft Datenbank und alle registrierten Services mit Antwortzeiten.
    """
    from api import dependencies
    from api.main import _COMMIT_HASH, _STARTUP_TIME

    services = {}
    overall_healthy = True

    # 1. Datenbank-Check
    try:
        import sqlalchemy
        from src.services.database import _engine

        t0 = time.monotonic()
        if _engine is None:
            services["database"] = {"status": "down", "error": "not_initialized"}
            overall_healthy = False
        else:
            with _engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            elapsed = round((time.monotonic() - t0) * 1000, 1)
            services["database"] = {"status": "healthy", "response_ms": elapsed}
    except Exception as exc:
        elapsed = round((time.monotonic() - t0) * 1000, 1)
        services["database"] = {"status": "down", "error": str(exc), "response_ms": elapsed}
        overall_healthy = False

    # 2. Alle registrierten Services pruefen
    critical_services = {"ai"}
    for name, svc in sorted(dependencies._svc.items()):
        if name == "bot_shim":
            continue
        t0 = time.monotonic()
        if hasattr(svc, "initialized") and not svc.initialized:
            elapsed = round((time.monotonic() - t0) * 1000, 1)
            services[name] = {"status": "down", "error": "init_failed", "response_ms": elapsed}
            if name in critical_services:
                overall_healthy = False
        else:
            elapsed = round((time.monotonic() - t0) * 1000, 1)
            services[name] = {"status": "healthy", "response_ms": elapsed}

    # Kritische Services die gar nicht registriert sind
    for name in critical_services:
        if name not in services:
            services[name] = {"status": "down", "error": "not_registered"}
            overall_healthy = False

    overall = "healthy" if overall_healthy else "unhealthy"
    return {
        "services": services,
        "overall": overall,
        "uptime": _uptime_str(),
        "commit": _COMMIT_HASH,
        "deployed_at": _STARTUP_TIME,
    }


@router.get("/status/detail")
async def status_detail(
    _user: Annotated[str, Depends(get_current_user)],
):
    """
    Detaillierter Status: Git-Commit, Branch, Services, Logs.
    Erfordert Auth – nur fuer authentifizierte Nutzer und Monitoring.
    """
    bot_active = _service_active("personal-assistant")
    api_active = _service_active("personal-assistant-api")
    webhook_active = _service_active("personal-assistant-webhook")

    return {
        "api": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": _uptime_str(),
        "git": {
            "commit": _git(["rev-parse", "--short", "HEAD"]),
            "commit_full": _git(["rev-parse", "HEAD"]),
            "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
            "last_commit_msg": _git(["log", "-1", "--pretty=%s"]),
            "last_commit_author": _git(["log", "-1", "--pretty=%an"]),
            "last_commit_date": _git(["log", "-1", "--pretty=%ci"]),
            "remote_url": _git(["remote", "get-url", "origin"]),
            "local_changes": _git(["status", "--short"]) or "none",
        },
        "services": {
            "personal-assistant": {
                "active": bot_active,
                "last_logs": _last_log_lines("personal-assistant"),
            },
            "personal-assistant-api": {
                "active": api_active,
                "last_logs": _last_log_lines("personal-assistant-api"),
            },
            "personal-assistant-webhook": {
                "active": webhook_active,
                "last_logs": _last_log_lines("personal-assistant-webhook"),
            },
        },
    }
