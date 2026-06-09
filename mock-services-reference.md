# Mock Services Reference

This document explains the locally running mock services, the scenes they support, and direct `curl` commands you can use to understand their input and output shapes without going through Kong first.

## Menu

- [Overview](#overview)
- [Shared Echo Behavior](#shared-echo-behavior)
- [Traffic And Routing: Header-Based Routing](#traffic-and-routing-header-based-routing)
- [Resilience: Failover And Health Checks](#resilience-failover-and-health-checks)
- [Identity And Generic Orders Flows](#identity-and-generic-orders-flows)
- [Monetization: Usage Metering](#monetization-usage-metering)
- [DataKit: Plugin Orchestration](#datakit-plugin-orchestration)
  - [Conditional Fallback](#conditional-fallback)
  - [Combine Results](#combine-results)
  - [Redis Cache](#redis-cache)
- [API Lifecycle](#api-lifecycle)
  - [Versioned Routing](#versioned-routing)
  - [Canary Migration](#canary-migration)
  - [Deprecation](#deprecation)
- [Keycloak Token Source](#keycloak-token-source)

## Overview

These services are started by `./start-demo.sh`.

| Service | Local URL | Purpose |
|---|---|---|
| `orders-east` | `http://localhost:9101` | Primary east-region mock Orders API |
| `orders-west` | `http://localhost:9102` | Primary west-region mock Orders API |
| `orders-instance-1` | `http://localhost:9201` | Resilience / weighted-routing mock instance |
| `orders-instance-2` | `http://localhost:9202` | Resilience / weighted-routing mock instance |
| `orders-v1` | `http://localhost:9301` | Versioned / deprecated API v1 |
| `orders-v2` | `http://localhost:9302` | Versioned / current API v2 |
| `datakit-api1` | `http://localhost:9401` | DataKit API1 mock |
| `datakit-api2` | `http://localhost:9402` | DataKit API2 mock |
| `redis` | `localhost:6379` | Redis used by DataKit cache scenario |
| `keycloak` | `http://localhost:8081` | Keycloak identity provider used by JWT-protected scenes |

All Python mock upstreams also expose:

```bash
curl -s http://localhost:<port>/health | jq
```

Example:

```bash
curl -s http://localhost:9101/health | jq
```

## Shared Echo Behavior

Most mock upstreams use the generic echo behavior in `services/mock_upstream/server.py`.

The generic echo payload includes:

- `service`
- `region`
- `api_version` when configured
- `release_stage` when configured
- `path`
- `query`
- `method`
- `request_id`
- `timestamp`
- `content_type`
- `content_length`
- `body`

Example:

```bash
curl -s \
  -H 'Content-Type: application/json' \
  -d '{"accountId":"acc-101","amount":125.75}' \
  http://localhost:9101/orders/example?channel=web | jq
```

## Traffic And Routing: Header-Based Routing

Scene services:

- `orders-east`
- `orders-west`

The upstreams themselves do not inspect `x-region`; Kong does. Direct calls below simply show what each target upstream returns once selected.

### East target

```bash
curl -s http://localhost:9101/orders/header-demo | jq
```

### West target

```bash
curl -s http://localhost:9102/orders/header-demo | jq
```

Expected distinguishing fields:

- `service`
- `region`

## Resilience: Failover And Health Checks

Scene services:

- `orders-instance-1`
- `orders-instance-2`

These are plain echo services. Kong handles weighting and failover policy.

### Instance 1

```bash
curl -s http://localhost:9201/orders/resilience | jq
```

### Instance 2

```bash
curl -s http://localhost:9202/orders/resilience | jq
```

## Identity And Generic Orders Flows

These scenes ultimately hit the generic Orders echo services:

- `Traffic Control: Rate Limiting`
- `Identity: Azure AD Token Validation`
- `Identity: Keycloak Authorization`
- `Network Policy: IP Allow/Deny`
- `Data Quality: Schema Validation`
- `Traffic Control: Request Size Limiting`
- `Security: Injection Protection`
- `Transformation: Gateway Payload Encryption/Decryption`
- `Transport Security`

Representative direct calls:

### `orders-east`

```bash
curl -s http://localhost:9101/orders/example | jq
```

### `orders-west`

```bash
curl -s http://localhost:9102/orders/example | jq
```

## Monetization: Usage Metering

Scene service:

- `orders-east` or whichever service Kong routes to behind `svc-orders-metering`

The mock upstream is still generic echo behavior. The monetization logic happens at Kong.

Representative direct call:

```bash
curl -s http://localhost:9101/orders/metering/direct | jq
```

The scene-specific behavior is not in the upstream body. It is in the Kong route and plugin layer.

## DataKit: Plugin Orchestration

Scene services:

- `datakit-api1`
- `datakit-api2`
- `redis`

This is the only mock service set with custom scene-specific endpoints.

### Conditional Fallback

Subscene purpose:

- call API1
- if API1 original status is `200`, return API1 result
- if API1 original status is non-`200`, call API2 and return API2 result

#### API1 direct success

```bash
curl -s 'http://localhost:9401/datakit/api1/fallback?mode=success' | jq
```

Returns:

- HTTP `200`
- API1 success payload

#### API1 direct failure

```bash
curl -si 'http://localhost:9401/datakit/api1/fallback?mode=fail'
```

Returns:

- HTTP `503`
- API1 failure payload

#### API1 wrapper success

This is what Datakit actually calls.

```bash
curl -s 'http://localhost:9401/datakit/api1/fallback-wrapper?mode=success' | jq
```

Expected shape:

```json
{
  "wrappedSource": "api1",
  "originalStatus": 200,
  "result": {
    "source": "api1",
    "mode": "success"
  }
}
```

#### API1 wrapper failure

```bash
curl -s 'http://localhost:9401/datakit/api1/fallback-wrapper?mode=fail' | jq
```

Expected shape:

```json
{
  "wrappedSource": "api1",
  "originalStatus": 503,
  "result": {
    "source": "api1",
    "mode": "fail"
  }
}
```

#### API2 fallback target

```bash
curl -s http://localhost:9402/datakit/api2/fallback | jq
```

Expected shape:

```json
{
  "source": "api2",
  "accountId": "acc-101",
  "status": "served-by-fallback",
  "product": "backup-account-summary"
}
```

How the subscene works:

1. Datakit calls API1 wrapper
2. reads `originalStatus`
3. if `200`, returns API1 result
4. if non-`200`, calls API2

### Combine Results

Subscene purpose:

- call API1 for a list of accounts
- call API2 for detail records
- join both on `accountId`

#### API1 account list

```bash
curl -s http://localhost:9401/datakit/api1/accounts | jq
```

Expected shape:

```json
{
  "source": "api1",
  "customerId": "cust-1001",
  "accounts": [
    {
      "accountId": "acc-101",
      "accountType": "savings",
      "status": "active",
      "nickname": "Primary Savings"
    },
    {
      "accountId": "acc-202",
      "accountType": "credit",
      "status": "delinquent",
      "nickname": "Rewards Credit"
    }
  ]
}
```

#### API2 detail lookup

```bash
curl -s \
  -H 'Content-Type: application/json' \
  -d '{"accountIds":["acc-101","acc-202"]}' \
  http://localhost:9402/datakit/api2/details | jq
```

Expected shape:

```json
{
  "source": "api2",
  "accountDetails": [
    {
      "accountId": "acc-101",
      "balance": 2400.12,
      "currency": "USD",
      "branch": "Downtown",
      "lastPaymentDate": "2026-05-01"
    },
    {
      "accountId": "acc-202",
      "balance": -320.75,
      "currency": "USD",
      "branch": "Airport",
      "lastPaymentDate": "2026-04-18"
    }
  ]
}
```

How the subscene works:

1. Datakit calls `API1_LIST`
2. extracts `accountIds`
3. Datakit calls `API2_DETAILS`
4. joins API1 and API2 on `accountId`

### Redis Cache

Subscene purpose:

- read from Redis first
- on miss, fetch from API1
- cache for `30` seconds
- on hit, serve cached payload without calling API1 again

#### API1 source endpoint

```bash
curl -s http://localhost:9401/datakit/api1/cache-source | jq
```

Expected shape:

```json
{
  "source": "api1",
  "accountId": "acc-101",
  "balance": 2400.12,
  "currency": "USD",
  "generatedAt": "..."
}
```

#### Redis visibility

If you want to inspect Redis directly:

```bash
redis-cli -p 6379 keys '*'
```

and:

```bash
redis-cli -p 6379 get 'datakit:account-cache:acc-101'
```

How the subscene works:

1. Datakit checks Redis for `datakit:account-cache:acc-101`
2. on miss, it calls API1 cache source
3. stores the payload with TTL `30`
4. on hit, it serves cached data directly

What to look for:

- same `generatedAt` during cache hits
- new `generatedAt` after TTL expiry

## API Lifecycle

### Versioned Routing

Scene services:

- `orders-v1`
- `orders-v2`

#### Path-based v1

```bash
curl -s http://localhost:9301/api/v1/orders | jq
```

#### Path-based v2

```bash
curl -s http://localhost:9302/api/v2/orders | jq
```

#### Header-based v1

Direct upstream call:

```bash
curl -s http://localhost:9301/orders/version/header | jq
```

Kong-level distinction comes from `x-api-version`, not from the upstream.

#### Header-based v2

Direct upstream call:

```bash
curl -s http://localhost:9302/orders/version/header | jq
```

What to look for:

- `service`
- `api_version`
- `release_stage`

### Canary Migration

Scene services:

- `orders-v1`
- `orders-v2`

Subscenes:

- `40% rollout`
- `time-based rollout`
- `header-based`
- `consumer-based`

The upstreams themselves do not know about the canary policy. Kong decides which upstream is selected.

#### V1 target

```bash
curl -s http://localhost:9301/orders/canary/direct | jq
```

#### V2 target

```bash
curl -s http://localhost:9302/orders/canary/direct | jq
```

Subscene notes:

- `40% rollout`
  - Kong sends a percentage of traffic to `orders-v2`
- `time-based rollout`
  - Kong increases rollout over the configured 2-minute window
- `header-based`
  - Kong can be steered by header policy
- `consumer-based`
  - Kong can steer based on consumer/ACL grouping

### Deprecation

Scene services:

- `orders-v1`
- `orders-v2`

Subscenes:

- `deprecated-v1`
- `current-v2`
- `sunset-enforced`

#### Deprecated v1 upstream

```bash
curl -s http://localhost:9301/orders/deprecation/v1 | jq
```

#### Current v2 upstream

```bash
curl -s http://localhost:9302/orders/deprecation/v2 | jq
```

Notes:

- `sunset-enforced` is not an upstream behavior
- it is a Kong request-termination policy

## Keycloak Token Source

JWT-protected scenes use Keycloak.

### Token for `consumer-1`

```bash
curl -s \
  -X POST \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials' \
  -d 'client_id=consumer-1' \
  -d 'client_secret=consumer-1-secret' \
  http://localhost:8081/realms/kong-demo/protocol/openid-connect/token | jq
```

### Token for `consumer-2`

```bash
curl -s \
  -X POST \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials' \
  -d 'client_id=consumer-2' \
  -d 'client_secret=consumer-2-secret' \
  http://localhost:8081/realms/kong-demo/protocol/openid-connect/token | jq
```

Use those bearer tokens when you want to call Kong routes directly outside the UI.
