#!/usr/bin/env bash
# Setup Let's Encrypt SSL for DualMind API
# Usage: sudo bash deploy/setup_ssl.sh <domain>
#
# This script handles the full bootstrapping process:
#   1. Deploys a temporary HTTP-only nginx config with the correct server_name
#   2. Requests a Let's Encrypt certificate via certbot
#   3. Deploys the final HTTPS nginx config
#   4. Enables auto-renewal
#
# Prerequisites:
#   - DNS A-record for <domain> must point to this server's IP
#   - Port 80 must be open (for ACME HTTP-01 challenge)
#   - Port 443 must be open (for HTTPS traffic after setup)
#   - Nginx must be installed and running
set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NGINX_SITE="/etc/nginx/sites-available/dualmind-api"
NGINX_ENABLED="/etc/nginx/sites-enabled/dualmind-api"

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

SERVER_IP=$(curl -4 -sf https://ifconfig.me 2>/dev/null || curl -4 -sf https://api.ipify.org 2>/dev/null || echo "unknown")
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
echo "  nginx found ✓"

# --- Install certbot ---

echo "=== Installing certbot ==="
apt-get update -qq
apt-get install -y -qq certbot python3-certbot-nginx

# --- Create ACME challenge directory ---

mkdir -p /var/www/certbot

# --- Phase 1: Deploy temporary HTTP-only config with correct server_name ---
# Certbot --nginx needs a server block with server_name matching the domain.
# The final nginx.conf includes HTTPS blocks that require certs to exist,
# so we deploy a temporary HTTP-only config first.

echo "=== Deploying temporary HTTP-only nginx config ==="

cat > "$NGINX_SITE" << CONF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
}
CONF

# Ensure symlink exists
ln -sf "$NGINX_SITE" "$NGINX_ENABLED"
# Remove default site if it exists (avoids conflicts on port 80)
rm -f /etc/nginx/sites-enabled/default

nginx -t || { echo "ERROR: temporary nginx config failed validation"; exit 1; }
systemctl reload nginx
echo "  temporary config deployed ✓"

# --- Phase 2: Request certificate ---

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

# Check if cert already exists (e.g. from a previous failed install)
if certbot certificates -d "$DOMAIN" 2>/dev/null | grep -q "Certificate Name"; then
    echo "  Certificate already exists → installing into nginx"
    certbot install --cert-name "$DOMAIN" --nginx --non-interactive --redirect
else
    certbot --nginx $DOMAINS \
        --non-interactive \
        --agree-tos \
        --email admin@"$DOMAIN" \
        --redirect
fi

# --- Phase 3: Deploy final HTTPS config ---

echo "=== Deploying final HTTPS nginx config ==="
cp "$SCRIPT_DIR/nginx.conf" "$NGINX_SITE"
nginx -t || {
    echo "ERROR: final nginx config failed validation."
    echo "  Certbot's auto-generated config is still active and working."
    echo "  Fix deploy/nginx.conf and re-run: sudo cp deploy/nginx.conf $NGINX_SITE && sudo nginx -t && sudo systemctl reload nginx"
    exit 1
}
systemctl reload nginx
echo "  final HTTPS config deployed ✓"

# --- Setup auto-renewal ---

echo "=== Setting up auto-renewal ==="
systemctl enable certbot.timer
systemctl start certbot.timer

# --- Verify ---

echo "=== Verifying ==="
echo ""
certbot certificates -d "$DOMAIN"
echo ""

echo "=== Done! SSL is active for $DOMAIN ==="
echo ""
echo "Verification commands:"
echo "  curl -I http://$DOMAIN          # should 301 → https"
echo "  curl -I https://$DOMAIN         # should 200"
echo "  curl https://$DOMAIN/health     # API health check"
echo "  sudo certbot renew --dry-run    # test auto-renewal"
