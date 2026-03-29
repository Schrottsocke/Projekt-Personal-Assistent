#!/usr/bin/env bash
# Health check script for DualMind Personal Assistant
# Polls /status endpoint and sends Telegram alert on failure
#
# Usage: bash scripts/health_check.sh
# Cron:  */5 * * * * /path/to/scripts/health_check.sh
#
# Required env vars:
#   HEALTH_CHECK_URL    - API status endpoint (default: http://localhost:8000/status)
#   TELEGRAM_BOT_TOKEN  - Telegram bot token for alerts
#   TELEGRAM_CHAT_ID    - Chat ID to send alerts to
#   STATE_FILE          - Path to state file (default: /tmp/dualmind-health-state)

set -euo pipefail

URL="${HEALTH_CHECK_URL:-http://localhost:8000/status}"
STATE_FILE="${STATE_FILE:-/tmp/dualmind-health-state}"
PREV_STATE="up"

# Read previous state
if [[ -f "$STATE_FILE" ]]; then
    PREV_STATE=$(cat "$STATE_FILE")
fi

# Check health
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL" 2>/dev/null || echo "000")

if [[ "$HTTP_CODE" == "200" ]]; then
    CURRENT_STATE="up"
else
    CURRENT_STATE="down"
fi

# Only alert on state change (no spam)
if [[ "$CURRENT_STATE" != "$PREV_STATE" ]]; then
    if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
        if [[ "$CURRENT_STATE" == "down" ]]; then
            MSG="DualMind API is DOWN (HTTP $HTTP_CODE) - $URL"
        else
            MSG="DualMind API is back UP - $URL"
        fi
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${MSG}" \
            -d "parse_mode=HTML" > /dev/null 2>&1 || true
    fi
    echo "$CURRENT_STATE" > "$STATE_FILE"
fi

# Always log
echo "$(date -Iseconds) status=$CURRENT_STATE http=$HTTP_CODE url=$URL"
