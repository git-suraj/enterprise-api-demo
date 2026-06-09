#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys


KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "kong-demo")
KEYCLOAK_ALLOWED_ROLE = os.environ.get("KEYCLOAK_ALLOWED_ROLE", "api-access")
AD_PROTECTED_API_TENANT_ID = os.environ.get("AD_PROTECTED_API_TENANT_ID", "").strip()
AD_PROTECTED_API_AUDIENCE = os.environ.get("AD_PROTECTED_API_AUDIENCE", "").strip()
AD_CONSUMER1_CLIENT_ID = os.environ.get("AD_CONSUMER1_CLIENT_ID", "").strip()
AD_CONSUMER2_CLIENT_ID = os.environ.get("AD_CONSUMER2_CLIENT_ID", "").strip()


def service(name, host, port, path="/", *, routes=None, plugins=None, **extra):
    item = {
        "name": name,
        "host": host,
        "port": port,
        "protocol": "http",
        "path": path,
    }
    if routes:
        item["routes"] = routes
    if plugins:
        item["plugins"] = plugins
    item.update(extra)
    return item


def route(name, paths, methods, *, plugins=None, headers=None, protocols=None, **extra):
    item = {
        "name": name,
        "paths": paths,
        "methods": methods,
        "protocols": protocols or ["http", "https"],
        "strip_path": False,
    }
    if headers:
        item["headers"] = headers
    if plugins:
        item["plugins"] = plugins
    item.update(extra)
    return item


def plugin(name, config):
    return {"name": name, "enabled": True, "config": config}


def key_auth_consumer(username, custom_id, key, *, plugins=None, acls=None):
    item = {
        "username": username,
        "custom_id": custom_id,
        "keyauth_credentials": [{"key": key}],
    }
    if plugins:
        item["plugins"] = plugins
    if acls:
        item["acls"] = [{"group": group} for group in acls]
    return item


