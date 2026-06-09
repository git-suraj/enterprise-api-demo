#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


PORTAL_API_URL = os.environ.get("DEV_PORTAL_API_URL", "http://localhost:8004").rstrip("/")
WORKSPACE = os.environ.get("DEV_PORTAL_WORKSPACE", "default").strip() or "default"
DEVELOPER_FULL_NAME = os.environ.get("DEV_PORTAL_DEVELOPER_FULL_NAME", "portal1")
DEVELOPER_EMAIL = os.environ.get("DEV_PORTAL_DEVELOPER_EMAIL", "portal1@example.com")
DEVELOPER_PASSWORD = os.environ.get("DEV_PORTAL_DEVELOPER_PASSWORD", "portal1")


def request(method: str, path: str, form: dict[str, str] | None = None) -> tuple[int, str]:
    url = f"{PORTAL_API_URL}/{WORKSPACE}{path}"
    headers = {"Accept": "application/json"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def main() -> int:
    status, body = request(
        "POST",
        "/register",
        {
            "meta": json.dumps({"full_name": DEVELOPER_FULL_NAME}),
            "email": DEVELOPER_EMAIL,
            "password": DEVELOPER_PASSWORD,
        },
    )
    if status == 200:
        print(json.dumps({"workspace": WORKSPACE, "developer": DEVELOPER_EMAIL, "action": "created"}))
        return 0

    lowered = body.lower()
    if status in {400, 409} and ("already" in lowered or "exist" in lowered or "unique" in lowered):
        print(json.dumps({"workspace": WORKSPACE, "developer": DEVELOPER_EMAIL, "action": "unchanged"}))
        return 0

    raise SystemExit(f"Failed to seed Dev Portal developer {DEVELOPER_EMAIL}: {status} {body}")


if __name__ == "__main__":
    raise SystemExit(main())
