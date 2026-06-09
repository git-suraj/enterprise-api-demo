import os
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
CRYPTO_DIR = ROOT_DIR / "certs" / "crypto"
GATEWAY_PRIVATE_KEY = CRYPTO_DIR / "gateway_private.pem"
GATEWAY_PUBLIC_KEY = CRYPTO_DIR / "gateway_public.pem"
CLIENT_PRIVATE_KEY = CRYPTO_DIR / "client_private.pem"
CLIENT_PUBLIC_KEY = CRYPTO_DIR / "client_public.pem"
PASSPHRASE = os.environ.get("CRYPTO_GATEWAY_PRIVATE_KEY_PASSPHRASE", "gateway-demo-passphrase")


def run_openssl(args, *, env=None):
    completed = subprocess.run(["openssl", *args], capture_output=True, check=False, env=env)
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.decode("utf-8", errors="replace").strip() or "openssl failed")


def main():
    CRYPTO_DIR.mkdir(parents=True, exist_ok=True)

    if not GATEWAY_PRIVATE_KEY.exists():
        run_openssl(
            [
                "genpkey",
                "-algorithm",
                "RSA",
                "-pkeyopt",
                "rsa_keygen_bits:2048",
                "-aes-256-cbc",
                "-pass",
                f"pass:{PASSPHRASE}",
                "-out",
                str(GATEWAY_PRIVATE_KEY),
            ]
        )

    if not GATEWAY_PUBLIC_KEY.exists():
        run_openssl(
            [
                "rsa",
                "-pubout",
                "-in",
                str(GATEWAY_PRIVATE_KEY),
                "-passin",
                f"pass:{PASSPHRASE}",
                "-out",
                str(GATEWAY_PUBLIC_KEY),
            ]
        )

    if not CLIENT_PRIVATE_KEY.exists():
        run_openssl(
            [
                "genpkey",
                "-algorithm",
                "RSA",
                "-pkeyopt",
                "rsa_keygen_bits:2048",
                "-out",
                str(CLIENT_PRIVATE_KEY),
            ]
        )

    if not CLIENT_PUBLIC_KEY.exists():
        run_openssl(
            [
                "rsa",
                "-pubout",
                "-in",
                str(CLIENT_PRIVATE_KEY),
                "-out",
                str(CLIENT_PUBLIC_KEY),
            ]
        )

    print(f"Payload crypto materials ready in {CRYPTO_DIR}")


if __name__ == "__main__":
    main()
