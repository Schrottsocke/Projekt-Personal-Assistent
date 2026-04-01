#!/usr/bin/env python3
"""
GitHub Webhook Deployer
=======================
Lauscht auf Port 9000 auf GitHub Push-Webhooks.
Bei einem Push auf den konfigurierten Branch:
  1. git pull --rebase origin <branch>
  2. pip install -r requirements.txt
  3. systemctl restart personal-assistant personal-assistant-api

Einrichtung:
  1. WEBHOOK_SECRET in /home/assistant/projekt-personal-assistent/.env setzen
  2. GitHub → Repo → Settings → Webhooks → Add webhook:
       Payload URL: http://DEINE_IP:9000/deploy
       Content type: application/json
       Secret: <gleicher Wert wie WEBHOOK_SECRET>
       Events: Just the push event
"""

import hashlib
import hmac
import http.server
import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

# --- Konfiguration ---
PROJ_DIR = Path(__file__).parent.parent
ENV_FILE = PROJ_DIR / ".env"
PORT = int(os.getenv("WEBHOOK_PORT", "9000"))
BRANCH = os.getenv("DEPLOY_BRANCH", "main")
SERVICES = ["personal-assistant", "personal-assistant-api", "personal-assistant-webhook"]
VENV_PIP = PROJ_DIR / "venv" / "bin" / "pip"
BOT_USER = "assistant"

# Lock gegen parallele Deployments
_deploy_lock = threading.Lock()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [webhook] %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("webhook")


def _load_secret() -> str:
    """Liest WEBHOOK_SECRET aus der .env-Datei."""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith("WEBHOOK_SECRET="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.getenv("WEBHOOK_SECRET", "")


def _verify_signature(body: bytes, signature_header: str, secret: str) -> bool:
    """Verifiziert die HMAC-SHA256-Signatur von GitHub."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _run(cmd: list[str], cwd: Path = PROJ_DIR) -> tuple[int, str]:
    """Führt einen Shell-Befehl aus und gibt (returncode, output) zurück."""
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=120)
    output = (result.stdout + result.stderr).strip()
    return result.returncode, output


def deploy() -> tuple[bool, str]:
    """Führt den Deploy-Prozess aus. Gibt (success, log) zurück."""
    if not _deploy_lock.acquire(blocking=False):
        logger.warning("Deploy übersprungen – ein anderes Deployment läuft bereits.")
        return False, "Deploy skipped: another deployment is already running."

    try:
        return _deploy_inner()
    finally:
        _deploy_lock.release()


def _deploy_inner() -> tuple[bool, str]:
    """Eigentliche Deploy-Logik (wird unter Lock aufgerufen)."""
    lines = []

    # 1. Git pull
    logger.info("git pull --rebase ...")
    rc, out = _run(["sudo", "-u", BOT_USER, "git", "pull", "--rebase", "origin", BRANCH])
    lines.append(f"git pull: rc={rc}\n{out}")
    if rc != 0:
        logger.error(f"git pull fehlgeschlagen: {out}")
        return False, "\n".join(lines)
    logger.info(f"git pull OK: {out[:200]}")

    # 2. pip install
    if VENV_PIP.exists():
        logger.info("pip install -r requirements.txt ...")
        rc, out = _run(
            [
                "sudo",
                "-u",
                BOT_USER,
                str(VENV_PIP),
                "install",
                "-r",
                str(PROJ_DIR / "requirements.txt"),
                "-q",
            ]
        )
        lines.append(f"pip install: rc={rc}\n{out}")
        if rc != 0:
            logger.warning(f"pip install Warnung: {out[:200]}")

    # 3. Services neustarten
    for svc in SERVICES:
        logger.info(f"systemctl restart {svc} ...")
        rc, out = _run(["sudo", "systemctl", "restart", svc])
        lines.append(f"restart {svc}: rc={rc} {out}")
        if rc != 0:
            logger.warning(f"restart {svc} fehlgeschlagen: {out}")

    logger.info("Deploy erfolgreich abgeschlossen.")
    return True, "\n".join(lines)


class WebhookHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logger.info(fmt % args)

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            rc, commit = _run(["git", "rev-parse", "--short", "HEAD"])
            self.wfile.write(
                json.dumps(
                    {
                        "status": "ok",
                        "commit": commit.strip() if rc == 0 else "unknown",
                        "branch": BRANCH,
                        "port": PORT,
                    }
                ).encode()
            )
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/deploy":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        secret = _load_secret()
        if not secret:
            logger.error("Webhook: WEBHOOK_SECRET nicht verfügbar – Request abgelehnt.")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Server misconfigured")
            return

        sig = self.headers.get("X-Hub-Signature-256", "")
        if not _verify_signature(body, sig, secret):
            logger.warning("Webhook: ungültige Signatur – abgelehnt.")
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Invalid signature")
            return

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        # Branch prüfen
        ref = payload.get("ref", "")
        expected_ref = f"refs/heads/{BRANCH}"
        if ref != expected_ref:
            logger.info(f"Webhook: Push auf '{ref}' ignoriert (erwartet: {expected_ref})")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Branch ignored")
            return

        pusher = payload.get("pusher", {}).get("name", "unknown")
        commit_msg = payload.get("head_commit", {}).get("message", "")[:80]
        logger.info(f"Webhook: Deploy ausgelöst von '{pusher}' – {commit_msg}")

        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "deploying"}')

        # Deploy asynchron starten (Handler darf nicht blockieren)
        threading.Thread(target=deploy, daemon=True).start()


if __name__ == "__main__":
    logger.info(f"Webhook-Deployer startet auf Port {PORT} ...")
    logger.info(f"Branch: {BRANCH}")
    logger.info(f"Projekt: {PROJ_DIR}")
    secret = _load_secret()
    if not secret:
        logger.error("WEBHOOK_SECRET nicht gesetzt – Start verweigert!")
        sys.exit(1)

    logger.info("WEBHOOK_SECRET geladen – Signaturprüfung aktiv.")
    server = http.server.HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Webhook-Deployer beendet.")
