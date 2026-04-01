#!/usr/bin/env bash
# Setup Let's Encrypt SSL for DualMind API
# Usage: sudo bash deploy/setup_ssl.sh <domain>
#
# Prerequisites:
#   - DNS A-record for <domain> must point to this server's IP
#   - Port 80 must be open (for ACME HTTP-01 challenge)
#   - Port 443 must be open (for HTTPS traffic after setup)
#   - Nginx must be installed and running
set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== SSL Setup for $DOMAIN ==="

# --- Pre-flight checks ---

echo ">>> Checking DNS resolution for $DOMAIN..."
RESOLVED_IP=$(dig +short "$DOMAIN" 2>/dev/null | tail -1)
if [ -z "$RESOLVED_IP" ]; then
    echo "ERROR: $DOMAIN does not resolve to any IP address."
    echo "  → Set an A-record in your DNS provider pointing to this server."
    echo "  → Wait for DNS propagation (5-30 minutes), then retry."
    exit 1
fi

SERVER_IP=$(curl -sf https://ifconfig.me 2>/dev/null || curl -sf https://api.ipify.org 2>/dev/null || echo "unknown")
if [ "$RESOLVED_IP" != "$SERVER_IP" ] && [ "$SERVER_IP" != "unknown" ]; then
    echo "WARNING: $DOMAIN resolves to $RESOLVED_IP but this server's IP is $SERVER_IP"
    echo "  → Certbot will fail if the domain does not point to this server."
    read -r -p "Continue anyway? [y/N] " response
    if [[ ! "$response" =~ ^[yY]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi
echo "  $DOMAIN → $RESOLVED_IP ✓"

echo ">>> Checking nginx..."
if ! command -v nginx &>/dev/null; then
    echo "ERROR: nginx is not installed. Install with: apt install nginx"
    exit 1
fi
nginx -t 2>/dev/null || { echo "ERROR: nginx config test failed. Fix before continuing."; exit 1; }
echo "  nginx config OK ✓"

# --- Install certbot ---

echo "=== Installing certbot ==="
apt-get update -qq
apt-get install -y -qq certbot python3-certbot-nginx

# --- Create ACME challenge directory ---

mkdir -p /var/www/certbot

# --- Request certificate ---

echo "=== Requesting certificate for $DOMAIN ==="

# Check if www subdomain also resolves (include it if so)
WWW_IP=$(dig +short "www.$DOMAIN" 2>/dev/null | tail -1)
if [ -n "$WWW_IP" ]; then
    echo "  www.$DOMAIN also resolves → including in certificate"
    DOMAINS="-d $DOMAIN -d www.$DOMAIN"
else
    echo "  www.$DOMAIN does not resolve → skipping (can add later)"
    DOMAINS="-d $DOMAIN"
fi

certbot --nginx $DOMAINS \
    --non-interactive \
    --agree-tos \
    --email admin@"$DOMAIN" \
    --redirect

# --- Setup auto-renewal ---

echo "=== Setting up auto-renewal ==="
systemctl enable certbot.timer
systemctl start certbot.timer

# --- Verify ---

echo "=== Verifying certificate ==="
certbot certificates -d "$DOMAIN"

echo ""
echo "=== Done! ==="
echo "Certificate installed for $DOMAIN"
echo "Auto-renewal is enabled via systemd timer."
echo ""
echo "Next steps:"
echo "  1. Deploy the HTTPS nginx config:"
echo "     sudo cp $SCRIPT_DIR/nginx.conf /etc/nginx/sites-available/dualmind-api"
echo "     sudo nginx -t && sudo systemctl reload nginx"
echo "  2. Verify HTTPS: curl -I https://$DOMAIN"
echo "  3. Test renewal:  sudo certbot renew --dry-run"
