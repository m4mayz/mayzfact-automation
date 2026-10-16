"""Tunnel ngrok buat brief (port 3100) dan Remotion Studio (port 3000), selalu dikunci basic-auth."""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
from dataclasses import dataclass
from typing import Any, Callable

from mayzfact.errors import PipelineError

AUTH_HINT = "Isi NGROK_BASIC_AUTH di .env, format user:password (password minimal 8 karakter, aturan ngrok)."


@dataclass
class Tunnel:
    url: str
    proc: Any

    def stop(self, *, windows: bool = os.name == "nt", run: Callable[..., Any] = subprocess.run) -> None:
        if windows:  # ngrok scoop = shim + proses asli; matiin satu pohon proses biar nggak ada yang nyangkut
            run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], capture_output=True)
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def _check_auth(basic_auth: str) -> None:
    user, sep, password = basic_auth.partition(":")
    if not sep or not user or len(password) < 8:
        raise PipelineError("ngrok", AUTH_HINT)


def start_tunnel(port: int, basic_auth: str, *, popen: Callable[..., Any] = subprocess.Popen,
                 which: Callable[[str], str | None] = shutil.which, timeout_s: float = 20.0) -> Tunnel:
    """Nyalain `ngrok http <port>` pakai basic-auth, balikin URL publiknya dari log JSON ngrok."""
    _check_auth(basic_auth)  # tanpa password, halaman tanpa login ini jangan pernah kebuka ke internet
    exe = which("ngrok")
    if not exe:
        raise PipelineError("ngrok", "ngrok belum ke-install. Install dulu (scoop install ngrok), terus ngrok config add-authtoken <token>.")
    proc = popen([exe, "http", str(port), "--basic-auth", basic_auth, "--log", "stdout", "--log-format", "json"],
                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    lines: queue.Queue[dict | None] = queue.Queue()

    def drain() -> None:
        # Log ngrok dibaca terus sampai proses mati, biar pipe-nya nggak penuh dan ngrok nggak ke-block.
        for raw in proc.stdout:
            try:
                lines.put(json.loads(raw))
            except ValueError:
                continue
        lines.put(None)

    threading.Thread(target=drain, name=f"ngrok-{port}", daemon=True).start()
    last_error = ""
    while True:
        try:
            entry = lines.get(timeout=timeout_s)
        except queue.Empty:
            proc.terminate()
            raise PipelineError("ngrok", f"ngrok nggak ngasih URL dalam {timeout_s:.0f} detik. {last_error}".strip())
        if entry is None:
            raise PipelineError("ngrok", f"ngrok berhenti sebelum tunnel jalan: {last_error or 'nggak ada pesan'}. "
                                         "Kalau ada ngrok lain yang masih jalan, matiin dulu (PowerShell: Stop-Process -Name ngrok).")
        if entry.get("msg") == "started tunnel" and str(entry.get("url", "")).startswith("https://"):
            return Tunnel(entry["url"], proc)
        if entry.get("lvl") in ("eror", "crit"):
            last_error = entry.get("err") or entry.get("msg") or last_error
