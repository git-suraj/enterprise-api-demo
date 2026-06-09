#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


KONG_ADMIN_URL = os.environ.get("KONG_ADMIN_URL", "http://kong-cp:8001").rstrip("/")
KONG_ADMIN_TOKEN = os.environ.get("KONG_ADMIN_TOKEN", "").strip()
DEV_PORTAL_API_URL = os.environ.get("DEV_PORTAL_API_URL", "http://kong-cp:8004").rstrip("/")
DEMO_PORTAL_URL = os.environ.get("DEMO_PORTAL_URL", "http://localhost:8003/default").rstrip("/")
WORKSPACE = "default"
DEVELOPER_EMAIL = os.environ.get("DEV_PORTAL_DEVELOPER_EMAIL", "portal1@example.com")
DEVELOPER_PASSWORD = os.environ.get("DEV_PORTAL_DEVELOPER_PASSWORD", "portal1")

SERVICE_NAME = "svc-portal-showcase-orders"
ROUTE_NAME = "route-portal-showcase-orders"
ROUTE_PATH = "/portal/orders"
UPSTREAM_URL = "http://orders-east:9101"
SERVICE_TAGS = ["portal-showcase", "cicd-demo", "dev-portal"]
API_SPEC_SLUG = "partner-orders-api"
PORTAL_SPEC_PATH = f"specs/{API_SPEC_SLUG}.json"


def api_json(method: str, base_url: str, path: str, payload: dict | None = None) -> tuple[int, dict | list | None]:
    url = f"{base_url}{path}"
    headers = {"Accept": "application/json"}
    if base_url.startswith(KONG_ADMIN_URL) and KONG_ADMIN_TOKEN:
        headers["Kong-Admin-Token"] = KONG_ADMIN_TOKEN
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        parsed = json.loads(body) if body else None
        return exc.code, parsed
    except urllib.error.URLError as exc:
        raise SystemExit(f"{method} {url} failed: {exc.reason}") from exc


def portal_form(method: str, path: str, form: dict[str, str]) -> tuple[int, str]:
    url = f"{DEV_PORTAL_API_URL}/{WORKSPACE}{path}"
    headers = {"Accept": "application/json"}
    data = urllib.parse.urlencode(form).encode("utf-8")
    headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def expect(status: int, ok_statuses: set[int], context: str, body: dict | list | None = None) -> dict | list | None:
    if status not in ok_statuses:
        raise SystemExit(f"{context} failed with status {status}: {json.dumps(body)}")
    return body


def get_by_name(path_prefix: str, name: str) -> dict | None:
    status, body = api_json("GET", KONG_ADMIN_URL, f"{path_prefix}/{urllib.parse.quote(name, safe='')}")
    if status == 404:
        return None
    return expect(status, {200}, f"lookup {path_prefix} {name}", body)  # type: ignore[return-value]


def build_deck_state() -> dict:
    return {
        "_format_version": "3.0",
        "services": [
            {
                "name": SERVICE_NAME,
                "url": UPSTREAM_URL,
                "tags": SERVICE_TAGS,
                "routes": [
                    {
                        "name": ROUTE_NAME,
                        "paths": [ROUTE_PATH],
                        "methods": ["GET"],
                        "strip_path": False,
                        "tags": SERVICE_TAGS,
                    }
                ],
            }
        ],
        "plugins": [
            {
                "name": "key-auth",
                "service": SERVICE_NAME,
                "config": {
                    "key_names": ["apikey"],
                    "hide_credentials": False,
                    "run_on_preflight": True,
                },
                "tags": SERVICE_TAGS,
            },
            {
                "name": "application-registration",
                "service": SERVICE_NAME,
                "config": {
                    "display_name": "Partner Orders API",
                    "description": "Partner-facing Orders API for the Dev Portal onboarding showcase.",
                    "auto_approve": True,
                    "enable_proxy_with_consumer_credential": True,
                    "show_issuer": False,
                },
                "tags": SERVICE_TAGS,
            },
            {
                "name": "rate-limiting",
                "route": ROUTE_NAME,
                "config": {
                    "minute": 30,
                    "policy": "local",
                    "limit_by": "consumer",
                    "hide_client_headers": False,
                },
                "tags": SERVICE_TAGS,
            },
            {
                "name": "correlation-id",
                "route": ROUTE_NAME,
                "config": {
                    "header_name": "x-correlation-id",
                    "generator": "uuid#counter",
                    "echo_downstream": True,
                },
                "tags": SERVICE_TAGS,
            },
        ],
    }


