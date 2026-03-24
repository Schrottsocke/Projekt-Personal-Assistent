#!/bin/bash
# =============================================================================
# update.sh – Schnelles Update nach Code-Änderungen
# Ausführen als ROOT auf dem Server: bash deploy/update.sh
# =============================================================================

PROJ_DIR="/home/assistant/projekt-personal-assistent"
BRANCH="claude/dual-personal-assistants-0Uqna"

echo ">>> Code aktualisieren..."
sudo -u assistant git -C "$PROJ_DIR" pull origin "$BRANCH"

echo ">>> Dependencies aktualisieren (falls neue Pakete)..."
sudo -u assistant bash -c "
    cd $PROJ_DIR
    source venv/bin/activate
    pip install -r requirements.txt -q
"

echo ">>> Service neustarten..."
systemctl restart personal-assistant

echo ">>> Status:"
systemctl status personal-assistant --no-pager -l

echo ""
echo "Live-Logs: journalctl -u personal-assistant -f"