def observability_plugins():
    access = """
kong.service.request.enable_buffering()
kong.ctx.shared.obs_request_headers = kong.request.get_headers(1000) or {}
local body, err = kong.request.get_raw_body()
if body ~= nil then
  kong.ctx.shared.obs_request_body = body
else
  kong.ctx.shared.obs_request_body = ""
end

local request_id = kong.ctx.shared.obs_request_headers["x-request-id"]
  or kong.ctx.shared.obs_request_headers["X-Request-Id"]

local span = kong.tracing.active_span()
if span and request_id then
  span:set_attribute("request.id", request_id)
end
""".strip()

    body_filter = """
local body = kong.response.get_raw_body()
if body ~= nil then
  kong.ctx.shared.obs_response_body = body
end
""".strip()

    log = """
local serialized = kong.log.serialize()
local request_headers = kong.ctx.shared.obs_request_headers or {}
local request_id = request_headers["x-request-id"]
  or request_headers["X-Request-Id"]
  or (serialized.request and serialized.request.id)

local span = kong.tracing.active_span()
if span then
  if request_id then
    span:set_attribute("request.id", request_id)
  end

  if serialized.request and serialized.request.id then
    span:set_attribute("kong.request.id", serialized.request.id)
  end
end
""".strip()

    return [
        plugin(
            "post-function",
            {
                "access": [access],
                "body_filter": [body_filter],
                "log": [log],
            },
        ),
        plugin(
            "opentelemetry",
            {
                "traces_endpoint": "http://otel-collector:4318/v1/traces",
                "logs_endpoint": "http://otel-collector:4318/v1/logs",
                "sampling_rate": 1,
                "resource_attributes": {
                    "service.name": "kong-enterprise",
                    "service.namespace": "enterprise-api-demo",
                    "deployment.environment": "local-onprem-demo",
                },
                "access_logs": {
                    "endpoint": "http://otel-collector:4318/v1/logs",
                    "custom_attributes_by_lua": {
                        "request_id": """local headers = kong.ctx.shared.obs_request_headers or {}
local serialized = kong.log.serialize()
return headers["x-request-id"] or headers["X-Request-Id"] or serialized.request.id""",
                        "trace_id": """local serialized = kong.log.serialize()
if type(serialized.trace_id) == "table" then
  return serialized.trace_id.w3c or serialized.trace_id.datadog
end
return serialized.trace_id""",
                        "consumer_name": """local serialized = kong.log.serialize()
if serialized.consumer and serialized.consumer.username then
  return serialized.consumer.username
end
return "anonymous" """,
                        "service_name_extracted": """local serialized = kong.log.serialize()
return serialized.service and serialized.service.name or "unmatched" """,
                        "route_name": """local serialized = kong.log.serialize()
return serialized.route and serialized.route.name or "unmatched" """,
                        "status_code": "return kong.response.get_status()",
                        "end_to_end_latency_ms": """local serialized = kong.log.serialize()
return serialized.latencies and serialized.latencies.request or nil""",
                        "kong_latency_ms": """local serialized = kong.log.serialize()
return serialized.latencies and serialized.latencies.kong or nil""",
                        "upstream_latency_ms": """local serialized = kong.log.serialize()
return serialized.latencies and serialized.latencies.proxy or nil""",
                        "response_source": """local serialized = kong.log.serialize()
return serialized.source or nil""",
                        "request_headers": """local cjson = require("cjson.safe")
return cjson.encode(kong.ctx.shared.obs_request_headers or {})""",
                        "request.body": "return kong.ctx.shared.obs_request_body",
                        "response_headers": """local cjson = require("cjson.safe")
return cjson.encode(kong.response.get_headers(1000) or {})""",
                        "response.body": "return kong.ctx.shared.obs_response_body",
                        "crypto_algorithm": "return kong.ctx.shared.crypto_algorithm",
                        "crypto_encrypted_request_payload": "return kong.ctx.shared.crypto_encrypted_request_payload",
                        "crypto_decrypted_request_payload": "return kong.ctx.shared.crypto_decrypted_request_payload",
                        "crypto_plain_response_payload": "return kong.ctx.shared.crypto_plain_response_payload",
                        "crypto_encrypted_response_payload": "return kong.ctx.shared.crypto_encrypted_response_payload",
                    },
                },
            },
        ),
    ]


def upstream(name, targets, *, weighted):
    default_weight = 30 if weighted else 100
    second_weight = 70 if weighted else 100
    return {
        "name": name,
        "algorithm": "round-robin",
        "slots": 10000,
        "use_srv_name": False,
        "healthchecks": {
            "active": {
                "concurrency": 10,
                "http_path": "/health",
                "timeout": 1,
                "type": "http",
                "healthy": {
                    "http_statuses": [200],
                    "interval": 2,
                    "successes": 2,
                },
                "unhealthy": {
                    "http_failures": 2,
                    "http_statuses": [429, 500, 501, 502, 503, 504, 505],
                    "interval": 2,
                    "tcp_failures": 2,
                    "timeouts": 2,
                },
            },
            "passive": {
                "type": "http",
                "healthy": {
                    "http_statuses": [
                        200, 201, 202, 203, 204, 205, 206, 207, 208, 226,
                        300, 301, 302, 303, 304, 305, 306, 307, 308,
                    ],
                    "successes": 0,
                },
                "unhealthy": {
                    "http_failures": 2,
                    "http_statuses": [429, 500, 503, 504],
                    "tcp_failures": 2,
                    "timeouts": 2,
                },
            },
            "threshold": 0,
        },
        "targets": [
            {"target": targets[0], "weight": default_weight},
            {"target": targets[1], "weight": second_weight},
        ],
    }


def keycloak_oidc_plugin():
    return plugin(
        "openid-connect",
        {
            "issuer": f"http://keycloak:8080/realms/{KEYCLOAK_REALM}",
            "auth_methods": ["bearer"],
            "bearer_token_param_type": ["header"],
            "consumer_claims": [["azp"]],
            "consumer_by": ["custom_id"],
            "roles_claim": ["realm_access", "roles"],
            "roles_required": [KEYCLOAK_ALLOWED_ROLE],
            "verify_parameters": False,
        },
    )


