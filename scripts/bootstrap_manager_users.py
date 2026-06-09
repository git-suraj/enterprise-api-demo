#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from hashlib import sha1


ADMIN_API_URL = os.environ.get("LOCAL_KONG_ADMIN_URL", "http://localhost:8001").rstrip("/")
REGISTRATION_FILE = os.environ.get("MANAGER_REGISTRATION_FILE", "")
AUTOMATION_ADMIN_TOKEN = os.environ.get("KONG_ADMIN_TOKEN", "local-demo-admin-token")
POSTGRES_CONTAINER = os.environ.get("KONG_POSTGRES_CONTAINER", "kong-demo-postgres")
POSTGRES_DB = os.environ.get("KONG_PG_DATABASE", "kong")
POSTGRES_USER = os.environ.get("KONG_PG_USER", "kong")

WORKSPACES = [
    {
        "workspace": "team-a",
        "admin_workspace": "default",
        "username": "demo1",
        "password": "demo1",
        "email": "demo1@example.com",
        "role": "team-a-manager",
    },
    {
        "workspace": "team-b",
        "admin_workspace": "default",
        "username": "demo2",
        "password": "demo2",
        "email": "demo2@example.com",
        "role": "team-b-manager",
    },
]

GLOBAL_ADMINS = [
    {
        "username": "admin",
        "password": "admin",
        "email": "admin@example.com",
        "role": "platform-super-admin",
    }
]


def request(method: str, path: str, payload: dict | None = None, workspace: str | None = None, query: dict | None = None) -> tuple[int, dict | list | None]:
    url = f"{ADMIN_API_URL}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    body = None
    headers = {"Accept": "application/json"}
    if AUTOMATION_ADMIN_TOKEN:
        headers["Kong-Admin-Token"] = AUTOMATION_ADMIN_TOKEN
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if workspace:
        headers["Kong-Workspace"] = workspace

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode("utf-8")
            return resp.status, json.loads(data) if data else None
    except urllib.error.HTTPError as exc:
        data = exc.read().decode("utf-8")
        parsed = json.loads(data) if data else None
        return exc.code, parsed


def request_workspace_admin(username: str, workspace: str, *, query: dict | None = None) -> tuple[int, dict | list | None]:
    return request("GET", f"/{urllib.parse.quote(workspace, safe='')}/admins/{urllib.parse.quote(username, safe='')}", query=query)


def expect_ok(status: int, body: dict | list | None, *, ok_statuses: set[int], context: str) -> dict | list | None:
    if status not in ok_statuses:
        raise RuntimeError(f"{context} failed with status {status}: {json.dumps(body)}")
    return body


def get_workspace(name: str) -> dict | None:
    status, body = request("GET", f"/workspaces/{urllib.parse.quote(name, safe='')}")
    if status == 404:
        return None
    return expect_ok(status, body, ok_statuses={200}, context=f"get workspace {name}")


def ensure_workspace(name: str) -> None:
    if get_workspace(name):
        return
    status, body = request("POST", "/workspaces", {"name": name})
    expect_ok(status, body, ok_statuses={201, 409}, context=f"create workspace {name}")


def get_admin(username: str, workspace: str | None = None) -> dict | None:
    status, body = request("GET", f"/admins/{urllib.parse.quote(username, safe='')}", workspace=workspace)
    if status == 404:
        return None
    return expect_ok(status, body, ok_statuses={200}, context=f"get admin {username}")


def get_workspace_admin(username: str, workspace: str) -> dict | None:
    admin = get_admin(username, workspace)
    if admin is not None:
        return admin
    if workspace and workspace != "default":
        status, body = request_workspace_admin(username, workspace)
        if status == 404:
            return None
        return expect_ok(status, body, ok_statuses={200}, context=f"get workspace admin {username}")
    return None


def admin_workspace_for(admin_def: dict[str, str]) -> str:
    return admin_def.get("admin_workspace", admin_def.get("workspace", "default"))


def ensure_admin(username: str, email: str, workspace: str | None = None) -> None:
    if get_admin(username, workspace):
        return
    status, body = request(
        "POST",
        "/admins",
        {
            "username": username,
            "email": email,
            "rbac_token_enabled": True,
        },
        workspace=workspace,
    )
    expect_ok(status, body, ok_statuses={200, 201, 409}, context=f"create admin {username}")


def get_role(role_name: str, workspace: str) -> dict | None:
    status, body = request("GET", f"/rbac/roles/{urllib.parse.quote(role_name, safe='')}", workspace=workspace)
    if status == 404:
        return None
    return expect_ok(status, body, ok_statuses={200}, context=f"get role {role_name}")


