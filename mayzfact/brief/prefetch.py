"""Download link klip di background begitu disimpan di brief, biar fetch tinggal motong (spec brief revisi §2)."""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Callable

from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, read_json, write_json_atomic

_BUSY = ("antre", "download")


class Prefetcher:
    def __init__(self, paths: RunPaths, obtain: Callable[[dict, Path], list[Path]], log: Callable[[str], None] = print) -> None:
        self._paths, self._obtain, self._log = paths, obtain, log
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._lock = threading.Lock()
        self._state: dict[str, dict] = {}
        if paths.prefetch_json.exists():
            try:
                self._state = read_json(paths.prefetch_json)
            except ValueError:
                self._state = {}
        # Sisa "antre"/"download" dari server yang dimatiin: dianggap belum jalan, bakal di-enqueue ulang pas start.
        for st in self._state.values():
            if st.get("state") in _BUSY:
                st.update(state="gagal", message="server brief ditutup sebelum selesai")
        self._thread = threading.Thread(target=self._run, name="brief-prefetch", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def enqueue(self, urls: list[str]) -> None:
        with self._lock:
            for url in dict.fromkeys(urls):
                if self._state.get(url, {}).get("state") in _BUSY:
                    continue  # lagi jalan, jangan dobel
                self._state[url] = {"state": "antre", "message": "", "files": []}
                self._queue.put(url)
            self._save()

    def snapshot(self) -> dict[str, dict]:
        with self._lock:
            return {k: dict(v) for k, v in self._state.items()}

    def stop(self, timeout_s: float = 30.0) -> None:
        """Berhenti rapi: antrean sisa dibuang, download yang lagi jalan ditunggu maksimal timeout_s."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._queue.put(None)
        self._thread.join(timeout_s)
        with self._lock:
            for st in self._state.values():
                if st["state"] in _BUSY:
                    st.update(state="gagal", message="server brief ditutup sebelum selesai")
            self._save()

    def _set(self, url: str, **fields) -> None:
        with self._lock:
            self._state.setdefault(url, {"state": "antre", "message": "", "files": []}).update(fields)
            self._save()

    def _save(self) -> None:
        write_json_atomic(self._paths.prefetch_json, self._state)

    def _run(self) -> None:
        while True:
            url = self._queue.get()
            if url is None:
                return
            self._set(url, state="download", message="")
            try:
                files = self._obtain({"url": url}, self._paths.root)
                self._set(url, state="siap", message="", files=[f.name for f in files])
                self._log(f"[brief] siap: {url}")
            except PipelineError as exc:
                self._set(url, state="gagal", message=exc.message.splitlines()[0][:160])
                self._log(f"[brief] gagal: {url}: {exc.message.splitlines()[0][:120]}")
            except Exception as exc:  # resolver pihak ketiga bisa ngelempar apa aja; worker jangan mati
                self._set(url, state="gagal", message=f"{type(exc).__name__}: {str(exc)[:120]}")
