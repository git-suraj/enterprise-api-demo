#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
HYBRID_CERT_DIR = ROOT_DIR / "certs" / "hybrid"
CLUSTER_CERT = HYBRID_CERT_DIR / "cluster.crt"
CLUSTER_KEY = HYBRID_CERT_DIR / "cluster.key"
CLUSTER_SUBJECT = os.environ.get("KONG_CLUSTER_CERT_SUBJECT", "/CN=kong_clustering")
CLUSTER_SAN = os.environ.get(
    "KONG_CLUSTER_CERT_SAN",
    "subjectAltName=DNS:kong_clustering,DNS:kong-cp,DNS:kong-demo-control-plane,DNS:localhost",
)


def run_openssl(args):
    completed = subprocess.run(["openssl", *args], capture_output=True, text=True, check=False)
    if completed.returncode == 0:
        return
    raise SystemExit(completed.stderr.strip() or "openssl failed")


def main():
    HYBRID_CERT_DIR.mkdir(parents=True, exist_ok=True)
    if CLUSTER_CERT.exists() and CLUSTER_KEY.exists():
        return

    run_openssl(
        [
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "3650",
            "-keyout",
            str(CLUSTER_KEY),
            "-out",
            str(CLUSTER_CERT),
            "-subj",
            CLUSTER_SUBJECT,
            "-addext",
            CLUSTER_SAN,
        ]
    )


if __name__ == "__main__":
    main()
