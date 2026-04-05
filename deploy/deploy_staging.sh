#!/bin/bash
# =============================================================================
# deploy_staging.sh – Staging-Deployment auf dem Staging-VPS
# Ausfuehren als deploy-User auf dem Staging-Server
# =============================================================================
set -euo pipefail

PROJ_DIR="${STAGING_PROJECT_DIR:-/home/assistant/projekt-personal-assistent}"
BRANCH="staging"
COMPOSE_FILE="docker-compose.staging.yml"

echo "=== Staging Deployment gestartet: $(date -Iseconds) ==="

# --- 1. Code aktualisieren ---
echo ">>> Code aktualisieren (Branch: $BRANCH)..."
cd "$PROJ_DIR"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"

# --- 2. Docker Compose: Pull + Rebuild ---
echo ">>> Docker-Images aktualisieren..."
if [ -f "$PROJ_DIR/$COMPOSE_FILE" ]; then
    docker compose -f "$COMPOSE_FILE" pull 2>/dev/null || true
    docker compose -f "$COMPOSE_FILE" build --no-cache
    echo ">>> Container neustarten..."
    docker compose -f "$COMPOSE_FILE" down --remove-orphans
    docker compose -f "$COMPOSE_FILE" up -d
else
    echo ">>> Kein Docker-Compose, Fallback auf systemd..."
    # Fallback: venv-basiertes Deployment
    source "$PROJ_DIR/venv/bin/activate"
    pip install -r requirements.txt -q

    # Alembic Migrations (falls vorhanden)
    if [ -f "$PROJ_DIR/alembic.ini" ]; then
        echo ">>> Alembic Migrations..."
        alembic upgrade head || echo "WARN: Alembic migration fehlgeschlagen"
    fi

    systemctl restart personal-assistant-staging 2>/dev/null || true
    systemctl restart personal-assistant-api-staging 2>/dev/null || true
fi

# --- 3. Alembic Migrations (Docker) ---
if [ -f "$PROJ_DIR/$COMPOSE_FILE" ] && [ -f "$PROJ_DIR/alembic.ini" ]; then
    echo ">>> Alembic Migrations im Container..."
    docker compose -f "$COMPOSE_FILE" exec -T api alembic upgrade head || echo "WARN: Alembic migration fehlgeschlagen"
fi

# --- 4. robots.txt fuer Staging (Suchmaschinen blockieren) ---
if [ -f "$PROJ_DIR/deploy/robots_staging.txt" ]; then
    cp "$PROJ_DIR/deploy/robots_staging.txt" "$PROJ_DIR/api/static/robots.txt" 2>/dev/null || true
fi

echo "=== Staging Deployment abgeschlossen: $(date -Iseconds) ==="
