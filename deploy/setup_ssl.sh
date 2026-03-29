#!/usr/bin/env bash
# Setup Let's Encrypt SSL for DualMind API
# Usage: sudo bash deploy/setup_ssl.sh <domain>
set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain>}"

echo "=== Installing certbot ==="
apt-get update -qq
apt-get install -y -qq certbot python3-certbot-nginx

echo "=== Requesting certificate for $DOMAIN ==="
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN" --redirect

echo "=== Setting up auto-renewal ==="
systemctl enable certbot.timer
systemctl start certbot.timer

echo "=== Done! Certificate installed for $DOMAIN ==="
echo "Auto-renewal is enabled via systemd timer."
