# Kong Enterprise On-Prem Demo

This repository runs a local **self-managed Kong Enterprise hybrid** demo with a **PostgreSQL-backed control plane**, a separate **data plane**, and configuration applied by **decK**.

## Runtime

The active runtime path is:

- [docker-compose.yml](/Users/surajpillai/Documents/work/demos/learn/enterprise-api-demo/docker-compose.yml)
- [start-demo.sh](/Users/surajpillai/Documents/work/demos/learn/enterprise-api-demo/start-demo.sh)
- [stop-demo.sh](/Users/surajpillai/Documents/work/demos/learn/enterprise-api-demo/stop-demo.sh)
- [scripts/render_deck_config.py](/Users/surajpillai/Documents/work/demos/learn/enterprise-api-demo/scripts/render_deck_config.py)
- [scripts/configure_datakit.py](/Users/surajpillai/Documents/work/demos/learn/enterprise-api-demo/scripts/configure_datakit.py)

`license.json` is mounted directly into the Kong control-plane and data-plane containers at `/etc/kong/license.json`.

## What It Does

The demo UI drives real requests through a local Kong Enterprise data plane and showcases:

- header-based routing
- anonymous and consumer-scoped rate limiting
- resilience with weighted upstreams and health checks
- Azure AD token validation
- Keycloak token validation and authorization
- IP allow/deny policy
- schema validation
- request size limiting
- DataKit orchestration
- payload encryption/decryption with a custom plugin
- injection protection
- HTTP blocked / redirected transport policy
- versioned routing
- canary rollout
- API deprecation and sunset behavior
- Grafana, Loki, Tempo, and OpenTelemetry-based observability

## Services

The local stack includes:

- `postgres`
- `kong-cp`
- `kong-dp`
- `demo-ui`
- `grafana`
- `loki`
- `tempo`
- `otel-collector`
- `keycloak`
- `redis`
- mock upstream services under `services/mock_upstream`

## Prerequisites

- Docker Desktop
- `deck`
- Python 3
- OpenSSL

Optional for the Azure scene:

- `AD_PROTECTED_API_TENANT_ID`
- `AD_PROTECTED_API_AUDIENCE`
- `AD_CONSUMER1_CLIENT_ID`
- `AD_CONSUMER1_SECRET`
- `AD_CONSUMER2_CLIENT_ID`
- `AD_CONSUMER2_SECRET`

## Run

Start the stack:

```bash
./start-demo.sh
```

Prepare the Dev Portal showcase path:

```bash
./prepare-dev-portal-showcase.sh
```

Stop the stack:

```bash
./stop-demo.sh
```

## Local Endpoints

- UI: `http://localhost:8080`
- Kong Data Plane Proxy: `http://localhost:8000`
- Kong Data Plane Status: `http://localhost:8100/status`
- Kong Control Plane Admin API: `http://localhost:8001`
- Kong Control Plane Manager: `http://localhost:8002`
- Dev Portal: `http://localhost:8003/default`
  - Login: `portal1@example.com / portal1`
- Grafana: `http://localhost:3001`
- Loki: `http://localhost:3100`
- Tempo portal: `http://localhost:3200`
- Tempo API: `http://localhost:3201`
- Keycloak: `http://localhost:8081`

## Notes

- The old Konnect/Terraform provisioning path has been removed.
- The generated decK state is rendered at runtime from `scripts/render_deck_config.py`.
- Datakit plugin flow definitions are still configured after decK sync because those route plugin payloads are easier to maintain as Admin API payloads than as static decK state.
- The Dev Portal showcase notes live in [dev-portal-app-showcase.md](/Users/surajpillai/Documents/work/demos/learn/enterprise-api-demo/dev-portal-app-showcase.md).
