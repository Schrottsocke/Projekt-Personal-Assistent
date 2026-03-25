#!/bin/bash
# =============================================================================
# setup_server.sh – Einmaliges Server-Setup auf Hostinger VPS
# Ausführen als ROOT: bash setup_server.sh
# =============================================================================

set -e  # Bei Fehler abbrechen

echo "======================================================"
echo "  Personal Assistant – Server Setup"
echo "======================================================"

# --- System-Pakete ---
echo ""
echo ">>> System aktualisieren..."
apt update -qq && apt upgrade -y -qq

echo ">>> Python + Build-Tools installieren..."
apt install -y -qq \
    python3.11 python3.11-venv python3-pip \
    git build-essential cmake \
    libssl-dev libffi-dev python3-dev \
    nano curl

# --- Benutzer anlegen ---
if ! id "assistant" &>/dev/null; then
    echo ">>> Benutzer 'assistant' anlegen..."
    useradd -m -s /bin/bash assistant
    echo "Benutzer 'assistant' erstellt."
else
    echo ">>> Benutzer 'assistant' existiert bereits."
fi

# --- Projekt klonen ---
PROJ_DIR="/home/assistant/projekt-personal-assistent"
if [ ! -d "$PROJ_DIR" ]; then
    echo ">>> Projekt klonen..."
    sudo -u assistant git clone \
        https://github.com/schrottsocke/projekt-personal-assistent.git \
        "$PROJ_DIR"
else
    echo ">>> Projekt existiert bereits, update..."
    sudo -u assistant git -C "$PROJ_DIR" pull
fi

# Branch wechseln
sudo -u assistant git -C "$PROJ_DIR" checkout claude/dual-personal-assistants-0Uqna

# --- Virtualenv + Dependencies ---
echo ">>> Python-Umgebung einrichten..."
sudo -u assistant bash -c "
    cd $PROJ_DIR
    python3.11 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
"

# --- Verzeichnisse ---
sudo -u assistant bash -c "
    mkdir -p $PROJ_DIR/data
    mkdir -p $PROJ_DIR/data/documents
    mkdir -p $PROJ_DIR/logs
    mkdir -p $PROJ_DIR/config
"

# --- .env Datei ---
if [ ! -f "$PROJ_DIR/.env" ]; then
    sudo -u assistant cp "$PROJ_DIR/.env.example" "$PROJ_DIR/.env"
    echo ""
    echo "======================================================"
    echo "  WICHTIG: .env Datei ausfüllen!"
    echo "  nano $PROJ_DIR/.env"
    echo "======================================================"
else
    echo ">>> .env existiert bereits."
fi

# --- Verzeichnis für Scans ---
sudo -u assistant mkdir -p "$PROJ_DIR/data/scans"

# --- Systemd Services installieren ---
echo ">>> Systemd Services installieren..."
cp "$PROJ_DIR/deploy/personal-assistant.service" \
   /etc/systemd/system/personal-assistant.service

cp "$PROJ_DIR/deploy/personal-assistant-api.service" \
   /etc/systemd/system/personal-assistant-api.service

systemctl daemon-reload
systemctl enable personal-assistant
systemctl enable personal-assistant-api
echo ">>> Services aktiviert (starten beim Reboot automatisch)."

echo ""
echo "======================================================"
echo "  Setup abgeschlossen!"
echo ""
echo "  Nächste Schritte:"
echo "  1. nano $PROJ_DIR/.env          (Keys eintragen)"
echo "  2. Google OAuth lokal ausführen (deploy/google_auth_local.py)"
echo "  3. Tokens hochladen (scp)"
echo "  4. systemctl start personal-assistant"
echo "  5. systemctl start personal-assistant-api"
echo "  6. journalctl -u personal-assistant -f  (Bot-Logs)"
echo "  7. journalctl -u personal-assistant-api -f  (API-Logs)"
echo "======================================================"
