"""Cache response search API di disk (Pixabay minta di-cache 24 jam)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Callable

from mayzfact.store import read_json, write_json_atomic


class SearchCache:
    def __init__(self, root: Path, ttl_s: float = 24 * 3600, now: Callable[[], float] = time.time) -> None:
        self.root = root
        self.ttl_s = ttl_s
        self._now = now

    def _path(self, provider: str, params: dict) -> Path:
        digest = hashlib.sha256(json.dumps(params, sort_keys=True).encode("utf-8")).hexdigest()[:24]
        return self.root / provider / f"{digest}.json"

    def get(self, provider: str, params: dict) -> dict | None:
        path = self._path(provider, params)
        if not path.exists():
            return None
        entry = read_json(path)
        if self._now() - entry["saved_at"] > self.ttl_s:
            return None
        return entry["response"]

    def put(self, provider: str, params: dict, response: dict) -> None:
        write_json_atomic(self._path(provider, params), {"saved_at": self._now(), "response": response})
