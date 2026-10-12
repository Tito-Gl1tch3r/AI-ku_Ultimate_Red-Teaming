from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from .service import (
    IdempotencyConflict,
    InvalidIdentifier,
    RewardService,
    RewardServiceError,
    UnknownReward,
)

MAX_BODY_BYTES = 4096


class RewardRequestHandler(BaseHTTPRequestHandler):
    service: RewardService
    server_version = "MobileTrustReference/0.1"

    def _send_json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_object(self) -> dict[str, object]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise InvalidIdentifier("invalid Content-Length") from error
        if length <= 0 or length > MAX_BODY_BYTES:
            raise InvalidIdentifier(f"request body must be 1..{MAX_BODY_BYTES} bytes")
        try:
            payload = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InvalidIdentifier("request body must be a JSON object") from error
        if not isinstance(payload, dict):
            raise InvalidIdentifier("request body must be a JSON object")
        return payload

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = urlparse(self.path).path
        if path == "/healthz":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        if path == "/v1/rewards":
            self._send_json(HTTPStatus.OK, {"rewards": self.service.reward_catalog()})
            return

        prefix = "/v1/accounts/"
        suffix = "/balance"
        if path.startswith(prefix) and path.endswith(suffix):
            account_id = unquote(path[len(prefix) : -len(suffix)]).strip("/")
            try:
                balance = self.service.balance_for(account_id)
            except InvalidIdentifier as error:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return
            self._send_json(HTTPStatus.OK, {"account_id": account_id, "balance": balance})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "route not found"})

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if urlparse(self.path).path != "/v1/rewards/claim":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "route not found"})
            return
        try:
            payload = self._read_json_object()
            allowed = {"account_id", "reward_id", "idempotency_key"}
            unexpected = sorted(set(payload) - allowed)
            if unexpected:
                raise InvalidIdentifier("unexpected fields: " + ", ".join(unexpected))
            result = self.service.claim_reward(
                payload.get("account_id"),
                payload.get("reward_id"),
                payload.get("idempotency_key"),
            )
        except IdempotencyConflict as error:
            self._send_json(HTTPStatus.CONFLICT, {"error": str(error)})
            return
        except UnknownReward as error:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": str(error)})
            return
        except RewardServiceError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return

        status = HTTPStatus.OK if result.replayed else HTTPStatus.CREATED
        self._send_json(status, result.to_dict())

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def build_server(host: str, port: int, service: RewardService | None = None) -> ThreadingHTTPServer:
    service = service or RewardService()

    class ConfiguredHandler(RewardRequestHandler):
        pass

    ConfiguredHandler.service = service
    return ThreadingHTTPServer((host, port), ConfiguredHandler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local Mobile Trust Lab reward reference")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    server = build_server(args.host, args.port)
    host, port = server.server_address[:2]
    print(f"reference service listening on http://{host}:{port}")
    print("local lab reference only; authentication and durable storage are out of scope")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
