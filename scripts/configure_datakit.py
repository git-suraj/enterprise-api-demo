#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request


SSL_CONTEXT = ssl._create_unverified_context()


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} must be set")
    return value


def api_json(method: str, url: str, payload: dict | None = None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    admin_token = os.environ.get("KONG_ADMIN_TOKEN", "").strip()
    if admin_token:
        headers["Kong-Admin-Token"] = admin_token
    request = urllib.request.Request(
        url,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20, context=SSL_CONTEXT) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {url} failed with {exc.code}: {error_body}") from exc


def route_plugin_payloads():
    role_headers = {
        "name": "ROLE_HEADERS",
        "type": "jq",
        "inputs": {"payload": "TOKEN.payload"},
        "jq": (
            '{\n'
            '  "x-authenticated-role": (\n'
            '    (.payload.realm_access.roles // [])\n'
            '    | map(select(. == "api-access"))[0]\n'
            '      // ((.payload.realm_access.roles // [])[0] // "unknown")\n'
            "  )\n"
            "}\n"
        ),
    }

    return {
        "route-datakit-fallback": {
            "name": "datakit",
            "config": {
                "nodes": [
                    {
                        "name": "AUTHORIZATION_HEADER",
                        "type": "jq",
                        "input": "request.headers",
                        "jq": 'with_entries(.key |= ascii_downcase) | .authorization // ""\n',
                    },
                    {"name": "TOKEN", "type": "jwt_decode", "input": "AUTHORIZATION_HEADER"},
                    role_headers,
                    {
                        "name": "API1_CALL",
                        "type": "call",
                        "method": "GET",
                        "url": "http://datakit-api1:9401/datakit/api1/fallback-wrapper",
                        "inputs": {"query": "request.query"},
                    },
                    {"name": "API1_STATUS", "type": "jq", "input": "API1_CALL.body", "jq": ".originalStatus\n"},
                    {"name": "API1_RESULT", "type": "jq", "input": "API1_CALL.body", "jq": ".result\n"},
                    {"name": "API1_SUCCEEDED", "type": "jq", "input": "API1_STATUS", "jq": ". == 200\n"},
                    {
                        "name": "FALLBACK_BRANCH",
                        "type": "branch",
                        "input": "API1_SUCCEEDED",
                        "then": ["API1_BODY", "API1_HEADERS", "EXIT_API1"],
                        "else": ["API2_CALL", "FALLBACK_BODY", "FALLBACK_HEADERS", "EXIT_FALLBACK"],
                    },
                    {
                        "name": "API2_CALL",
                        "type": "call",
                        "method": "GET",
                        "url": "http://datakit-api2:9402/datakit/api2/fallback",
                    },
                    {
                        "name": "API1_BODY",
                        "type": "jq",
                        "inputs": {"status": "API1_STATUS", "body": "API1_RESULT"},
                        "jq": '{\n  decision: "api1-success",\n  api1Status: .status,\n  source: "api1",\n  result: .body\n}\n',
                    },
                    {
                        "name": "API1_HEADERS",
                        "type": "jq",
                        "inputs": {"role": "ROLE_HEADERS"},
                        "jq": '.role * {\n  "x-datakit-scenario": "conditional-fallback",\n  "x-datakit-decision": "api1-success"\n}\n',
                    },
                    {
                        "name": "EXIT_API1",
                        "type": "exit",
                        "status": 200,
                        "inputs": {"body": "API1_BODY", "headers": "API1_HEADERS"},
                    },
                    {
                        "name": "FALLBACK_BODY",
                        "type": "jq",
                        "inputs": {
                            "api1_status": "API1_STATUS",
                            "api1_body": "API1_RESULT",
                            "api2_body": "API2_CALL.body",
                        },
                        "jq": (
                            '{\n'
                            '  decision: "api1-non-200-fallback",\n'
                            "  api1Status: .api1_status,\n"
                            "  api1Result: .api1_body,\n"
                            '  source: "api2",\n'
                            "  result: .api2_body\n"
                            "}\n"
                        ),
                    },
                    {
                        "name": "FALLBACK_HEADERS",
                        "type": "jq",
                        "inputs": {"role": "ROLE_HEADERS"},
                        "jq": '.role * {\n  "x-datakit-scenario": "conditional-fallback",\n  "x-datakit-decision": "api2-fallback"\n}\n',
                    },
                    {
                        "name": "EXIT_FALLBACK",
                        "type": "exit",
                        "status": 200,
                        "inputs": {"body": "FALLBACK_BODY", "headers": "FALLBACK_HEADERS"},
                    },
                ]
            },
        },
        "route-datakit-combine": {
            "name": "datakit",
            "config": {
                "nodes": [
                    {
                        "name": "AUTHORIZATION_HEADER",
                        "type": "jq",
                        "input": "request.headers",
                        "jq": 'with_entries(.key |= ascii_downcase) | .authorization // ""\n',
                    },
                    {"name": "TOKEN", "type": "jwt_decode", "input": "AUTHORIZATION_HEADER"},
                    role_headers,
                    {"name": "API1_LIST", "type": "call", "method": "GET", "url": "http://datakit-api1:9401/datakit/api1/accounts"},
                    {
                        "name": "DETAILS_REQUEST",
                        "type": "jq",
                        "inputs": {"body": "API1_LIST.body"},
                        "jq": '{\n  accountIds: [.body.accounts[].accountId]\n}\n',
                    },
                    {
                        "name": "API2_DETAILS",
                        "type": "call",
                        "method": "POST",
                        "url": "http://datakit-api2:9402/datakit/api2/details",
                        "inputs": {"body": "DETAILS_REQUEST"},
                    },
                    {
                        "name": "JOIN_RESULTS",
                        "type": "jq",
                        "inputs": {"api1": "API1_LIST.body", "api2": "API2_DETAILS.body"},
                        "jq": (
                            "{\n"
                            "  customerId: .api1.customerId,\n"
                            "  joinedAt: .api2.generatedAt,\n"
                            "  accounts: [\n"
                            "    .api1.accounts[] as $acct\n"
                            "    | (.api2.accountDetails | map(select(.accountId == $acct.accountId)) | .[0]) as $detail\n"
                            "    | $acct + {\n"
                            "        balance: $detail.balance,\n"
                            "        currency: $detail.currency,\n"
                            "        branch: $detail.branch,\n"
                            "        lastPaymentDate: $detail.lastPaymentDate\n"
                            "      }\n"
                            "  ]\n"
                            "}\n"
                        ),
                    },
                    {
                        "name": "COMBINE_HEADERS",
                        "type": "jq",
                        "inputs": {"role": "ROLE_HEADERS"},
                        "jq": '.role * {\n  "x-datakit-scenario": "combine-results",\n  "x-datakit-join-key": "accountId"\n}\n',
                    },
                    {
                        "name": "EXIT_COMBINE",
                        "type": "exit",
                        "status": 200,
                        "inputs": {"body": "JOIN_RESULTS", "headers": "COMBINE_HEADERS"},
                    },
                ]
            },
        },
        "route-datakit-cache": {
            "name": "datakit",
            "config": {
                "resources": {
                    "cache": {
                        "strategy": "redis",
                        "redis": {"host": "redis", "port": 6379, "database": 0},
                    }
                },
                "nodes": [
                    {
                        "name": "AUTHORIZATION_HEADER",
                        "type": "jq",
                        "input": "request.headers",
                        "jq": 'with_entries(.key |= ascii_downcase) | .authorization // ""\n',
                    },
                    {"name": "TOKEN", "type": "jwt_decode", "input": "AUTHORIZATION_HEADER"},
                    role_headers,
                    {"name": "CACHE_KEY", "type": "static", "values": {"key": "datakit:account-cache:acc-101"}},
                    {"name": "CACHE_TTL", "type": "static", "values": {"ttl": 30}},
                    {"name": "GET_CACHE", "type": "cache", "input": "CACHE_KEY"},
                    {
                        "name": "CACHE_BRANCH",
                        "type": "branch",
                        "input": "GET_CACHE.miss",
                        "then": ["FRESH_CALL", "CACHE_ENVELOPE", "SET_CACHE", "MISS_BODY", "MISS_HEADERS", "EXIT_MISS"],
                        "else": ["HIT_BODY", "HIT_HEADERS", "EXIT_HIT"],
                    },
                    {
                        "name": "FRESH_CALL",
                        "type": "call",
                        "method": "GET",
                        "url": "http://datakit-api1:9401/datakit/api1/cache-source",
                    },
                    {
                        "name": "CACHE_ENVELOPE",
                        "type": "jq",
                        "inputs": {"payload": "FRESH_CALL.body", "ttl": "CACHE_TTL.ttl"},
                        "jq": ".payload + {\n  cachedTtlSeconds: .ttl\n}\n",
                    },
                    {
                        "name": "SET_CACHE",
                        "type": "cache",
                        "inputs": {"key": "CACHE_KEY.key", "ttl": "CACHE_TTL.ttl", "data": "CACHE_ENVELOPE"},
                    },
                    {
                        "name": "MISS_BODY",
                        "type": "jq",
                        "inputs": {"payload": "CACHE_ENVELOPE"},
                        "jq": '.payload + {\n  cacheStatus: "MISS",\n  cacheExplanation: "Fresh response cached for 30 seconds."\n}\n',
                    },
                    {
                        "name": "MISS_HEADERS",
                        "type": "jq",
                        "inputs": {"role": "ROLE_HEADERS"},
                        "jq": '.role * {\n  "x-datakit-scenario": "redis-cache",\n  "x-cache-status": "MISS",\n  "x-cache-ttl-seconds": "30"\n}\n',
                    },
                    {
                        "name": "EXIT_MISS",
                        "type": "exit",
                        "status": 200,
                        "inputs": {"body": "MISS_BODY", "headers": "MISS_HEADERS"},
                    },
                    {
                        "name": "HIT_BODY",
                        "type": "jq",
                        "inputs": {"cached": "GET_CACHE.data", "ttl": "CACHE_TTL.ttl"},
                        "jq": '.cached + {\n  cacheStatus: "HIT",\n  cacheExplanation: ("Served from Redis cache within " + (.ttl | tostring) + " seconds.")\n}\n',
                    },
                    {
                        "name": "HIT_HEADERS",
                        "type": "jq",
                        "inputs": {"role": "ROLE_HEADERS"},
                        "jq": '.role * {\n  "x-datakit-scenario": "redis-cache",\n  "x-cache-status": "HIT",\n  "x-cache-ttl-seconds": "30"\n}\n',
                    },
                    {
                        "name": "EXIT_HIT",
                        "type": "exit",
                        "status": 200,
                        "inputs": {"body": "HIT_BODY", "headers": "HIT_HEADERS"},
                    },
                ],
            },
        },
    }


def main():
    base = require_env("KONG_ADMIN_URL").rstrip("/")

    routes = api_json("GET", f"{base}/routes?size=1000").get("data", [])
    routes_by_name = {route["name"]: route for route in routes}
    configured = []

    for route_name, payload in route_plugin_payloads().items():
        route = routes_by_name.get(route_name)
        if route is None:
            raise SystemExit(f"Could not find route {route_name}")
        route_id = route["id"]
        plugins_url = f"{base}/routes/{route_id}/plugins"
        existing_plugins = api_json("GET", f"{plugins_url}?size=1000").get("data", [])
        existing = next((plugin for plugin in existing_plugins if plugin.get("name") == "datakit"), None)
        if existing is None:
            created = api_json("POST", plugins_url, payload)
            configured.append({"route": route_name, "plugin_id": created["id"], "action": "created"})
        else:
            api_json("PUT", f"{base}/plugins/{existing['id']}", payload)
            configured.append({"route": route_name, "plugin_id": existing["id"], "action": "updated"})

    print(json.dumps({"configured": configured}, indent=2))


if __name__ == "__main__":
    main()
