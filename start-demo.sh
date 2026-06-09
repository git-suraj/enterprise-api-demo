#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
RUNTIME_DIR="$ROOT_DIR/.runtime"
DECK_STATE_FILE="$RUNTIME_DIR/kong.deck.json"
MANAGER_REGISTRATION_FILE="$RUNTIME_DIR/manager-registrations.json"
LOCAL_KONG_ADMIN_URL="${LOCAL_KONG_ADMIN_URL:-http://localhost:8001}"
LOCAL_KONG_PROXY_URL="${LOCAL_KONG_PROXY_URL:-http://localhost:8000}"
LOCAL_KONG_DP_STATUS_URL="${LOCAL_KONG_DP_STATUS_URL:-http://localhost:8100/status}"
AUTOMATION_ADMIN_TOKEN="${KONG_ADMIN_TOKEN:-local-demo-admin-token}"
MANAGER_SESSION_SECRET="${KONG_ADMIN_GUI_SESSION_SECRET:-manager-session-secret-change-me}"
MANAGER_SESSION_CONF="{\"secret\":\"${MANAGER_SESSION_SECRET}\",\"storage\":\"kong\",\"cookie_secure\":false}"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

mkdir -p "$RUNTIME_DIR"

wait_for_docker() {
  if docker info >/dev/null 2>&1; then
    return
  fi

  if [[ "$(uname -s)" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
    echo "Starting Docker Desktop"
    open -a Docker >/dev/null 2>&1 || true
  fi

  echo "Waiting for Docker daemon"
  for _ in $(seq 1 90); do
    if docker info >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done

  echo "Docker daemon did not become ready in time" >&2
  exit 1
}

wait_for_http() {
  local url="$1"
  local label="$2"
  for _ in $(seq 1 90); do
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
  for _ in $(seq 1 90); do
    if curl -fsS -H "${header_name}: ${header_value}" "$url" >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done
  echo "$label did not become ready in time" >&2
  exit 1
}

run_migrations() {
  if KONG_ENFORCE_RBAC=off KONG_ADMIN_GUI_AUTH= KONG_ADMIN_GUI_SESSION_CONF= \
    docker compose run --rm kong-migrations kong migrations bootstrap >/dev/null 2>&1; then
    return
  fi
  KONG_ENFORCE_RBAC=off KONG_ADMIN_GUI_AUTH= KONG_ADMIN_GUI_SESSION_CONF= \
    docker compose run --rm kong-migrations kong migrations up >/dev/null
}

compose_with_bootstrap_auth() {
  KONG_ENFORCE_RBAC=off KONG_ADMIN_GUI_AUTH= KONG_ADMIN_GUI_SESSION_CONF= \
    KONG_ADMIN_TOKEN="$AUTOMATION_ADMIN_TOKEN" \
    docker compose "$@"
}

compose_with_manager_auth() {
  KONG_ENFORCE_RBAC=on KONG_ADMIN_GUI_AUTH=basic-auth \
    KONG_ADMIN_GUI_SESSION_CONF="$MANAGER_SESSION_CONF" \
    KONG_ADMIN_TOKEN="$AUTOMATION_ADMIN_TOKEN" \
    docker compose "$@"
}

if ! command -v deck >/dev/null 2>&1; then
  echo "decK is required. Install it from https://developer.konghq.com/deck/" >&2
  exit 1
fi

if [[ ! -f "$ROOT_DIR/license.json" ]]; then
  echo "license.json is required at the repository root" >&2
  exit 1
fi

wait_for_docker

echo "Preparing payload crypto materials"
python3 scripts/setup_payload_crypto_materials.py

echo "Preparing hybrid clustering materials"
python3 scripts/setup_hybrid_clustering_materials.py

echo "Starting local dependencies"
docker compose up -d \
  postgres \
  orders-east \
  orders-west \
  orders-instance-1 \
  orders-instance-2 \
  orders-v1 \
  orders-v2 \
  datakit-api1 \
  datakit-api2 \
  redis \
  keycloak \
  loki \
  tempo \
  otel-collector \
  grafana \
  crypto-helper

echo "Bootstrapping local Keycloak realm"
python3 scripts/bootstrap_keycloak.py

echo "Running Kong database migrations"
run_migrations

echo "Starting Kong Enterprise in bootstrap mode"
compose_with_bootstrap_auth up -d kong-cp
wait_for_http "$LOCAL_KONG_ADMIN_URL/status" "Kong Admin API"

echo "Rendering decK state"
python3 scripts/render_deck_config.py >"$DECK_STATE_FILE"

echo "Syncing gateway configuration with decK"
deck gateway sync --kong-addr "$LOCAL_KONG_ADMIN_URL" "$DECK_STATE_FILE"

echo "Preparing Kong Manager users, workspaces, and automation token"
LOCAL_KONG_ADMIN_URL="$LOCAL_KONG_ADMIN_URL" \
KONG_ADMIN_TOKEN="$AUTOMATION_ADMIN_TOKEN" \
MANAGER_REGISTRATION_FILE="$MANAGER_REGISTRATION_FILE" \
python3 scripts/bootstrap_manager_users.py prepare

echo "Recreating Kong Enterprise with Manager auth enabled"
compose_with_manager_auth up -d kong-cp
wait_for_http_with_header "$LOCAL_KONG_ADMIN_URL/status" "Kong Admin API" "Kong-Admin-Token" "$AUTOMATION_ADMIN_TOKEN"

echo "Registering Kong Manager passwords"
LOCAL_KONG_ADMIN_URL="$LOCAL_KONG_ADMIN_URL" \
MANAGER_REGISTRATION_FILE="$MANAGER_REGISTRATION_FILE" \
KONG_ADMIN_TOKEN="$AUTOMATION_ADMIN_TOKEN" \
python3 scripts/bootstrap_manager_users.py register

echo "Configuring default Dev Portal"
LOCAL_KONG_ADMIN_URL="$LOCAL_KONG_ADMIN_URL" \
KONG_ADMIN_TOKEN="$AUTOMATION_ADMIN_TOKEN" \
python3 scripts/configure_dev_portal_auth.py

echo "Configuring Datakit plugin flows"
KONG_ADMIN_URL="$LOCAL_KONG_ADMIN_URL" \
KONG_ADMIN_TOKEN="$AUTOMATION_ADMIN_TOKEN" \
python3 scripts/configure_datakit.py

echo "Starting Kong data plane"
compose_with_manager_auth up -d kong-dp
wait_for_http "$LOCAL_KONG_DP_STATUS_URL" "Kong data plane status"

echo "Seeding Dev Portal developer"
python3 scripts/seed_dev_portal_developer.py

echo "Starting demo UI"
compose_with_manager_auth up -d demo-ui
wait_for_http "http://localhost:8080/api/config" "demo UI"

echo "Installing Dev Portal customizations"
LOCAL_KONG_ADMIN_URL="$LOCAL_KONG_ADMIN_URL" \
KONG_ADMIN_TOKEN="$AUTOMATION_ADMIN_TOKEN" \
python3 scripts/install_dev_portal_customizations.py

echo
echo "Configuration applied"
echo "UI:               http://localhost:8080"
echo "Kong DP Proxy:     http://localhost:8000"
echo "Kong DP Proxy TLS: https://localhost:8443"
echo "Kong DP Status:    http://localhost:8100/status"
echo "Kong CP Admin API: http://localhost:8001"
echo "Kong CP Manager:   http://localhost:8002"
echo "Dev Portal:        http://localhost:8003/default"
echo "Dev Portal Login:  portal1@example.com / portal1"
echo "Grafana:           http://localhost:3001"
echo "Loki:              http://localhost:3100"
echo "Trace Portal:      http://localhost:3200"
echo "Tempo API:         http://localhost:3201"
echo "Orders East Mock:  http://localhost:9101"
echo "Orders West Mock:  http://localhost:9102"
echo "Instance 1 Mock:   http://localhost:9201"
echo "Instance 2 Mock:   http://localhost:9202"
echo "Orders V1 Mock:    http://localhost:9301"
echo "Orders V2 Mock:    http://localhost:9302"
echo "Keycloak:          http://localhost:8081"