def wait_for_admin_ready(timeout_seconds: int = 90) -> None:
    deadline = time.time() + timeout_seconds
    attempt = 1
    while time.time() < deadline:
        try:
            status, body = api_json("GET", KONG_ADMIN_URL, "/status")
            if status == 200:
                print(f"Kong Admin API is ready at {KONG_ADMIN_URL}")
                return
            print(f"Attempt {attempt}: Admin API returned {status}, retrying...")
        except SystemExit as exc:
            print(f"Attempt {attempt}: {exc}")
        attempt += 1
        time.sleep(2)
    raise SystemExit(f"Kong Admin API did not become ready at {KONG_ADMIN_URL} within {timeout_seconds} seconds")


def cmd_validate_spec(spec_path: str) -> None:
    with open(spec_path, "r", encoding="utf-8") as handle:
        spec = json.load(handle)

    if spec.get("openapi") != "3.0.3":
        raise SystemExit("OpenAPI version must be 3.0.3")
    title = (((spec.get("info") or {}).get("title")) or "").strip()
    version = (((spec.get("info") or {}).get("version")) or "").strip()
    paths = spec.get("paths") or {}
    if not title or not version or ROUTE_PATH not in paths:
        raise SystemExit("Spec must define info.title, info.version, and /portal/orders")

    print(f"Validated OpenAPI spec {spec_path}")
    print(f"API title: {title}")
    print(f"API version: {version}")
    print(f"Published path candidate: {ROUTE_PATH}")


def cmd_render_deck(output_path: str) -> None:
    rendered = build_deck_state()
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(rendered, handle, indent=2)
        handle.write("\n")

    print("Rendered decK state for portal showcase")
    print(
        "Equivalent CI/CD step: "
        f"deck gateway sync --kong-addr {KONG_ADMIN_URL} "
        f"--headers Kong-Admin-Token:{KONG_ADMIN_TOKEN or '<unset>'} "
        f"--select-tag portal-showcase {output_path}"
    )
    print(json.dumps(rendered, indent=2))


def cmd_sync_deck(input_path: str) -> None:
    with open(input_path, "r", encoding="utf-8") as handle:
        rendered = json.load(handle)
    if not rendered.get("services"):
        raise SystemExit("Rendered deck state does not contain any services")

    wait_for_admin_ready()
    command = [
        "deck",
        "gateway",
        "sync",
        "--kong-addr",
        KONG_ADMIN_URL,
        "--headers",
        f"Kong-Admin-Token:{KONG_ADMIN_TOKEN}",
        "--select-tag",
        "portal-showcase",
        input_path,
    ]
    print(f"Applying rendered decK state from {input_path}")
    print("Executing real decK command:")
    print(" ".join(command))
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line.rstrip("\n"))
    process.wait()
    if process.returncode != 0:
        raise SystemExit(f"deck gateway sync failed with exit code {process.returncode}")
    print(f"decK sync complete for {ROUTE_NAME}")


def cmd_prepare_portal() -> None:
    wait_for_admin_ready()
    status, body = api_json("PATCH", KONG_ADMIN_URL, f"/{WORKSPACE}/workspaces/{WORKSPACE}", {
        "config": {
            "portal": True,
            "portal_auth": "basic-auth",
            "portal_auto_approve": True,
            "portal_auth_conf": None,
            "portal_session_conf": {
                "secret": "portal-session-secret-change-me",
                "storage": "kong",
                "cookie_secure": False,
            },
        }
    })
    expect(status, {200}, "configure portal auth", body)
    print("Ensured Dev Portal auth is enabled")

    status, body = portal_form(
        "POST",
        "/register",
        {
            "meta": json.dumps({"full_name": "portal1"}),
            "email": DEVELOPER_EMAIL,
            "password": DEVELOPER_PASSWORD,
        },
    )
    lowered = body.lower()
    if status == 200:
        print(f"Created portal developer {DEVELOPER_EMAIL}")
    elif status in {400, 409} and ("already" in lowered or "exist" in lowered or "unique" in lowered):
        print(f"Portal developer {DEVELOPER_EMAIL} already exists")
    else:
        raise SystemExit(f"seed portal developer failed with status {status}: {body}")

    print("Portal preparation completed")


