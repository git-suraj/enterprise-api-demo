#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


ADMIN_API_URL = os.environ.get("LOCAL_KONG_ADMIN_URL", "http://localhost:8001").rstrip("/")
ADMIN_TOKEN = os.environ.get("KONG_ADMIN_TOKEN", "").strip()
WORKSPACE = os.environ.get("DEV_PORTAL_WORKSPACE", "default").strip() or "default"


def api_json(method: str, path: str, payload: dict | None = None) -> tuple[int, dict | None]:
    url = f"{ADMIN_API_URL}{path}"
    headers = {"Accept": "application/json"}
    if ADMIN_TOKEN:
        headers["Kong-Admin-Token"] = ADMIN_TOKEN
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        parsed = json.loads(body) if body else None
        return exc.code, parsed


def main() -> int:
    path = f"/{WORKSPACE}/workspaces/{WORKSPACE}"
    status, body = api_json("GET", path)
    if status != 200 or not isinstance(body, dict):
        raise SystemExit(f"Failed to fetch workspace {WORKSPACE}: {status} {body}")

    config = body.get("config") or {}
    if config.get("portal") is True:
        print(json.dumps({"workspace": WORKSPACE, "portal": True, "action": "unchanged"}))
        return 0

    status, body = api_json("PATCH", path, {"config": {"portal": True}})
    if status != 200:
        raise SystemExit(f"Failed to enable Dev Portal for workspace {WORKSPACE}: {status} {body}")

    print(json.dumps({"workspace": WORKSPACE, "portal": True, "action": "enabled"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
