#!/usr/bin/env bash
# Validate that all JS view files are listed in sw.js SHELL_ASSETS.
# Exit 1 if any are missing (useful for CI / pre-commit).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SW_FILE="$REPO_ROOT/api/static/sw.js"
VIEWS_DIR="$REPO_ROOT/api/static/js/views"

if [ ! -f "$SW_FILE" ]; then
  echo "ERROR: sw.js not found at $SW_FILE"
  exit 1
fi

missing=0

for js in "$VIEWS_DIR"/*.js; do
  filename="$(basename "$js")"
  expected="/static/js/views/$filename"
  if ! grep -qF "$expected" "$SW_FILE"; then
    echo "MISSING in SHELL_ASSETS: $expected"
    missing=$((missing + 1))
  fi
done

if [ "$missing" -gt 0 ]; then
  echo ""
  echo "$missing view file(s) missing from sw.js SHELL_ASSETS"
  exit 1
else
  echo "OK: all view files present in sw.js SHELL_ASSETS"
  exit 0
fi
