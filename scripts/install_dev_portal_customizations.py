#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.error
import urllib.request


ADMIN_API_URL = os.environ.get("LOCAL_KONG_ADMIN_URL", "http://localhost:8001").rstrip("/")
ADMIN_TOKEN = os.environ.get("KONG_ADMIN_TOKEN", "").strip()
SCRIPT_TAG = '<script src="http://localhost:8080/static/portal-app-automation.js"></script>'
TARGET_PATHS = [
    "themes/base/layouts/system/create-app.html",
    "themes/base/layouts/system/applications.html",
    "themes/base/layouts/system/view-app.html",
]


def api_json(method: str, path: str, payload: dict | None = None) -> tuple[int, dict | None]:
    url = f"{ADMIN_API_URL}/{path.lstrip('/')}"
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


def inject_page_js(contents: str) -> str:
    if SCRIPT_TAG in contents:
        return contents
    if "{-page_js-}" in contents:
        prefix, _, suffix = contents.partition("{-page_js-}")
        return f"{prefix}{{-page_js-}}\n{SCRIPT_TAG}\n{{-page_js-}}{suffix}"
    return f'{contents.rstrip()}\n\n{{-page_js-}}\n{SCRIPT_TAG}\n{{-page_js-}}\n'


def main() -> int:
    changed = []
    for path in TARGET_PATHS:
        encoded_path = urllib.parse.quote(path, safe="")
        status, body = api_json("GET", f"files/{encoded_path}")
        if status != 200 or not isinstance(body, dict):
            raise SystemExit(f"Failed to fetch portal layout {path}: {status} {body}")

        updated_contents = inject_page_js(body.get("contents") or "")
        if updated_contents == (body.get("contents") or ""):
            continue

        status, patched = api_json("PATCH", f"files/{encoded_path}", {"contents": updated_contents})
        if status != 200:
            raise SystemExit(f"Failed to update portal layout {path}: {status} {patched}")
        changed.append(path)

    print(json.dumps({"changed": changed, "count": len(changed)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
