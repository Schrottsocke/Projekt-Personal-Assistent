#!/bin/bash
# =============================================================================
# bootstrap.sh – Einmaliges Setup: PAT einrichten + Code pullen + Services starten
# Ausführen als ROOT auf dem Server:
#
#   bash /home/assistant/projekt-personal-assistent/deploy/bootstrap.sh ghp_DEINTOKEN
#
# Oder direkt von GitHub (vor dem ersten Pull):
#   curl -fsSL https://raw.githubusercontent.com/Schrottsocke/Projekt-Personal-Assistent/claude/dual-personal-assistants-0Uqna/deploy/bootstrap.sh | bash -s -- ghp_DEINTOKEN
# =============================================================================

set -e

PAT="${1:-}"
PROJ_DIR="/home/assistant/projekt-personal-assistent"
BRANCH="claude/dual-personal-assistants-0Uqna"
REPO="Schrottsocke/Projekt-Personal-Assistent"

# --- Farben ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}  $*"; }
warn() { echo -e "${YELLOW}[!!]${NC}  $*"; }
fail() { echo -e "${RED}[ERR]${NC} $*"; exit 1; }

echo ""
echo "======================================================"
echo "  Personal Assistant – Bootstrap Setup"
echo "======================================================"

# --- PAT prüfen ---
if [ -z "$PAT" ]; then
    echo ""
    fail "Kein PAT übergeben. Verwendung:
  bash bootstrap.sh ghp_DEINTOKEN

  PAT erstellen: GitHub → Settings → Developer Settings
                 → Personal access tokens → Tokens (classic)
                 → Generate new token → Scope: repo"
fi

if [[ "$PAT" == "<PAT>" ]] || [[ "$PAT" == "ghp_DEINTOKEN" ]]; then
    fail "Das ist ein Platzhalter, kein echter Token. Bitte einen echten ghp_... Token übergeben."
fi

if [[ ! "$PAT" =~ ^ghp_ ]] && [[ ! "$PAT" =~ ^github_pat_ ]]; then
    warn "Token sieht ungewöhnlich aus (erwartet: ghp_... oder github_pat_...). Fortfahren..."
fi

# --- Benutzer anlegen falls nötig ---
if ! id "assistant" &>/dev/null; then
    echo ">>> Benutzer 'assistant' anlegen..."
    useradd -m -s /bin/bash assistant
    ok "Benutzer 'assistant' erstellt."
fi

# --- Git Remote URL mit PAT setzen ---
echo ""
echo ">>> Git Remote URL mit PAT konfigurieren..."
sudo -u assistant git -C "$PROJ_DIR" remote set-url origin \
    "https://${PAT}@github.com/${REPO}.git"
ok "Remote URL gesetzt."

# --- Neuesten Code pullen ---
echo ">>> Code aktualisieren (Branch: $BRANCH)..."
sudo -u assistant git -C "$PROJ_DIR" fetch origin "$BRANCH"
sudo -u assistant git -C "$PROJ_DIR" checkout "$BRANCH"
sudo -u assistant git -C "$PROJ_DIR" pull --rebase origin "$BRANCH"
ok "Code aktuell."

# --- Dependencies aktualisieren ---
echo ">>> Python-Dependencies aktualisieren..."
sudo -u assistant bash -c "
    cd $PROJ_DIR
    source venv/bin/activate
    pip install -r requirements.txt -q
"
ok "Dependencies installiert."

# --- WEBHOOK_SECRET in .env setzen (falls fehlt) ---
ENV_FILE="$PROJ_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    if ! grep -q "^WEBHOOK_SECRET=" "$ENV_FILE"; then
        # Zufälligen Secret generieren
        WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        echo "" >> "$ENV_FILE"
        echo "WEBHOOK_SECRET=${WEBHOOK_SECRET}" >> "$ENV_FILE"
        echo "WEBHOOK_PORT=9000" >> "$ENV_FILE"
        echo "DEPLOY_BRANCH=${BRANCH}" >> "$ENV_FILE"
        ok "WEBHOOK_SECRET automatisch generiert und in .env eingetragen."
        echo ""
        warn "Merke dir diesen Secret für die GitHub Webhook-Konfiguration:"
        echo -e "  ${YELLOW}WEBHOOK_SECRET = ${WEBHOOK_SECRET}${NC}"
        echo ""
    else
        ok "WEBHOOK_SECRET bereits in .env vorhanden."
    fi
else
    warn ".env nicht gefunden – überspringe WEBHOOK_SECRET."
fi

# --- Webhook Service installieren + starten ---
echo ">>> Webhook-Service installieren..."
cp "$PROJ_DIR/deploy/personal-assistant-webhook.service" \
   /etc/systemd/system/personal-assistant-webhook.service
systemctl daemon-reload
systemctl enable personal-assistant-webhook
systemctl restart personal-assistant-webhook
sleep 2
if systemctl is-active --quiet personal-assistant-webhook; then
    ok "personal-assistant-webhook läuft."
else
    warn "personal-assistant-webhook hat Probleme. Logs: journalctl -u personal-assistant-webhook -n 20"
fi

# --- Bot + API neustarten ---
echo ">>> Bot und API neustarten..."
systemctl restart personal-assistant 2>/dev/null && ok "personal-assistant neugestartet." || warn "personal-assistant: Fehler beim Neustart."
systemctl restart personal-assistant-api 2>/dev/null && ok "personal-assistant-api neugestartet." || warn "personal-assistant-api: Fehler beim Neustart."

# --- Status anzeigen ---
echo ""
echo "======================================================"
echo "  Service-Status:"
echo "======================================================"
systemctl is-active --quiet personal-assistant      && echo -e "  Bot:     ${GREEN}aktiv${NC}" || echo -e "  Bot:     ${RED}inaktiv${NC}"
systemctl is-active --quiet personal-assistant-api  && echo -e "  API:     ${GREEN}aktiv${NC}" || echo -e "  API:     ${RED}inaktiv${NC}"
systemctl is-active --quiet personal-assistant-webhook && echo -e "  Webhook: ${GREEN}aktiv${NC}" || echo -e "  Webhook: ${RED}inaktiv${NC}"

# --- Nächste Schritte ---
WEBHOOK_SECRET_VAL=$(grep "^WEBHOOK_SECRET=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "siehe .env")
echo ""
echo "======================================================"
echo "  Noch offen (manuell):"
echo "======================================================"
echo ""
echo "  1. GitHub Webhook einrichten:"
echo "     URL:    http://72.62.152.187:9000/deploy"
echo "     Secret: ${WEBHOOK_SECRET_VAL}"
echo "     Event:  Just the push event"
echo "     Pfad:   GitHub → Repo → Settings → Webhooks → Add webhook"
echo ""
echo "  2. Hostinger Firewall: TCP Port 9000 öffnen"
echo "     Hostinger → VPS → Firewall → Regel hinzufügen"
echo ""
echo "  3. Status prüfen:"
echo "     curl http://72.62.152.187:8000/status"
echo ""
echo "======================================================"
echo "  Bootstrap abgeschlossen!"
echo "======================================================"
