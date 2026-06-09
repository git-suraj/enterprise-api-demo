import base64
import json
import os
import subprocess
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = os.environ.get("CRYPTO_HELPER_HOST", "0.0.0.0")
PORT = int(os.environ.get("CRYPTO_HELPER_PORT", "8092"))
ALGORITHM = "AES/CBC/PKCS5Padding"
GATEWAY_PRIVATE_KEY_PATH = Path(os.environ.get("CRYPTO_GATEWAY_PRIVATE_KEY_PATH", "/crypto/gateway_private.pem"))
GATEWAY_PUBLIC_KEY_PATH = Path(os.environ.get("CRYPTO_GATEWAY_PUBLIC_KEY_PATH", "/crypto/gateway_public.pem"))
CLIENT_PRIVATE_KEY_PATH = Path(os.environ.get("CRYPTO_CLIENT_PRIVATE_KEY_PATH", "/crypto/client_private.pem"))
CLIENT_PUBLIC_KEY_PATH = Path(os.environ.get("CRYPTO_CLIENT_PUBLIC_KEY_PATH", "/crypto/client_public.pem"))
GATEWAY_PRIVATE_KEY_PASSPHRASE = os.environ.get(
    "CRYPTO_GATEWAY_PRIVATE_KEY_PASSPHRASE",
    "gateway-demo-passphrase",
)


