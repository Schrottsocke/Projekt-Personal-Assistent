#!/usr/bin/env bash
set -euo pipefail

APP_URL="https://dualmind.cloud"

# === AUTH ===
TAAKE_PW=$(grep API_PASSWORD_TAAKE .env | cut -d'=' -f2 | tr -d '"' | tr -d ' ')
if [ -z "$TAAKE_PW" ]; then
  echo "❌ API_PASSWORD_TAAKE nicht in .env gefunden"
  exit 1
fi

LOGIN_RESP=$(curl -s -X POST "$APP_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"taake\",\"password\":\"$TAAKE_PW\"}")

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token','LOGIN_FEHLER'))" 2>/dev/null)

if [ "$TOKEN" = "LOGIN_FEHLER" ] || [ -z "$TOKEN" ]; then
  echo "❌ Login fehlgeschlagen. Response: $LOGIN_RESP"
  exit 1
fi
echo "✅ Login OK — Token: ${TOKEN:0:40}..."

# === 1. BASIS-ERREICHBARKEIT ===
echo ""
echo "=== 1. BASIS-ERREICHBARKEIT ==="
for path in "/" "/app" "/docs" "/health"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$APP_URL$path")
  echo "$path → $CODE"
done

echo ""
echo "--- Health Details ---"
curl -s --max-time 10 "$APP_URL/health" | python3 -m json.tool 2>/dev/null || echo "(kein JSON)"

# === 2. ROUTER HEALTH-CHECKS ===
echo ""
echo "=== 2. ROUTER HEALTH-CHECKS ==="
for prefix in finance inventory family notifications gdpr onboarding \
              dashboard tasks calendar shopping recipes meal-plan \
              drive email shifts contacts search weather \
              suggestions templates automation inbox; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
    -H "Authorization: Bearer $TOKEN" \
    "$APP_URL/$prefix")
  echo "$prefix → $CODE"
done

# === 3. KERNFUNKTIONEN ===
echo ""
echo "=== 3a. TASKS ==="
TASK=$(curl -s -X POST "$APP_URL/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Audit-Test","priority":"medium"}')
echo "Create Response: $TASK"

TASK_ID=$(echo "$TASK" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('id',''))" 2>/dev/null)

if [ -n "$TASK_ID" ] && [ "$TASK_ID" != "None" ] && [ "$TASK_ID" != "" ]; then
  echo "Task ID: $TASK_ID"
  curl -s -X PATCH "$APP_URL/tasks/$TASK_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"title":"Audit-Test EDITED"}' \
    -o /dev/null -w "Edit Task   → %{http_code}\n"
  curl -s -X DELETE "$APP_URL/tasks/$TASK_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -o /dev/null -w "Delete Task → %{http_code}\n"
else
  echo "⚠️ Task-Create fehlgeschlagen – Edit/Delete übersprungen"
fi

echo ""
echo "=== 3b. CALENDAR ==="
EVENT=$(curl -s -X POST "$APP_URL/calendar/events" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Audit-Event","start":"2026-04-10T10:00:00","end":"2026-04-10T11:00:00"}')
echo "Create Response: $EVENT"
EVENT_ID=$(echo "$EVENT" | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('id',''))" 2>/dev/null)
if [ -n "$EVENT_ID" ] && [ "$EVENT_ID" != "None" ] && [ "$EVENT_ID" != "" ]; then
  echo "Event ID: $EVENT_ID"
  curl -s -X DELETE "$APP_URL/calendar/events/$EVENT_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -o /dev/null -w "Delete Event → %{http_code}\n"
else
  echo "⚠️ Event-Create fehlgeschlagen – Delete übersprungen"
fi

echo ""
echo "=== 3c. SEARCH ==="
SEARCH_RESP=$(curl -s --max-time 10 "$APP_URL/search?q=test" \
  -H "Authorization: Bearer $TOKEN")
echo "$SEARCH_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Ergebnisse: {len(d) if isinstance(d,list) else d}')" 2>/dev/null || echo "Response: $SEARCH_RESP"

echo ""
echo "=== 3d. CHAT ==="
CHAT_RESP=$(curl -s --max-time 30 -X POST "$APP_URL/chat/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Audit-Ping"}')
echo "Response: ${CHAT_RESP:0:200}"

echo ""
echo "=== 3e. INBOX ==="
INBOX_RESP=$(curl -s --max-time 10 "$APP_URL/inbox/messages" \
  -H "Authorization: Bearer $TOKEN")
echo "$INBOX_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Messages: {len(d) if isinstance(d,list) else d}')" 2>/dev/null || echo "Response: $INBOX_RESP"

echo ""
echo "=== 3f. SHOPPING ==="
SHOP_RESP=$(curl -s --max-time 10 "$APP_URL/shopping/items" \
  -H "Authorization: Bearer $TOKEN")
echo "$SHOP_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Items: {len(d) if isinstance(d,list) else d}')" 2>/dev/null || echo "Response: $SHOP_RESP"

echo ""
echo "=== 3g. CONTACTS ==="
CONTACTS_RESP=$(curl -s --max-time 10 "$APP_URL/contacts" \
  -H "Authorization: Bearer $TOKEN")
echo "$CONTACTS_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Contacts: {len(d) if isinstance(d,list) else d}')" 2>/dev/null || echo "Response: $CONTACTS_RESP"

echo ""
echo "=== 3h. SHIFTS ==="
SHIFTS_RESP=$(curl -s --max-time 10 "$APP_URL/shifts" \
  -H "Authorization: Bearer $TOKEN")
echo "$SHIFTS_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Shifts: {len(d) if isinstance(d,list) else d}')" 2>/dev/null || echo "Response: $SHIFTS_RESP"

# === 4. NEUE PRIVATKUNDEN-ROUTER ===
echo ""
echo "=== 4. NEUE ROUTER ==="
for ep in "finance/expenses" "finance/contracts" \
          "inventory/items" "family/lists" \
          "notifications" "onboarding/status" "gdpr/export"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
    -H "Authorization: Bearer $TOKEN" "$APP_URL/$ep")
  echo "$ep → $CODE"
done

# === 5. STATIC ASSETS DER PWA ===
echo ""
echo "=== 5. STATIC ASSETS ==="
for asset in "static/app.js" "static/style.css" "static/css/app.css" \
             "static/js/app.js" "static/js/router.js" "static/js/api.js" \
             "app/sw.js" "static/manifest.json" "static/sw.js"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$APP_URL/$asset")
  echo "$asset → $CODE"
done

echo ""
echo "========================================="
echo "  AUDIT ABGESCHLOSSEN — $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="
echo ""
echo "Kopiere die gesamte Ausgabe und paste sie in die Claude-Session."