def maybe_azure_entities(services, consumers):
    if not all(
        [
            AD_PROTECTED_API_TENANT_ID,
            AD_PROTECTED_API_AUDIENCE,
            AD_CONSUMER1_CLIENT_ID,
            AD_CONSUMER2_CLIENT_ID,
        ]
    ):
        return

    azure_plugin = plugin(
        "openid-connect",
        {
            "issuer": f"https://login.microsoftonline.com/{AD_PROTECTED_API_TENANT_ID}/.well-known/openid-configuration",
            "auth_methods": ["bearer"],
            "bearer_token_param_type": ["header"],
            "audience_claim": ["aud"],
            "audience_required": [AD_PROTECTED_API_AUDIENCE],
            "issuers_allowed": [f"https://sts.windows.net/{AD_PROTECTED_API_TENANT_ID}/"],
            "consumer_claims": [["appid"]],
            "consumer_by": ["custom_id"],
            "verify_parameters": False,
        },
    )

    services.append(
        service(
            "svc-orders-auth-azure",
            "orders-east",
            9101,
            routes=[
                route(
                    "route-orders-auth-azure",
                    ["/orders/auth/azure"],
                    ["GET"],
                    plugins=[azure_plugin],
                )
            ],
        )
    )
    consumers.extend(
        [
            {"username": "azure-ad-consumer-1", "custom_id": AD_CONSUMER1_CLIENT_ID},
            {"username": "azure-ad-consumer-2", "custom_id": AD_CONSUMER2_CLIENT_ID},
        ]
    )


