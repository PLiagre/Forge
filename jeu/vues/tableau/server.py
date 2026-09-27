"""Serveur HTTP local stdlib : fichiers statiques + snapshots fournis."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from vues.tableau.snapshot_loader import EchantillonVide, construire_dashboard, serialize_dashboard

_STATIC = Path(__file__).resolve().parent / "static"


class SnapshotServer(ThreadingHTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        snapshot_a: bytes,
        snapshot_b: Optional[bytes],
    ) -> None:
        self.snapshot_a = snapshot_a
        self.snapshot_b = snapshot_b
        self._dashboard: Optional[bytes] = None
        super().__init__(address, _Handler)

    def dashboard_bytes(self) -> bytes:
        if self._dashboard is None:
            document = json.loads(self.snapshot_a.decode("utf-8"))
            self._dashboard = serialize_dashboard(construire_dashboard(document))
        return self._dashboard


class _Handler(BaseHTTPRequestHandler):
    server: SnapshotServer

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/snapshot.json":
            self._send(200, self.server.snapshot_a, "application/json; charset=utf-8")
            return
        if path == "/compare.json":
            if self.server.snapshot_b is None:
                self._send(404, b"absent\n", "text/plain; charset=utf-8")
                return
            self._send(200, self.server.snapshot_b, "application/json; charset=utf-8")
            return
        if path == "/dashboard.json":
            try:
                payload = self.server.dashboard_bytes()
            except EchantillonVide as exc:
                self._send(409, f"{exc}\n".encode("utf-8"), "text/plain; charset=utf-8")
                return
            self._send(200, payload, "application/json; charset=utf-8")
            return
        if path == "/meta.json":
            payload = json.dumps(
                {"has_compare": self.server.snapshot_b is not None},
                separators=(",", ":"),
            ).encode("utf-8")
            self._send(200, payload, "application/json; charset=utf-8")
            return
        relative = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
        if ".." in relative or relative.startswith("/"):
            self._send(404, b"refus\n", "text/plain; charset=utf-8")
            return
        candidate = (_STATIC / relative).resolve()
        try:
            candidate.relative_to(_STATIC.resolve())
        except ValueError:
            self._send(404, b"refus\n", "text/plain; charset=utf-8")
            return
        if not candidate.is_file():
            self._send(404, b"absent\n", "text/plain; charset=utf-8")
            return
        data = candidate.read_bytes()
        types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }
        self._send(200, data, types.get(candidate.suffix, "application/octet-stream"))


def serve(
    host: str,
    port: int,
    snapshot_a: bytes,
    snapshot_b: Optional[bytes],
) -> SnapshotServer:
    return SnapshotServer((host, port), snapshot_a, snapshot_b)
