#!/bin/sh
set -eu

run_command() {
  command_text="$1"
  printf '__CMD__ %s\n' "$command_text"
  if sh -c "$command_text"; then
    printf '__CMD_DONE__ success %s\n' "$command_text"
    return
  else
    status_code=$?
    printf '__CMD_DONE__ error %s\n' "$command_text"
    exit "$status_code"
  fi
}

echo "Starting API onboarding pipeline for Dev Portal showcase"
echo "Workspace: default"
echo "Target route: /portal/orders"

run_command "python3 /app/onboard_api_runner.py validate-spec /app/partner-orders-api.json"
run_command "python3 /app/onboard_api_runner.py render-deck /tmp/portal-showcase-deck.json"
run_command "python3 /app/onboard_api_runner.py wait-admin"
run_command "deck gateway sync --kong-addr \"$KONG_ADMIN_URL\" --headers \"Kong-Admin-Token:$KONG_ADMIN_TOKEN\" --select-tag portal-showcase /tmp/portal-showcase-deck.json"
run_command "python3 /app/onboard_api_runner.py publish-portal /app/partner-orders-api.json"
run_command "python3 /app/onboard_api_runner.py prepare-portal"
run_command "python3 /app/onboard_api_runner.py summary"