def build_state():
    services = [
        service(
            "svc-orders-header-east",
            "orders-east",
            9101,
            routes=[
                route(
                    "route-orders-header-east",
                    ["/orders"],
                    ["GET"],
                    headers={"x-region": ["east"]},
                )
            ],
        ),
        service(
            "svc-orders-header-west",
            "orders-west",
            9102,
            routes=[
                route(
                    "route-orders-header-west",
                    ["/orders"],
                    ["GET"],
                    headers={"x-region": ["west"]},
                )
            ],
        ),
        service(
            "svc-orders-header-missing-region",
            "orders-east",
            9101,
            routes=[
                route(
                    "route-orders-header-catchall",
                    ["/orders"],
                    ["GET"],
                    plugins=[
                        plugin(
                            "request-termination",
                            {
                                "status_code": 400,
                                "content_type": "application/json",
                                "body": json.dumps(
                                    {
                                        "message": "Missing required x-region header.",
                                        "allowed_values": ["east", "west"],
                                        "policy": "orders-header-missing-region-policy",
                                    }
                                ),
                            },
                        )
                    ],
                )
            ],
        ),
        service(
            "svc-orders-rate-anonymous",
            "orders-east",
            9101,
            plugins=[
                plugin(
                    "rate-limiting-advanced",
                    {
                        "limit": [20],
                        "window_size": [30],
                        "window_type": "fixed",
                        "strategy": "local",
                        "namespace": "orders-rate-anonymous",
                        "identifier": "ip",
                        "hide_client_headers": False,
                    },
                )
            ],
            routes=[route("route-orders-rate-anonymous", ["/orders/rate/anonymous"], ["GET"])],
        ),
        service(
            "svc-orders-rate-consumer",
            "orders-east",
            9101,
            plugins=[
                plugin(
                    "key-auth",
                    {
                        "key_names": ["apikey"],
                        "hide_credentials": False,
                    },
                )
            ],
            routes=[route("route-orders-rate-consumer", ["/orders/rate/consumer"], ["GET"])],
        ),
        service(
            "svc-orders-resilience-weighted",
            "upstream-orders-weighted",
            80,
            retries=1,
            connect_timeout=1000,
            read_timeout=5000,
            write_timeout=5000,
            routes=[route("route-orders-resilience-weighted", ["/orders/resilience/weighted"], ["GET"])],
        ),
        service(
            "svc-orders-circuit-breaker",
            "upstream-orders-circuit-breaker",
            80,
            retries=1,
            connect_timeout=1000,
            read_timeout=5000,
            write_timeout=5000,
            routes=[route("route-orders-circuit-breaker", ["/orders/resilience/circuit-breaker"], ["GET"])],
        ),
        service(
            "svc-orders-auth-keycloak",
            "orders-east",
            9101,
            routes=[
                route(
                    "route-orders-auth-keycloak",
                    ["/orders/auth/keycloak"],
                    ["GET"],
                    plugins=[keycloak_oidc_plugin()],
                )
            ],
        ),
        service(
            "svc-orders-ip-restriction",
            "orders-east",
            9101,
            routes=[
                route(
                    "route-orders-ip-restriction",
                    ["/orders/network/ip"],
                    ["GET"],
                    plugins=[plugin("ip-restriction", {"allow": ["10.10.10.0/24"], "deny": ["10.10.10.66"]})],
                )
            ],
        ),
        service(
            "svc-orders-schema-validation",
            "orders-east",
            9101,
            routes=[
                route(
                    "route-orders-schema-validation",
                    ["/orders/validate/schema"],
                    ["POST"],
                    plugins=[
                        plugin(
                            "request-validator",
                            {
                                "version": "kong",
                                "allowed_content_types": ["application/json"],
                                "body_schema": json.dumps(
                                    [
                                        {"orderId": {"type": "string", "required": True, "len_min": 1}},
                                        {"amount": {"type": "number", "required": True}},
                                        {"currency": {"type": "string", "required": True, "one_of": ["USD", "INR"]}},
                                    ]
                                ),
                                "parameter_schema": [
                                    {
                                        "name": "channel",
                                        "in": "query",
                                        "required": True,
                                        "schema": json.dumps({"type": "string", "enum": ["web", "mobile"]}),
                                        "style": "form",
                                        "explode": True,
                                    },
                                    {
                                        "name": "x-order-source",
                                        "in": "header",
                                        "required": True,
                                        "schema": json.dumps({"type": "string", "enum": ["portal", "partner"]}),
                                        "style": "simple",
                                        "explode": False,
                                    },
                                ],
                            },
                        )
                    ],
                )
            ],
        ),
        service(
            "svc-orders-request-size",
            "orders-east",
            9101,
            routes=[
                route(
                    "route-orders-request-size",
                    ["/orders/limits/request-size"],
                    ["POST"],
                    plugins=[plugin("request-size-limiting", {"allowed_payload_size": 2, "size_unit": "kilobytes"})],
                )
            ],
        ),
        service(
            "svc-datakit-fallback",
            "datakit-api1",
            9401,
            path="/datakit/api1/fallback",
            routes=[
                route(
                    "route-datakit-fallback",
                    ["/orders/datakit/fallback"],
                    ["GET"],
                    plugins=[keycloak_oidc_plugin()],
                )
            ],
        ),
        service(
            "svc-datakit-combine",
            "datakit-api1",
            9401,
            path="/datakit/api1/accounts",
            routes=[
                route(
                    "route-datakit-combine",
                    ["/orders/datakit/combine"],
                    ["GET"],
                    plugins=[keycloak_oidc_plugin()],
                )
            ],
        ),
        service(
            "svc-datakit-cache",
            "datakit-api1",
            9401,
            path="/datakit/api1/cache-source",
            routes=[
                route(
                    "route-datakit-cache",
                    ["/orders/datakit/cache"],
                    ["GET"],
                    plugins=[keycloak_oidc_plugin()],
                )
            ],
        ),
        service(
            "svc-orders-payload-crypto",
            "orders-east",
            9101,
            routes=[
                route(
                    "route-orders-payload-crypto",
                    ["/orders/security/payload-crypto"],
                    ["POST"],
                    plugins=[
                        plugin(
                            "payload-crypto-demo",
                            {
                                "algorithm": "AES/CBC/PKCS5Padding",
                                "gateway_private_key_path": "/crypto/gateway_private.pem",
                                "client_public_key_path": "/crypto/client_public.pem",
                                "gateway_private_key_passphrase_env": "CRYPTO_GATEWAY_PRIVATE_KEY_PASSPHRASE",
                            },
                        )
                    ],
                )
            ],
        ),
        service(
            "svc-orders-injection-protection",
            "orders-east",
            9101,
            routes=[
                route(
                    "route-orders-injection-query",
                    ["/orders/security/injection/query"],
                    ["GET"],
                    plugins=[
                        plugin(
                            "injection-protection",
                            {
                                "injection_types": ["sql"],
                                "locations": ["path_and_query"],
                                "enforcement_mode": "block",
                                "error_status_code": 400,
                                "error_message": "Bad Request",
                            },
                        )
                    ],
                ),
                route(
                    "route-orders-injection-body",
                    ["/orders/security/injection/body"],
                    ["POST"],
                    plugins=[
                        plugin(
                            "injection-protection",
                            {
                                "injection_types": ["sql"],
                                "locations": ["body"],
                                "enforcement_mode": "block",
                                "error_status_code": 400,
                                "error_message": "Bad Request",
                            },
                        )
                    ],
                ),
                route(
                    "route-orders-injection-headers",
                    ["/orders/security/injection/headers"],
                    ["GET"],
                    plugins=[
                        plugin(
                            "injection-protection",
                            {
                                "injection_types": ["sql"],
                                "locations": ["headers"],
                                "enforcement_mode": "block",
                                "error_status_code": 400,
                                "error_message": "Bad Request",
                            },
                        )
                    ],
                ),
            ],
        ),
        service(
            "svc-orders-transport-security",
            "orders-east",
            9101,
            routes=[
                route(
                    "route-orders-http-blocked",
                    ["/orders/transport/http-blocked"],
                    ["GET"],
                    protocols=["https"],
                    https_redirect_status_code=426,
                ),
                route(
                    "route-orders-http-redirect",
                    ["/orders/transport/http-redirect"],
                    ["GET"],
                    protocols=["https"],
                    https_redirect_status_code=308,
                ),
            ],
        ),
        service(
            "svc-orders-version-v1",
            "orders-v1",
            9301,
            routes=[
                route("route-orders-version-path-v1", ["/api/v1/orders"], ["GET"]),
                route(
                    "route-orders-version-header-v1",
                    ["/orders/version/header"],
                    ["GET"],
                    headers={"x-api-version": ["v1"]},
                ),
            ],
        ),
        service(
            "svc-orders-version-v2",
            "orders-v2",
            9302,
            routes=[
                route("route-orders-version-path-v2", ["/api/v2/orders"], ["GET"]),
                route(
                    "route-orders-version-header-v2",
                    ["/orders/version/header"],
                    ["GET"],
                    headers={"x-api-version": ["v2"]},
                ),
            ],
        ),
        service(
            "svc-orders-canary-primary",
            "orders-v1",
            9301,
            routes=[
                route(
                    "route-orders-canary-40",
                    ["/orders/canary/40"],
                    ["GET"],
                    plugins=[plugin("canary", {"upstream_host": "orders-v2", "upstream_port": 9302, "percentage": 40, "hash": "none", "steps": 100})],
                ),
                route(
                    "route-orders-canary-time",
                    ["/orders/canary/time"],
                    ["GET"],
                    plugins=[plugin("canary", {"upstream_host": "orders-v2", "upstream_port": 9302, "hash": "none", "steps": 20, "duration": 120})],
                ),
                route(
                    "route-orders-canary-header",
                    ["/orders/canary/header"],
                    ["GET"],
                    plugins=[plugin("canary", {"upstream_host": "orders-v2", "upstream_port": 9302, "hash": "none", "steps": 100, "percentage": 0, "canary_by_header_name": "x-canary-version"})],
                ),
                route(
                    "route-orders-canary-consumer",
                    ["/orders/canary/consumer"],
                    ["GET"],
                    plugins=[
                        plugin("key-auth", {"key_names": ["apikey"], "hide_credentials": False}),
                        plugin("acl", {"allow": ["canary-allow", "standard-access"], "hide_groups_header": True, "include_consumer_groups": True}),
                        plugin("canary", {"upstream_host": "orders-v2", "upstream_port": 9302, "canary_by_header_name": "x-canary-version", "hash": "none", "steps": 100, "percentage": 0}),
                    ],
                ),
            ],
        ),
        service(
            "svc-orders-deprecation-v1",
            "orders-v1",
            9301,
            routes=[
                route(
                    "route-orders-deprecation-v1",
                    ["/orders/deprecation/v1"],
                    ["GET"],
                    plugins=[
                        plugin(
                            "response-transformer",
                            {
                                "add": {
                                    "headers": [
                                        "Deprecation:true",
                                        "Sunset:Tue, 30 Jun 2026 23:59:59 GMT",
                                        "Link:</api/v2/orders>; rel=\"successor-version\"",
                                        "Warning:299 - \"API v1 is deprecated; migrate to v2\"",
                                    ]
                                }
                            },
                        )
                    ],
                ),
                route(
                    "route-orders-deprecation-sunset",
                    ["/orders/deprecation/v1/sunset"],
                    ["GET"],
                    plugins=[
                        plugin(
                            "request-termination",
                            {
                                "status_code": 410,
                                "content_type": "application/json",
                                "body": json.dumps(
                                    {
                                        "message": "API v1 has passed its sunset date and is no longer available.",
                                        "successor_version": "/orders/deprecation/v2",
                                        "deprecation_policy": "orders-v1-sunset",
                                    }
                                ),
                            },
                        )
                    ],
                ),
            ],
        ),
        service(
            "svc-orders-deprecation-v2",
            "orders-v2",
            9302,
            routes=[route("route-orders-deprecation-v2", ["/orders/deprecation/v2"], ["GET"])],
        ),
    ]

    consumers = [
        key_auth_consumer(
            "consumer-gold",
            "consumer-gold",
            "key-consumer-gold",
            plugins=[
                plugin(
                    "rate-limiting-advanced",
                    {
                        "limit": [10],
                        "window_size": [30],
                        "window_type": "fixed",
                        "strategy": "local",
                        "namespace": "consumer-gold-rate-limit",
                        "identifier": "consumer",
                        "hide_client_headers": False,
                    },
                )
            ],
        ),
        key_auth_consumer(
            "consumer-standard",
            "consumer-standard",
            "key-consumer-standard",
            plugins=[
                plugin(
                    "rate-limiting-advanced",
                    {
                        "limit": [5],
                        "window_size": [30],
                        "window_type": "fixed",
                        "strategy": "local",
                        "namespace": "consumer-standard-rate-limit",
                        "identifier": "consumer",
                        "hide_client_headers": False,
                    },
                )
            ],
        ),
        {"username": "keycloak-consumer-1", "custom_id": "consumer-1"},
        {"username": "keycloak-consumer-2", "custom_id": "consumer-2"},
        key_auth_consumer("consumer-pilot", "consumer-pilot", "key-consumer-pilot", acls=["canary-allow"]),
        key_auth_consumer(
            "consumer-standard-lifecycle",
            "consumer-standard-lifecycle",
            "key-consumer-standard-lifecycle",
            acls=["standard-access"],
        ),
    ]

    maybe_azure_entities(services, consumers)

    return {
        "_format_version": "3.0",
        "_transform": True,
        "plugins": observability_plugins(),
        "upstreams": [
            upstream("upstream-orders-weighted", ["orders-instance-1:9201", "orders-instance-2:9202"], weighted=True),
            upstream("upstream-orders-circuit-breaker", ["orders-instance-1:9201", "orders-instance-2:9202"], weighted=False),
        ],
        "services": services,
        "consumers": consumers,
    }


def main():
    json.dump(build_state(), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