def ensure_role(role_name: str, workspace: str, comment: str) -> None:
    if get_role(role_name, workspace):
        return
    status, body = request("POST", "/rbac/roles", {"name": role_name, "comment": comment}, workspace=workspace)
    expect_ok(status, body, ok_statuses={201, 409}, context=f"create role {role_name}")


def ensure_role_endpoint_permission(role_name: str, workspace_scope: str, role_workspace: str) -> None:
    status, body = request("GET", f"/rbac/roles/{urllib.parse.quote(role_name, safe='')}/endpoints", workspace=role_workspace)
    endpoints = expect_ok(status, body, ok_statuses={200}, context=f"list role endpoints for {role_name}")
    for item in endpoints.get("data", []):
        if item.get("endpoint") == "*" and item.get("workspace") == workspace_scope:
            actions = sorted(item.get("actions", []))
            if actions == ["create", "delete", "read", "update"]:
                return

    status, body = request(
        "POST",
        f"/rbac/roles/{urllib.parse.quote(role_name, safe='')}/endpoints",
        {
            "endpoint": "*",
            "workspace": workspace_scope,
            "actions": ["*"],
            "comment": f"Full access within {workspace_scope}",
        },
        workspace=role_workspace,
    )
    expect_ok(status, body, ok_statuses={201, 409}, context=f"grant endpoint permission for {role_name}")


def ensure_admin_role(username: str, role_name: str, workspace: str) -> None:
    status, body = request("GET", f"/admins/{urllib.parse.quote(username, safe='')}/roles", workspace=workspace)
    if status == 200:
        roles = expect_ok(status, body, ok_statuses={200}, context=f"list roles for {username}")
        if any(role.get("name") == role_name for role in roles.get("roles", [])):
            return
    elif status != 404:
        expect_ok(status, body, ok_statuses={200}, context=f"list roles for {username}")

    status, body = request(
        "POST",
        f"/admins/{urllib.parse.quote(username, safe='')}/roles",
        {"roles": role_name},
        workspace=workspace,
    )
    if status in {201, 409}:
        return
    if status == 400 and isinstance(body, dict) and "role not found" in body.get("message", ""):
        bind_admin_role_in_db(username, role_name)
        return
    expect_ok(status, body, ok_statuses={201, 409}, context=f"assign role {role_name} to {username}")


def run_sql(query: str, *, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker",
            "exec",
            POSTGRES_CONTAINER,
            "psql",
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DB,
            "-At",
            "-c",
            query,
        ],
        check=True,
        capture_output=capture_output,
        text=True,
    )


def workspace_id_for_name(workspace: str) -> str:
    result = run_sql(
        "SELECT id FROM workspaces "
        f"WHERE name = '{sql_escape(workspace)}' "
        "LIMIT 1;",
        capture_output=True,
    )
    value = result.stdout.strip()
    if not value:
        raise RuntimeError(f"workspace {workspace} not found in database")
    return value


def has_basic_auth_credential(username: str, workspace: str) -> bool:
    workspace_id = workspace_id_for_name(workspace)
    result = run_sql(
        "SELECT 1 FROM basicauth_credentials "
        f"WHERE username = '{sql_escape(username)}' "
        f"AND ws_id = '{sql_escape(workspace_id)}' "
        "LIMIT 1;",
        capture_output=True,
    )
    return result.stdout.strip() == "1"


def delete_basic_auth_credential(username: str, workspace: str) -> None:
    workspace_id = workspace_id_for_name(workspace)
    run_sql(
        "DELETE FROM basicauth_credentials "
        f"WHERE username = '{sql_escape(username)}' "
        f"AND ws_id = '{sql_escape(workspace_id)}';"
    )


def delete_all_basic_auth_credentials(username: str) -> None:
    run_sql(
        "DELETE FROM basicauth_credentials "
        f"WHERE username = '{sql_escape(username)}';"
    )


def activate_admin_if_registered(username: str) -> None:
    run_sql(
        "UPDATE admins "
        "SET status = 0 "
        "WHERE username = '{username}' "
        "AND EXISTS ("
        "  SELECT 1 "
        "  FROM basicauth_credentials b "
        "  WHERE b.consumer_id = admins.consumer_id"
        ");".format(username=sql_escape(username))
    )


