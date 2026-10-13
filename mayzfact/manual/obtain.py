"""Link/file dari brief → file media lokal (spec metode manual bagian 5)."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

from mayzfact.embed import can_open_image
from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import probe
from mayzfact.manual.douyin import resolve_douyin
from mayzfact.manual.links import IMAGE_EXTS, VIDEO_EXTS, link_kind
from mayzfact.manual.og import og_media
from mayzfact.manual.rednote import resolve_rednote
from mayzfact.manual.types import Media
from mayzfact.net import download
from mayzfact.ytdlp import run_ytdlp

YTDLP_TIMEOUT_S = 300


def cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def media_kind(path: Path) -> str | None:
    if can_open_image(path):
        return "photo"
    try:
        info = probe(path, "fetch")
    except PipelineError:
        return None
    return "video" if info.get("width") and (info.get("duration_s") or 0) > 0 else None


def _suffix(url: str, default: str) -> str:
    suffix = PurePosixPath(urlparse(url).path).suffix.lower()
    return suffix if suffix in VIDEO_EXTS | IMAGE_EXTS else default


class Obtainer:
    def __init__(
        self,
        cache_dir: Path,
        client: httpx.Client,
        *,
        ytdlp: Callable[..., Path] = run_ytdlp,
        resolvers: dict[str, Callable[[str], list[Media]]] | None = None,
        log: Callable[[str], None] = print,
    ) -> None:
        self._cache = cache_dir
        self._client = client
        self._ytdlp = ytdlp
        self._resolvers = resolvers or {"douyin": resolve_douyin, "rednote": resolve_rednote, "og": og_media}
        self._log = log

    def obtain(self, entry: dict, run_root: Path) -> list[Path]:
        if entry.get("file"):
            path = (run_root / entry["file"]).resolve()
            if run_root.resolve() not in path.parents or not path.exists():
                raise PipelineError("fetch", f"File upload {entry['file']} nggak ketemu. Upload ulang di brief.")
            return [path]
        url = entry["url"]
        key = cache_key(url)
        cached = sorted(self._cache.glob(f"{key}_*"))
        cached = [p for p in cached if not p.name.endswith((".part", ".tmp.mp4"))]
        if cached:
            return cached
        kind = link_kind(url)
        if kind == "direct":
            return [download(self._client, url, self._cache / f"{key}_0{_suffix(url, '.bin')}", step="fetch")]
        errors: list[str] = []
        try:
            return [self._ytdlp(url, self._cache / f"{key}_0.mp4", step="fetch", timeout_s=YTDLP_TIMEOUT_S)]
        except PipelineError as exc:
            errors.append(f"yt-dlp: {exc.message.splitlines()[0][:120]}")
        for name in [kind, "og"]:
            resolver: Any = self._resolvers.get(name)
            if resolver is None:
                continue
            try:
                media = resolver(url)
            except (PipelineError, httpx.HTTPError) as exc:
                errors.append(f"{name}: {getattr(exc, 'message', str(exc))[:120]}")
                continue
            if media:
                return self._download(media, key)
        raise PipelineError("fetch", f"Link {kind} nggak bisa di-download ({'; '.join(errors)}). Coba link lain atau upload file-nya.")

    def _download(self, media: list[Media], key: str) -> list[Path]:
        videos = [m for m in media if m.kind == "video"]
        if videos:
            last = None
            for item in videos:
                try:
                    return [download(self._client, item.url, self._cache / f"{key}_0.mp4", step="fetch")]
                except PipelineError as exc:
                    last = exc
            raise last  # type: ignore[misc]
        return [
            download(self._client, item.url, self._cache / f"{key}_{i}{_suffix(item.url, '.jpg')}", step="fetch")
            for i, item in enumerate(media)
        ]
