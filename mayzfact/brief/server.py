"""Server lokal halaman brief: 127.0.0.1 doang, baca/tulis links.json, terima upload (spec metode manual bagian 4)."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import PurePosixPath
from urllib.parse import parse_qs, unquote, urlparse

from mayzfact.brief.page import render_page
from mayzfact.manual.links import (
    IMAGE_EXTS,
    VIDEO_EXTS,
    load_links,
    missing_shots,
    normalize_links,
    save_links,
)
from mayzfact.store import RunPaths, read_json

MAX_UPLOAD = 500 * 1024 * 1024
PORT_TRIES = 10


def make_server(paths: RunPaths, port: int, *, max_upload: int = MAX_UPLOAD) -> ThreadingHTTPServer:
    root = paths.root.resolve()

    def plan() -> dict:
        return read_json(paths.shots_plan_json)

    def status() -> dict:
        return read_json(paths.links_status_json) if paths.links_status_json.exists() else {"shots": {}}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # jangan spam terminal
            pass

        def _send(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, data: dict) -> None:
            self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _host_ok(self) -> bool:
            """Host cuma boleh 127.0.0.1/localhost. Ini nutup DNS rebinding (domain luar yang di-resolve ke 127.0.0.1)."""
            port = self.server.server_address[1]
            return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

        def do_GET(self) -> None:
            if not self._host_ok():
                return self._json(403, {"error": "host nggak dikenal"})
            url = urlparse(self.path)
            if url.path == "/":
                html = render_page(paths.root.name, plan(), load_links(paths.links_json), status())
                return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            if url.path == "/api/state":
                return self._json(200, {"plan": plan(), "links": load_links(paths.links_json), "status": status()})
            if url.path.startswith("/files/"):
                target = (root / unquote(url.path[len("/files/"):])).resolve()
                if root in target.parents and target.is_file():
                    kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                    return self._send(200, target.read_bytes(), kind)
            self._json(404, {"error": "nggak ada"})

        def _body(self, length: int, out=None) -> None:
            """Baca body per 1 MB. Body yang ditolak tetap dibaca (dibuang), kalau nggak Windows ngirim RST ke client."""
            while length > 0:
                chunk = self.rfile.read(min(length, 1024 * 1024))
                if not chunk:
                    break
                length -= len(chunk)
                if out is not None:
                    out.write(chunk)

        def _reject(self, code: int, message: str, length: int) -> None:
            self._body(length)
            self._json(code, {"error": message})

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            if not self._host_ok():
                return self._reject(403, "host nggak dikenal", length)
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host')}":  # tolak POST dari web lain (CSRF)
                return self._reject(403, "request dari luar halaman brief ditolak", length)
            url = urlparse(self.path)
            if url.path == "/api/links":
                try:
                    data = normalize_links(json.loads(self.rfile.read(length) or b"{}"), len(plan()["shots"]))
                except (ValueError, TypeError) as exc:
                    return self._json(400, {"error": str(exc)})
                save_links(paths.links_json, data)
                return self._json(200, {"ok": True, "missing": missing_shots(plan(), data)})
            if url.path == "/api/upload":
                try:
                    number = int(parse_qs(url.query).get("shot", ["0"])[0])
                except ValueError:
                    number = 0
                suffix = PurePosixPath(unquote(self.headers.get("X-Filename", ""))).suffix.lower()
                if not 1 <= number <= len(plan()["shots"]):
                    return self._reject(400, f"shot {number} nggak ada di plan", length)
                if suffix not in VIDEO_EXTS | IMAGE_EXTS:
                    return self._reject(400, f"ekstensi {suffix or '?'} nggak didukung", length)
                if length > max_upload:
                    return self._reject(413, f"file kegedean (maks {max_upload // (1024 * 1024)} MB)", length)
                paths.manual_dir.mkdir(parents=True, exist_ok=True)
                for old in paths.manual_dir.glob(f"shot_{number:02d}.*"):
                    old.unlink()
                dest = paths.manual_dir / f"shot_{number:02d}{suffix}"
                with dest.open("wb") as fh:
                    self._body(length, fh)
                rel = f"manual/{dest.name}"
                links = load_links(paths.links_json)
                links.setdefault("shots", {})[str(number)] = {"file": rel}
                save_links(paths.links_json, links)
                return self._json(200, {"file": rel})
            self._reject(404, "nggak ada", length)

    last: OSError | None = None
    for candidate in [0] if port == 0 else range(port, port + PORT_TRIES):
        try:
            return ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
        except OSError as exc:
            last = exc
    raise OSError(f"Port {port}-{port + PORT_TRIES - 1} kepakai semua: {last}")
