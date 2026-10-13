"""Link/file dari brief → file media lokal (spec metode manual bagian 5)."""

from __future__ import annotations

import hashlib
import re
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
from mayzfact.manual.tiktok import resolve_tiktok
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
        self._resolvers = resolvers or {"douyin": resolve_douyin, "rednote": resolve_rednote, "tiktok": resolve_tiktok, "og": og_media}
        self._log = log

    def obtain(self, entry: dict, run_root: Path) -> list[Path]:
        if entry.get("file"):
            path = (run_root / entry["file"]).resolve()
            if run_root.resolve() not in path.parents or not path.exists():
                raise PipelineError("fetch", f"File upload {entry['file']} nggak ketemu. Upload ulang di brief.")
            return [path]
        url = entry["url"]
        key = cache_key(url)
        cached = self._cached(key)
        if cached:
            return cached
        kind = link_kind(url)
        if kind == "direct":
            return [_checked(download(self._client, url, self._cache / f"{key}_0{_suffix(url, '.bin')}", step="fetch"))]
        errors: list[str] = []
        try:
            return [_checked(self._ytdlp(url, self._cache / f"{key}_0.mp4", step="fetch", timeout_s=YTDLP_TIMEOUT_S))]
        except PipelineError as exc:
            errors.append(f"yt-dlp: {exc.message.splitlines()[0][:120]}")
        for name in [kind, "og"]:
            resolver: Any = self._resolvers.get(name)
            if resolver is None:
                continue
            try:
                media = resolver(url)
                if media:
                    return self._download(media, key)
            except Exception as exc:  # halaman pihak ketiga bisa berubah bentuk: jangan bikin fetch crash
                errors.append(f"{name}: {getattr(exc, 'message', str(exc))[:120]}")
        raise PipelineError("fetch", f"Link {kind} nggak bisa di-download ({'; '.join(errors)}). Coba link lain atau upload file-nya.")

    def _cached(self, key: str) -> list[Path]:
        """File cache {key}_N.ext, urut N angka (bukan urutan string: _2 sebelum _10). Sisa .part/.tmp nggak ikut."""
        pattern = re.compile(rf"{key}_(\d+)\.[A-Za-z0-9]+")
        found = [(int(m.group(1)), p) for p in self._cache.glob(f"{key}_*") if (m := pattern.fullmatch(p.name))]
        return [p for _, p in sorted(found)]

    def _download(self, media: list[Media], key: str) -> list[Path]:
        videos = [m for m in media if m.kind == "video"]
        if videos:
            last: PipelineError | None = None
            for item in videos:
                try:
                    return [_checked(download(self._client, item.url, self._cache / f"{key}_0.mp4", step="fetch"))]
                except PipelineError as exc:
                    last = exc
            raise last  # type: ignore[misc]
        # Foto di-download ke nama sementara dulu, baru di-rename kalau semuanya berhasil. Jadi cache nggak pernah setengah.
        temps: list[tuple[Path, Path]] = []
        try:
            for i, item in enumerate(media):
                suffix = _suffix(item.url, ".jpg")
                temp = _checked(download(self._client, item.url, self._cache / f"{key}_tmp{i}{suffix}", step="fetch"))
                temps.append((temp, self._cache / f"{key}_{i}{suffix}"))
        except PipelineError:
            for temp, _ in temps:
                temp.unlink(missing_ok=True)
            raise
        for temp, final in temps:
            temp.replace(final)
        return [final for _, final in temps]


def _checked(path: Path) -> Path:
    """Hasil download harus video/gambar beneran. HTML/audio dibuang biar nggak ke-cache selamanya."""
    if media_kind(path) is None:
        path.unlink(missing_ok=True)
        raise PipelineError("fetch", f"Hasil download {path.name} bukan video/gambar.")
    return path