def upsert_portal_spec(spec_path: str) -> None:
    with open(spec_path, "r", encoding="utf-8") as handle:
        spec_contents = handle.read()

    existing = get_by_name("/files", PORTAL_SPEC_PATH)
    payload = {"path": PORTAL_SPEC_PATH, "contents": spec_contents}
    if existing is None:
        status, body = api_json("POST", KONG_ADMIN_URL, "/files", payload)
        expect(status, {201}, f"create portal spec file {PORTAL_SPEC_PATH}", body)
        print(f"Created portal spec file at {PORTAL_SPEC_PATH}")
    else:
        status, body = api_json(
            "PATCH",
            KONG_ADMIN_URL,
            f"/files/{urllib.parse.quote(PORTAL_SPEC_PATH, safe='')}",
            {"contents": spec_contents},
        )
        expect(status, {200}, f"update portal spec file {PORTAL_SPEC_PATH}", body)
        print(f"Updated portal spec file at {PORTAL_SPEC_PATH}")


def bind_spec_to_service() -> None:
    service = get_by_name("/services", SERVICE_NAME)
    if service is None:
        raise SystemExit(f"Gateway service {SERVICE_NAME} is missing; decK sync must run before portal publication")
    service_id = (service.get("id") if isinstance(service, dict) else None) or ""
    if not service_id:
        raise SystemExit(f"Gateway service {SERVICE_NAME} did not return an id")

    status, body = api_json(
        "GET",
        KONG_ADMIN_URL,
        f"/services/{urllib.parse.quote(service_id, safe='')}/document_objects",
    )
    parsed = expect(status, {200}, f"list document objects for {SERVICE_NAME}", body)
    existing = []
    if isinstance(parsed, dict):
        existing = parsed.get("data") or []
    elif isinstance(parsed, list):
        existing = parsed

    if any(item.get("path") == PORTAL_SPEC_PATH for item in existing if isinstance(item, dict)):
        print(f"Portal catalog already points {SERVICE_NAME} to {PORTAL_SPEC_PATH}")
        return

    status, body = api_json(
        "POST",
        KONG_ADMIN_URL,
        f"/services/{urllib.parse.quote(service_id, safe='')}/document_objects",
        {"path": PORTAL_SPEC_PATH},
    )
    expect(status, {200, 201}, f"bind portal spec {PORTAL_SPEC_PATH} to {SERVICE_NAME}", body)
    print(f"Published {SERVICE_NAME} into the Dev Portal catalog with {PORTAL_SPEC_PATH}")


def cmd_publish_portal(spec_path: str) -> None:
    wait_for_admin_ready()
    upsert_portal_spec(spec_path)
    bind_spec_to_service()
    print("Portal publication completed")


def cmd_summary() -> None:
    print("CI/CD onboarding run completed")
    print(f"Spec slug: {API_SPEC_SLUG}")
    print(f"Portal spec path: {PORTAL_SPEC_PATH}")
    print(f"Portal URL: {DEMO_PORTAL_URL}")
    print(f"Gateway URL: https://localhost:8443{ROUTE_PATH}")
    print(f"Portal login: {DEVELOPER_EMAIL} / {DEVELOPER_PASSWORD}")
    print("Published outcome:")
    print("  1. Tagged gateway resources synced with decK using --select-tag portal-showcase")
    print("  2. API spec uploaded into the Dev Portal file store")
    print("  3. Service published into the Dev Portal catalog")
    print("  4. Application registration enabled on the published service")
    print("Next manual steps:")
    print("  1. Log into the Dev Portal")
    print("  2. Open Partner Orders API")
    print("  3. Create an application")
    print("  4. Generate an API key")
    print(f"  5. Call GET https://localhost:8443{ROUTE_PATH} with header apikey: <generated-key>")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit(
            "usage: onboard_api_runner.py "
            "<validate-spec|render-deck|wait-admin|sync-deck|publish-portal|prepare-portal|summary> [args]"
        )

    command = argv[1]
    if command == "validate-spec":
        if len(argv) != 3:
            raise SystemExit("validate-spec requires a spec path")
        cmd_validate_spec(argv[2])
        return 0
    if command == "render-deck":
        if len(argv) != 3:
            raise SystemExit("render-deck requires an output path")
        cmd_render_deck(argv[2])
        return 0
    if command == "wait-admin":
        wait_for_admin_ready()
        return 0
    if command == "sync-deck":
        if len(argv) != 3:
            raise SystemExit("sync-deck requires an input path")
        cmd_sync_deck(argv[2])
        return 0
    if command == "publish-portal":
        if len(argv) != 3:
            raise SystemExit("publish-portal requires a spec path")
        cmd_publish_portal(argv[2])
        return 0
    if command == "prepare-portal":
        cmd_prepare_portal()
        return 0
    if command == "summary":
        cmd_summary()
        return 0

    raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
