import argparse
import json
import os
import socket
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs


DATAKIT_ACCOUNTS = [
    {
        "accountId": "acc-101",
        "accountType": "savings",
        "status": "active",
        "nickname": "Primary Savings",
    },
    {
        "accountId": "acc-202",
        "accountType": "credit",
        "status": "delinquent",
        "nickname": "Rewards Credit",
    },
]

DATAKIT_ACCOUNT_DETAILS = {
    "acc-101": {
        "accountId": "acc-101",
        "balance": 2400.12,
        "currency": "USD",
        "branch": "Downtown",
        "lastPaymentDate": "2026-05-01",
    },
    "acc-202": {
        "accountId": "acc-202",
        "balance": -320.75,
        "currency": "USD",
        "branch": "Airport",
        "lastPaymentDate": "2026-04-18",
    },
}


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def build_handler(service_name: str, region: str, api_version: str = "", release_stage: str = ""):
    class UpstreamHandler(BaseHTTPRequestHandler):
        server_version = "MockUpstream/1.0"

        def _request_payload(self, method: str, body_text: str = ""):
            request_id = self.headers.get("x-request-id") or str(uuid.uuid4())
            query = {}
            path = self.path
            if "?" in self.path:
                path, query_string = self.path.split("?", 1)
                query = {
                    key: values if len(values) > 1 else values[0]
                    for key, values in parse_qs(query_string, keep_blank_values=True).items()
                }
            return {
                "service": service_name,
                "region": region,
                "api_version": api_version or None,
                "release_stage": release_stage or None,
                "handled_by": f"{region}-cluster",
                "path": path,
                "query": query,
                "method": method,
                "request_id": request_id,
                "host": socket.gethostname(),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "content_type": self.headers.get("Content-Type", ""),
                "content_length": self.headers.get("Content-Length", "0"),
                "body": body_text,
            }

        def _send_json(self, status: int, payload: dict, request_id: str):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("x-upstream-service", service_name)
            self.send_header("x-upstream-region", region)
            self.send_header("x-request-id", request_id)
            self.end_headers()
            self.wfile.write(body)

        def _request_context(self):
            query = {}
            path = self.path
            if "?" in self.path:
                path, query_string = self.path.split("?", 1)
                query = {
                    key: values if len(values) > 1 else values[0]
                    for key, values in parse_qs(query_string, keep_blank_values=True).items()
                }
            request_id = self.headers.get("x-request-id") or str(uuid.uuid4())
            return path, query, request_id

        def _send_datakit_fallback(self, query: dict, request_id: str):
            mode = query.get("mode", "success")
            if mode == "fail":
                self._send_json(
                    503,
                    {
                        "source": "api1",
                        "mode": "fail",
                        "message": "API1 failed and should trigger Datakit fallback.",
                        "generatedAt": utc_timestamp(),
                    },
                    request_id,
                )
                return

            self._send_json(
                200,
                {
                    "source": "api1",
                    "mode": "success",
                    "accountId": "acc-101",
                    "status": "active",
                    "product": "checking",
                    "generatedAt": utc_timestamp(),
                },
                request_id,
            )

        def _send_datakit_fallback_wrapper(self, query: dict, request_id: str):
            mode = query.get("mode", "success")
            if mode == "fail":
                self._send_json(
                    200,
                    {
                        "wrappedSource": "api1",
                        "originalStatus": 503,
                        "result": {
                            "source": "api1",
                            "mode": "fail",
                            "message": "API1 failed and should trigger Datakit fallback.",
                            "generatedAt": utc_timestamp(),
                        },
                    },
                    request_id,
                )
                return

            self._send_json(
                200,
                {
                    "wrappedSource": "api1",
                    "originalStatus": 200,
                    "result": {
                        "source": "api1",
                        "mode": "success",
                        "accountId": "acc-101",
                        "status": "active",
                        "product": "checking",
                        "generatedAt": utc_timestamp(),
                    },
                },
                request_id,
            )

        def _send_datakit_api2_fallback(self, request_id: str):
            self._send_json(
                200,
                {
                    "source": "api2",
                    "accountId": "acc-101",
                    "status": "served-by-fallback",
                    "product": "backup-account-summary",
                    "generatedAt": utc_timestamp(),
                },
                request_id,
            )

        def _send_datakit_accounts(self, request_id: str):
            self._send_json(
                200,
                {
                    "source": "api1",
                    "customerId": "cust-1001",
                    "generatedAt": utc_timestamp(),
                    "accounts": DATAKIT_ACCOUNTS,
                },
                request_id,
            )

        def _send_datakit_cache_source(self, request_id: str):
            detail = DATAKIT_ACCOUNT_DETAILS["acc-101"]
            self._send_json(
                200,
                {
                    "source": "api1",
                    "accountId": detail["accountId"],
                    "balance": detail["balance"],
                    "currency": detail["currency"],
                    "generatedAt": utc_timestamp(),
                },
                request_id,
            )

        def do_GET(self):
            path, query, request_id = self._request_context()
            if path == "/health":
                payload = {
                    "service": service_name,
                    "region": region,
                    "status": "healthy",
                }
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path == "/datakit/api1/fallback":
                self._send_datakit_fallback(query, request_id)
                return

            if path == "/datakit/api1/fallback-wrapper":
                self._send_datakit_fallback_wrapper(query, request_id)
                return

            if path == "/datakit/api2/fallback":
                self._send_datakit_api2_fallback(request_id)
                return

            if path == "/datakit/api1/accounts":
                self._send_datakit_accounts(request_id)
                return

            if path == "/datakit/api1/cache-source":
                self._send_datakit_cache_source(request_id)
                return

            payload = self._request_payload("GET")
            self._send_json(200, payload, payload["request_id"])

        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", "0") or "0")
            body_text = self.rfile.read(content_length).decode("utf-8", errors="replace") if content_length > 0 else ""
            path, _, request_id = self._request_context()

            if path == "/datakit/api2/details":
                try:
                    parsed = json.loads(body_text) if body_text else {}
                except json.JSONDecodeError:
                    parsed = {}
                account_ids = parsed.get("accountIds") or []
                details = [DATAKIT_ACCOUNT_DETAILS[account_id] for account_id in account_ids if account_id in DATAKIT_ACCOUNT_DETAILS]
                self._send_json(
                    200,
                    {
                        "source": "api2",
                        "generatedAt": utc_timestamp(),
                        "accountDetails": details,
                    },
                    request_id,
                )
                return

            payload = self._request_payload("POST", body_text)
            self._send_json(200, payload, payload["request_id"])

        def log_message(self, fmt, *args):
            print(
                json.dumps(
                    {
                        "service": service_name,
                        "region": region,
                        "client": self.address_string(),
                        "message": fmt % args,
                    }
                )
            )

    return UpstreamHandler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--api-version", default="")
    parser.add_argument("--release-stage", default="")
    args = parser.parse_args()

    handler = build_handler(args.service, args.region, args.api_version, args.release_stage)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    print(
        json.dumps(
            {
                "message": "mock upstream ready",
                "service": args.service,
                "region": args.region,
                "api_version": args.api_version,
                "release_stage": args.release_stage,
                "port": args.port,
                "pid": os.getpid(),
            }
        )
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