def ensure_registered_password(username: str, email: str, password: str, workspace: str) -> None:
    admin = get_workspace_admin(username, workspace)
    if admin and admin.get("status") == 0:
        return

    delete_all_basic_auth_credentials(username)

    if not REGISTRATION_FILE:
        raise RuntimeError("MANAGER_REGISTRATION_FILE must be set for register mode")
    registrations = json.loads(open(REGISTRATION_FILE, "r", encoding="utf-8").read())
    token = registrations.get(username, {}).get("token")
    if not token:
        raise RuntimeError(f"missing registration token for {username}")

    status, body = request(
        "POST",
        "/admins/register",
        {
            "username": username,
            "email": email,
            "password": password,
            "token": token,
        },
    )
    if status in {200, 201}:
        activate_admin_if_registered(username)
        return

    activate_admin_if_registered(username)
    admin = get_workspace_admin(username, workspace)
    if admin and admin.get("status") == 0:
        return
    raise RuntimeError(f"register password for {username} failed with status {status}: {json.dumps(body)}")


def collect_registration_tokens(admin_targets: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    registrations: dict[str, dict[str, str]] = {}
    for target in admin_targets:
        username = target["username"]
        workspace = target.get("workspace")
        admin = get_workspace_admin(username, workspace or "default")
        if admin and admin.get("status") == 0:
            continue
        status, body = request(
            "GET",
            f"/admins/{urllib.parse.quote(username, safe='')}",
            workspace=workspace,
            query={"generate_register_url": "true"},
        )
        if status == 404 and workspace and workspace != "default":
            status, body = request_workspace_admin(
                username,
                workspace,
                query={"generate_register_url": "true"},
            )
        if status == 404 and workspace and workspace != "default":
            status, body = request(
                "GET",
                f"/admins/{urllib.parse.quote(username, safe='')}",
                query={"generate_register_url": "true"},
            )
        admin = expect_ok(status, body, ok_statuses={200}, context=f"generate register token for {username}")
        token = admin.get("token")
        email = admin.get("email")
        if not token or not email:
            raise RuntimeError(f"missing registration details for {username}")
        registrations[username] = {"token": token, "email": email}
    return registrations


def build_admin_targets() -> list[dict[str, str]]:
    targets = [{"username": admin_def["username"], "workspace": "default"} for admin_def in GLOBAL_ADMINS]
    targets.extend({"username": item["username"], "workspace": admin_workspace_for(item)} for item in WORKSPACES)
    return targets


def write_registration_tokens() -> None:
    if not REGISTRATION_FILE:
        raise RuntimeError("MANAGER_REGISTRATION_FILE must be set for register mode")
    registrations = collect_registration_tokens(build_admin_targets())
    with open(REGISTRATION_FILE, "w", encoding="utf-8") as handle:
        json.dump(registrations, handle)


def sql_escape(value: str) -> str:
    return value.replace("'", "''")


def seed_admin_api_token(username: str, token: str) -> None:
    ident = sha1(token.encode("utf-8")).hexdigest()[:5]
    sql = (
        "UPDATE rbac_users "
        f"SET user_token = '{sql_escape(token)}', user_token_ident = '{ident}' "
        "FROM admins "
        "WHERE admins.rbac_user_id = rbac_users.id "
        f"AND admins.username = '{sql_escape(username)}';"
    )
    subprocess.run(
        [
            "docker",
            "exec",
            POSTGRES_CONTAINER,
            "psql",
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DB,
            "-c",
            sql,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def update_admin_workspace_binding(username: str, workspace: str) -> None:
    sql = (
        "UPDATE rbac_users "
        "SET ws_id = (SELECT id FROM workspaces WHERE name = '{workspace}') "
        "FROM admins "
        "WHERE admins.rbac_user_id = rbac_users.id "
        "AND admins.username = '{username}';"
    ).format(workspace=sql_escape(workspace), username=sql_escape(username))
    subprocess.run(
        [
            "docker",
            "exec",
            POSTGRES_CONTAINER,
            "psql",
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DB,
            "-c",
            sql,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def update_role_workspace_binding(role_name: str, workspace: str) -> None:
    check_sql = (
        "SELECT 1 "
        "FROM rbac_roles "
        "WHERE name = '{role_name}' "
        "AND ws_id = (SELECT id FROM workspaces WHERE name = '{workspace}') "
        "LIMIT 1;"
    ).format(workspace=sql_escape(workspace), role_name=sql_escape(role_name))
    check = subprocess.run(
        [
            "docker",
            "exec",
            POSTGRES_CONTAINER,
            "psql",
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DB,
            "-At",
            "-c",
            check_sql,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    if check.stdout.strip() == "1":
        return

    sql = (
        "UPDATE rbac_roles "
        "SET ws_id = (SELECT id FROM workspaces WHERE name = '{workspace}') "
        "WHERE name = '{role_name}' "
        "AND ws_id = (SELECT id FROM workspaces WHERE name = 'default');"
    ).format(workspace=sql_escape(workspace), role_name=sql_escape(role_name))
    subprocess.run(
        [
            "docker",
            "exec",
            POSTGRES_CONTAINER,
            "psql",
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DB,
            "-c",
            sql,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def bind_admin_role_in_db(username: str, role_name: str) -> None:
    sql = (
        "INSERT INTO rbac_user_roles (user_id, role_id, role_source) "
        "SELECT admins.rbac_user_id, ("
        "  SELECT r.id "
        "  FROM rbac_roles r "
        "  WHERE r.name = '{role_name}' "
        "    AND (r.ws_id = rbac_users.ws_id OR r.ws_id IS NULL) "
        "  ORDER BY CASE WHEN r.ws_id = rbac_users.ws_id THEN 0 ELSE 1 END "
        "  LIMIT 1"
        "), 'local' "
        "FROM admins "
        "JOIN rbac_users ON rbac_users.id = admins.rbac_user_id "
        "WHERE admins.username = '{username}' "
        "AND NOT EXISTS ("
        "  SELECT 1 FROM rbac_user_roles "
        "  WHERE user_id = admins.rbac_user_id "
        "    AND role_id = ("
        "      SELECT r.id "
        "      FROM rbac_roles r "
        "      WHERE r.name = '{role_name}' "
        "        AND (r.ws_id = rbac_users.ws_id OR r.ws_id IS NULL) "
        "      ORDER BY CASE WHEN r.ws_id = rbac_users.ws_id THEN 0 ELSE 1 END "
        "      LIMIT 1"
        "    )"
        ");"
    ).format(role_name=sql_escape(role_name), username=sql_escape(username))
    subprocess.run(
        [
            "docker",
            "exec",
            POSTGRES_CONTAINER,
            "psql",
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DB,
            "-c",
            sql,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def delete_admin_if_present(username: str) -> None:
    if not get_admin(username):
        return
    status, body = request("DELETE", f"/admins/{urllib.parse.quote(username, safe='')}")
    expect_ok(status, body, ok_statuses={204}, context=f"delete admin {username}")


def delete_workspace_admin_if_present(username: str, workspace: str) -> None:
    if workspace == "default":
        return
    workspace_admin = get_workspace_admin(username, workspace)
    if not workspace_admin:
        return
    belong_workspace = (workspace_admin.get("belong_workspace") or {}).get("name")
    if belong_workspace != workspace:
        return
    status, body = request("DELETE", f"/{urllib.parse.quote(workspace, safe='')}/admins/{urllib.parse.quote(username, safe='')}")
    expect_ok(status, body, ok_statuses={204}, context=f"delete workspace admin {username}")


def prepare() -> int:
    ensure_role("platform-super-admin", "default", "Global Manager access across all workspaces")
    ensure_role_endpoint_permission("platform-super-admin", "*", "default")

    for workspace_def in WORKSPACES:
        workspace = workspace_def["workspace"]
        ensure_workspace(workspace)
        ensure_role(workspace_def["role"], workspace, f"Full Manager access for {workspace}")
        ensure_role_endpoint_permission(workspace_def["role"], workspace, workspace)
        update_role_workspace_binding(workspace_def["role"], workspace)

    for admin_def in GLOBAL_ADMINS:
        ensure_admin(admin_def["username"], admin_def["email"], "default")
        ensure_admin_role(admin_def["username"], admin_def["role"], "default")

    for workspace_def in WORKSPACES:
        delete_workspace_admin_if_present(workspace_def["username"], workspace_def["workspace"])
        ensure_admin(workspace_def["username"], workspace_def["email"], admin_workspace_for(workspace_def))
        ensure_admin_role(workspace_def["username"], workspace_def["role"], workspace_def["workspace"])

    delete_admin_if_present("probe-admin")
    seed_admin_api_token("admin", AUTOMATION_ADMIN_TOKEN)

    print("Manager users, workspaces, and automation token are prepared")
    return 0


def register() -> int:
    write_registration_tokens()

    for admin_def in GLOBAL_ADMINS:
        ensure_registered_password(admin_def["username"], admin_def["email"], admin_def["password"], "default")

    for workspace_def in WORKSPACES:
        ensure_registered_password(
            workspace_def["username"],
            workspace_def["email"],
            workspace_def["password"],
            admin_workspace_for(workspace_def),
        )

    print("Manager passwords are registered")
    return 0


if __name__ == "__main__":
    try:
        mode = sys.argv[1] if len(sys.argv) > 1 else "prepare"
        if mode == "prepare":
            raise SystemExit(prepare())
        if mode == "register":
            raise SystemExit(register())
        raise SystemExit(f"unknown mode: {mode}")
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
