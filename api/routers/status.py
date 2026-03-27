"""
Status-Endpunkt – öffentlich, kein Auth nötig.
Gibt Git-Stand, Service-Status und Uptime zurück.
Ermöglicht Claude Code, den Server-Zustand remote zu prüfen.
"""

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

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


@router.get("/status")
async def status():
    """
    Server-Status: Git-Commit, Branch, Services, Uptime, letzte Logs.
    Kein Auth erforderlich – für Monitoring und Claude Code Debugging.
    """
    uptime_seconds = int(time.time() - _start_time)
    h, rem = divmod(uptime_seconds, 3600)
    m, s = divmod(rem, 60)

    bot_active = _service_active("personal-assistant")
    api_active = _service_active("personal-assistant-api")
    webhook_active = _service_active("personal-assistant-webhook")

    return {
        "api": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": f"{h}h {m}m {s}s",
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