def run_openssl(args, *, input_bytes=None):
    completed = subprocess.run(
        ["openssl", *args],
        input=input_bytes,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace").strip() or "openssl failed")
    return completed.stdout


def ensure_algorithm(payload):
    algorithm = payload.get("algorithm", ALGORITHM)
    if algorithm != ALGORITHM:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    return algorithm


def encode_envelope(*, encrypted_session_key, iv, encrypted_payload):
    return {
        "algorithm": ALGORITHM,
        "encryptedSessionKey": base64.b64encode(encrypted_session_key).decode("utf-8"),
        "iv": base64.b64encode(iv).decode("utf-8"),
        "encryptedPayload": base64.b64encode(encrypted_payload).decode("utf-8"),
    }


def decode_base64_field(payload, field_name):
    raw = payload.get(field_name)
    if not raw:
        raise ValueError(f"Missing field: {field_name}")
    return base64.b64decode(raw)


def unwrap_envelope(payload):
    if isinstance(payload.get("envelope"), dict):
        return payload["envelope"]
    return payload


def encrypt_payload(plaintext, public_key_path):
    plaintext_bytes = plaintext.encode("utf-8") if isinstance(plaintext, str) else plaintext
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        plaintext_path = tmpdir_path / "plaintext.bin"
        key_path = tmpdir_path / "session.key"
        iv_path = tmpdir_path / "session.iv"
        ciphertext_path = tmpdir_path / "ciphertext.bin"
        wrapped_key_path = tmpdir_path / "wrapped.key"

        plaintext_path.write_bytes(plaintext_bytes)
        key_bytes = run_openssl(["rand", "32"])
        iv_bytes = run_openssl(["rand", "16"])
        key_path.write_bytes(key_bytes)
        iv_path.write_bytes(iv_bytes)

        run_openssl(
            [
                "enc",
                "-aes-256-cbc",
                "-nosalt",
                "-K",
                key_bytes.hex(),
                "-iv",
                iv_bytes.hex(),
                "-in",
                str(plaintext_path),
                "-out",
                str(ciphertext_path),
            ]
        )
        run_openssl(
            [
                "pkeyutl",
                "-encrypt",
                "-pubin",
                "-inkey",
                str(public_key_path),
                "-in",
                str(key_path),
                "-out",
                str(wrapped_key_path),
            ]
        )
        return encode_envelope(
            encrypted_session_key=wrapped_key_path.read_bytes(),
            iv=iv_bytes,
            encrypted_payload=ciphertext_path.read_bytes(),
        )


def decrypt_payload(payload, private_key_path, *, passphrase=None):
    payload = unwrap_envelope(payload)
    ensure_algorithm(payload)
    encrypted_session_key = decode_base64_field(payload, "encryptedSessionKey")
    iv = decode_base64_field(payload, "iv")
    encrypted_payload = decode_base64_field(payload, "encryptedPayload")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        wrapped_key_path = tmpdir_path / "wrapped.key"
        wrapped_key_path.write_bytes(encrypted_session_key)
        session_key_path = tmpdir_path / "session.key"
        ciphertext_path = tmpdir_path / "ciphertext.bin"
        ciphertext_path.write_bytes(encrypted_payload)
        plaintext_path = tmpdir_path / "plaintext.bin"

        decrypt_args = [
            "pkeyutl",
            "-decrypt",
            "-inkey",
            str(private_key_path),
            "-in",
            str(wrapped_key_path),
            "-out",
            str(session_key_path),
        ]
        env = os.environ.copy()
        if passphrase:
            decrypt_args.extend(["-passin", "env:CRYPTO_GATEWAY_PRIVATE_KEY_PASSPHRASE"])
            env["CRYPTO_GATEWAY_PRIVATE_KEY_PASSPHRASE"] = passphrase
        completed = subprocess.run(
            ["openssl", *decrypt_args],
            capture_output=True,
            check=False,
            env=env,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.decode("utf-8", errors="replace").strip() or "openssl pkeyutl decrypt failed"
            )

        session_key = session_key_path.read_bytes()
        run_openssl(
            [
                "enc",
                "-d",
                "-aes-256-cbc",
                "-nosalt",
                "-K",
                session_key.hex(),
                "-iv",
                iv.hex(),
                "-in",
                str(ciphertext_path),
                "-out",
                str(plaintext_path),
            ]
        )
        return plaintext_path.read_text("utf-8")


class CryptoHelperHandler(BaseHTTPRequestHandler):
    server_version = "CryptoHelper/1.0"

    def do_GET(self):
        if self.path == "/health":
            self.respond_json(
                {
                    "ok": True,
                    "gatewayPrivateKey": GATEWAY_PRIVATE_KEY_PATH.exists(),
                    "gatewayPublicKey": GATEWAY_PUBLIC_KEY_PATH.exists(),
                    "clientPrivateKey": CLIENT_PRIVATE_KEY_PATH.exists(),
                    "clientPublicKey": CLIENT_PUBLIC_KEY_PATH.exists(),
                }
            )
            return
        self.respond_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self):
        try:
            payload = self.read_json()
            if self.path == "/encrypt-request":
                plaintext = payload.get("payload", {})
                plaintext_text = plaintext if isinstance(plaintext, str) else json.dumps(plaintext)
                self.respond_json(
                    {
                        "plaintext": json.loads(plaintext_text),
                        "envelope": encrypt_payload(plaintext_text, GATEWAY_PUBLIC_KEY_PATH),
                    }
                )
                return
            if self.path == "/decrypt-request":
                plaintext_text = decrypt_payload(
                    payload,
                    GATEWAY_PRIVATE_KEY_PATH,
                    passphrase=GATEWAY_PRIVATE_KEY_PASSPHRASE,
                )
                self.respond_json({"plaintext": plaintext_text})
                return
            if self.path == "/encrypt-response":
                plaintext = payload.get("payload")
                if plaintext is None:
                    plaintext = payload.get("plaintext", {})
                plaintext_text = plaintext if isinstance(plaintext, str) else json.dumps(plaintext)
                self.respond_json(
                    {
                        "plaintext": json.loads(plaintext_text),
                        "envelope": encrypt_payload(plaintext_text, CLIENT_PUBLIC_KEY_PATH),
                    }
                )
                return
            if self.path == "/decrypt-response":
                plaintext_text = decrypt_payload(payload, CLIENT_PRIVATE_KEY_PATH)
                self.respond_json({"plaintext": plaintext_text})
                return
        except ValueError as exc:
            self.respond_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except RuntimeError as exc:
            self.respond_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self.respond_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def read_json(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def respond_json(self, payload, status=HTTPStatus.OK):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):  # noqa: A003
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), CryptoHelperHandler)
    server.serve_forever()
