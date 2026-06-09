#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

LOCAL_KONG_ADMIN_URL="${LOCAL_KONG_ADMIN_URL:-http://localhost:8001}"
DEV_PORTAL_URL="${DEV_PORTAL_URL:-http://localhost:8003/default}"
DEV_PORTAL_API_URL="${DEV_PORTAL_API_URL:-http://localhost:8004}"
KONG_ADMIN_TOKEN="${KONG_ADMIN_TOKEN:-local-demo-admin-token}"
DEV_PORTAL_WORKSPACE="${DEV_PORTAL_WORKSPACE:-default}"
DEV_PORTAL_DEVELOPER_EMAIL="${DEV_PORTAL_DEVELOPER_EMAIL:-portal1@example.com}"
DEV_PORTAL_DEVELOPER_PASSWORD="${DEV_PORTAL_DEVELOPER_PASSWORD:-portal1}"
START_STACK_IF_NEEDED="${START_STACK_IF_NEEDED:-true}"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

wait_for_http() {
  local url="$1"
  local label="$2"
  for _ in $(seq 1 60); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done
  echo "$label did not become ready in time" >&2
  exit 1
}

wait_for_http_with_header() {
  local url="$1"
  local label="$2"
  local header_name="$3"
  local header_value="$4"
  for _ in $(seq 1 60); do
    if curl -fsS -H "${header_name}: ${header_value}" "$url" >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done
  echo "$label did not become ready in time" >&2
  exit 1
}

ensure_stack() {
  if curl -fsS -H "Kong-Admin-Token: ${KONG_ADMIN_TOKEN}" "${LOCAL_KONG_ADMIN_URL}/status" >/dev/null 2>&1; then
    return
  fi

  if [[ "${START_STACK_IF_NEEDED}" != "true" ]]; then
    echo "Kong Admin API is not reachable at ${LOCAL_KONG_ADMIN_URL}" >&2
    echo "Start the demo stack first with ./start-demo.sh" >&2
    exit 1
  fi

  echo "Starting demo stack first"
  ./start-demo.sh
}

echo "Ensuring Kong demo stack is running"
ensure_stack

echo "Waiting for Kong Admin API"
wait_for_http_with_header "$LOCAL_KONG_ADMIN_URL/status" "Kong Admin API" "Kong-Admin-Token" "$KONG_ADMIN_TOKEN"

echo "Waiting for Dev Portal API"
wait_for_http "${DEV_PORTAL_API_URL}/${DEV_PORTAL_WORKSPACE}/session" "Dev Portal API"

echo "Enabling Dev Portal on workspace ${DEV_PORTAL_WORKSPACE}"
LOCAL_KONG_ADMIN_URL="$LOCAL_KONG_ADMIN_URL" \
KONG_ADMIN_TOKEN="$KONG_ADMIN_TOKEN" \
DEV_PORTAL_WORKSPACE="$DEV_PORTAL_WORKSPACE" \
python3 scripts/enable_dev_portal.py

echo "Configuring Dev Portal authentication"
LOCAL_KONG_ADMIN_URL="$LOCAL_KONG_ADMIN_URL" \
KONG_ADMIN_TOKEN="$KONG_ADMIN_TOKEN" \
DEV_PORTAL_WORKSPACE="$DEV_PORTAL_WORKSPACE" \
python3 scripts/configure_dev_portal_auth.py

echo "Seeding Dev Portal developer"
DEV_PORTAL_API_URL="$DEV_PORTAL_API_URL" \
DEV_PORTAL_WORKSPACE="$DEV_PORTAL_WORKSPACE" \
DEV_PORTAL_DEVELOPER_EMAIL="$DEV_PORTAL_DEVELOPER_EMAIL" \
DEV_PORTAL_DEVELOPER_PASSWORD="$DEV_PORTAL_DEVELOPER_PASSWORD" \
python3 scripts/seed_dev_portal_developer.py

echo
echo "Dev Portal showcase base is ready"
echo "Portal URL:        ${DEV_PORTAL_URL}"
echo "Portal login:      ${DEV_PORTAL_DEVELOPER_EMAIL} / ${DEV_PORTAL_DEVELOPER_PASSWORD}"
echo
echo "Suggested next steps for the app-registration demo:"
echo "1. Publish a dedicated API spec into the portal catalog."
echo "2. Apply gateway policies for that API via decK."
echo "3. Log into the portal and create an application."
echo "4. Generate credentials for the application."
echo "5. Call the API through Kong with the generated credential."
echo
echo "Design note: ./dev-portal-app-showcase.md"
