#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time


CONTAINER = os.environ.get("KEYCLOAK_CONTAINER_NAME", "kong-demo-keycloak")
ADMIN_USERNAME = os.environ.get("KEYCLOAK_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin")
REALM = os.environ.get("KEYCLOAK_REALM", "kong-demo")
ALLOWED_ROLE = os.environ.get("KEYCLOAK_ALLOWED_ROLE", "api-access")
PROTECTED_API_CLIENT_ID = os.environ.get("KEYCLOAK_PROTECTED_API_CLIENT_ID", "protected-api")
CONSUMER1_CLIENT_ID = os.environ.get("KEYCLOAK_CONSUMER1_CLIENT_ID", "consumer-1")
CONSUMER1_SECRET = os.environ.get("KEYCLOAK_CONSUMER1_SECRET", "consumer-1-secret")
CONSUMER2_CLIENT_ID = os.environ.get("KEYCLOAK_CONSUMER2_CLIENT_ID", "consumer-2")
CONSUMER2_SECRET = os.environ.get("KEYCLOAK_CONSUMER2_SECRET", "consumer-2-secret")
CONFIG_PATH = "/tmp/kcadm.config"


def run(command, *, expect_json=False, check=True):
    result = subprocess.run(command, capture_output=True, text=True)
    if check and result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Command failed: {' '.join(command)} :: {stderr}")
    output = (result.stdout or "").strip()
    if expect_json:
        return json.loads(output or "null")
    return output


def kcadm(*args, expect_json=False, check=True):
    command = [
        "docker",
        "exec",
        CONTAINER,
        "/opt/keycloak/bin/kcadm.sh",
        *args,
        "--config",
        CONFIG_PATH,
    ]
    return run(command, expect_json=expect_json, check=check)


def wait_for_keycloak():
    for _ in range(90):
        try:
            run(["docker", "exec", CONTAINER, "/bin/sh", "-lc", "exec 3<>/dev/tcp/127.0.0.1/8080"], check=True)
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Keycloak container did not become ready in time")


def login():
    last_error = None
    for _ in range(30):
        try:
            kcadm(
                "config",
                "credentials",
                "--server",
                "http://localhost:8080",
                "--realm",
                "master",
                "--user",
                ADMIN_USERNAME,
                "--password",
                ADMIN_PASSWORD,
            )
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2)
    raise last_error or RuntimeError("Keycloak login failed")


def realm_exists():
    result = subprocess.run(
        [
            "docker",
            "exec",
            CONTAINER,
            "/opt/keycloak/bin/kcadm.sh",
            "get",
            f"realms/{REALM}",
            "--config",
            CONFIG_PATH,
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def ensure_realm():
    if not realm_exists():
        kcadm(
            "create",
            "realms",
            "-s",
            f"realm={REALM}",
            "-s",
            "enabled=true",
            "-s",
            "sslRequired=NONE",
        )
    else:
        kcadm(
            "update",
            f"realms/{REALM}",
            "-s",
            "enabled=true",
            "-s",
            "sslRequired=NONE",
        )


def ensure_master_realm_http():
    kcadm(
        "update",
        "realms/master",
        "-s",
        "sslRequired=NONE",
    )


def ensure_realm_role():
    roles = kcadm("get", "roles", "-r", REALM, expect_json=True)
    if not any(role["name"] == ALLOWED_ROLE for role in roles or []):
        kcadm("create", "roles", "-r", REALM, "-s", f"name={ALLOWED_ROLE}")


def get_client(client_id):
    clients = kcadm("get", "clients", "-r", REALM, "-q", f"clientId={client_id}", expect_json=True)
    return clients[0] if clients else None


def ensure_client(client_id, secret, service_account):
    client = get_client(client_id)
    args = [
        "-s",
        f"clientId={client_id}",
        "-s",
        "protocol=openid-connect",
        "-s",
        "publicClient=false",
        "-s",
        f"serviceAccountsEnabled={'true' if service_account else 'false'}",
        "-s",
        "standardFlowEnabled=false",
        "-s",
        "directAccessGrantsEnabled=false",
        "-s",
        "implicitFlowEnabled=false",
        "-s",
        "fullScopeAllowed=true",
        "-s",
        f"secret={secret}",
        "-s",
        "enabled=true",
    ]
    if client is None:
        result = subprocess.run(
            [
                "docker",
                "exec",
                CONTAINER,
                "/opt/keycloak/bin/kcadm.sh",
                "create",
                "clients",
                "-r",
                REALM,
                *args,
                "--config",
                CONFIG_PATH,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            if "already exists" not in stderr:
                raise RuntimeError(
                    f"Command failed: docker exec {CONTAINER} /opt/keycloak/bin/kcadm.sh create clients -r {REALM} ... :: {stderr}"
                )
        client = get_client(client_id)
        if client is None:
            raise RuntimeError(f"Client lookup failed after create: {client_id}")
    else:
        client = get_client(client_id)
    kcadm("update", f"clients/{client['id']}", "-r", REALM, *args)
    return get_client(client_id)


def get_service_account_user_id(client_id):
    client = get_client(client_id)
    if client is None:
        raise RuntimeError(f"Client not found: {client_id}")
    user = kcadm("get", f"clients/{client['id']}/service-account-user", "-r", REALM, expect_json=True)
    return user["id"]


def get_user_realm_roles(user_id):
    roles = kcadm("get", f"users/{user_id}/role-mappings/realm", "-r", REALM, expect_json=True)
    return {role["name"] for role in roles or []}


def ensure_role_mapping(client_id, assign):
    user_id = get_service_account_user_id(client_id)
    current = get_user_realm_roles(user_id)
    if assign and ALLOWED_ROLE not in current:
        kcadm("add-roles", "-r", REALM, "--uid", user_id, "--rolename", ALLOWED_ROLE)
    if not assign and ALLOWED_ROLE in current:
        kcadm("remove-roles", "-r", REALM, "--uid", user_id, "--rolename", ALLOWED_ROLE)


def main():
    wait_for_keycloak()
    login()
    ensure_master_realm_http()
    ensure_realm()
    ensure_realm_role()
    ensure_client(PROTECTED_API_CLIENT_ID, "protected-api-secret", service_account=False)
    ensure_client(CONSUMER1_CLIENT_ID, CONSUMER1_SECRET, service_account=True)
    ensure_client(CONSUMER2_CLIENT_ID, CONSUMER2_SECRET, service_account=True)
    ensure_role_mapping(CONSUMER1_CLIENT_ID, assign=True)
    ensure_role_mapping(CONSUMER2_CLIENT_ID, assign=False)
    print(json.dumps({"realm": REALM, "status": "ready"}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)
