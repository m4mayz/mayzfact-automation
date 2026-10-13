"""Step hook: cari klip HOOK_SECONDS awal yang sama/mirip source (spec Fase 2 bagian 4)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import urlparse

import numpy as np

from mayzfact.embed import Encoder, can_open_image, mean_unit
from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import extract_frame, probe, sample_frames
from mayzfact.hook_queries import describe_segments, transcript_near
from mayzfact.matching import match_label, top_k
from mayzfact.media import pick_rendition
from mayzfact.net import download
from mayzfact.platforms.base import PlatformBlocked
from mayzfact.providers.types import Candidate
from mayzfact.scenes import detect_cuts, merge_cuts, segments
from mayzfact.store import RunPaths, write_json_atomic

FRAME_POSITIONS = (0.25, 0.5, 0.75)
TOP_PER_SOURCE = 8
MIN_RESULTS_BEFORE_SECOND_QUERY = 3
VERIFY_TOP = 3
VERIFY_EVERY_S = 0.5
VERIFY_MAX_S = 30.0
KEEP_CANDIDATES = 5
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


class Searcher(Protocol):
    name: str
    language: str

    def search(self, query: str) -> list[Candidate]: ...

    def download(self, candidate: Candidate, dest: Path) -> Path: ...


@dataclass
class HookDeps:
    download_source: Callable[[str, Path], Path]
    encoder: Encoder
    describe: Callable[[list[dict], list[Path]], dict[int, dict]]
    searchers: list[Any]
    fetch_thumb: Callable[[Candidate], Path | None]
    log: Callable[[str], None] = print
    close: Callable[[], None] = lambda: None


class StockSearcher:
    """Pexels + Pixabay (video & foto) sebagai satu sumber hook."""

    name = "stock"
    language = "en"

    def __init__(self, stock: Any, client: Any, fg_min_ratio: float) -> None:
        self._stock, self._client, self._fg = stock, client, fg_min_ratio

    def search(self, query: str) -> list[Candidate]:
        return self._stock.candidates("video", query) + self._stock.candidates("photo", query)

    def download(self, candidate: Candidate, dest: Path) -> Path:
        return download(self._client, pick_rendition(candidate, self._fg).url, dest, step="hook")


def _media_ext(candidate: Candidate) -> str:
    if candidate.kind == "video":
        return ".mp4"
    suffix = Path(urlparse(candidate.renditions[0].url).path).suffix.lower() if candidate.renditions else ""
    return suffix if suffix in PHOTO_EXTS else ".jpg"


def _gather(queries: dict, deps: HookDeps, skipped: dict[str, str], used: set) -> list[tuple[Any, Candidate]]:
    found: list[tuple[Any, Candidate]] = []
    seen = set(used)
    for searcher in deps.searchers:
        if searcher.name in skipped:
            continue
        for query in queries.get(searcher.language, [])[:2]:
            try:
                results = searcher.search(query)
            except PlatformBlocked as exc:
                skipped[searcher.name] = exc.reason
                deps.log(f"[hook] {searcher.name} di-skip ({exc.reason}). Login ulang: mayzfact login {searcher.name}")
                break
            except PipelineError as exc:
                deps.log(f"[hook] search {searcher.name} gagal: {exc.message[:120]}")
                break
            fresh = [c for c in results if (c.provider, c.id) not in seen][:TOP_PER_SOURCE]
            for candidate in fresh:
                seen.add((candidate.provider, candidate.id))
                found.append((searcher, candidate))
            if len(results) >= MIN_RESULTS_BEFORE_SECOND_QUERY:
                break
    return found


def _verify(searcher: Any, candidate: Candidate, seg_vec: np.ndarray, deps: HookDeps, paths: RunPaths, media_cache: Path):
    media = media_cache / f"{candidate.provider}_{candidate.kind}_{candidate.id}{_media_ext(candidate)}"
    try:
        media = searcher.download(candidate, media)
        if candidate.kind == "video":
            frames = sample_frames(
                media, paths.hook_dir / "verify" / f"{candidate.provider}_{candidate.id}",
                every_s=VERIFY_EVERY_S, max_s=VERIFY_MAX_S,
            )
            if not frames:
                raise PipelineError("hook", f"{media.name} nggak punya frame")
            sims = deps.encoder.images([p for _, p in frames]) @ seg_vec
            best = int(np.argmax(sims))
            return float(sims[best]), frames[best][0], media
        if not can_open_image(media):
            raise PipelineError("hook", f"{media.name} bukan gambar")
        return float((deps.encoder.images([media]) @ seg_vec)[0]), 0.0, media
    except (PipelineError, PlatformBlocked, OSError) as exc:
        deps.log(f"[hook] {candidate.provider} {candidate.id} gagal diverifikasi: {str(exc)[:120]}")
        if isinstance(exc, PipelineError):
            media.unlink(missing_ok=True)  # file rusak jangan dipakai ulang dari cache
        return None


def _match_segment(info, seg_vec, queries, deps, skipped, used, paths, media_cache, threshold) -> dict:
    record = {
        "index": info["index"], "start_s": info["start_s"], "end_s": info["end_s"],
        "queries": queries, "candidates": [], "winner": None,
    }
    thumbs = []
    for searcher, candidate in _gather(queries, deps, skipped, used):
        path = deps.fetch_thumb(candidate)
        if path is not None and can_open_image(path):
            thumbs.append((searcher, candidate, path))
    if not thumbs:
        deps.log(f"[hook] segmen {info['index'] + 1}: nggak ada kandidat")
        return record
    scores = [float(s) for s in deps.encoder.images([t[2] for t in thumbs]) @ seg_vec]
    order = top_k(scores, max(VERIFY_TOP, KEEP_CANDIDATES))
    record["candidates"] = [
        {"source": thumbs[j][0].name, "provider_id": thumbs[j][1].id, "thumb_score": round(scores[j], 4)}
        for j in order[:KEEP_CANDIDATES]
    ]
    best = None
    for j in order[:VERIFY_TOP]:
        searcher, candidate, _ = thumbs[j]
        verified = _verify(searcher, candidate, seg_vec, deps, paths, media_cache)
        if verified and (best is None or verified[0] > best[0]):
            best = (*verified, searcher, candidate)
    if best is None:
        deps.log(f"[hook] segmen {info['index'] + 1}: semua kandidat gagal diverifikasi")
        return record
    score, offset, media, searcher, candidate = best
    dest = paths.hook_dir / f"winner_{info['index'] + 1:02d}{media.suffix}"
    shutil.copyfile(media, dest)
    used.add((candidate.provider, candidate.id))
    record["winner"] = {
        "source": searcher.name, "provider": candidate.provider, "provider_id": candidate.id, "kind": candidate.kind,
        "file": f"hook/{dest.name}", "offset_s": offset, "score": round(score, 4),
        "label": match_label(score, threshold), "page_url": candidate.page_url, "author": candidate.author,
    }
    deps.log(f"[hook] segmen {info['index'] + 1}: {searcher.name} {candidate.id} skor {score:.3f} ({record['winner']['label']})")
    return record


def prepare_source_segments(
    paths: RunPaths, source: dict, download_source: Callable[[str, Path], Path], hook_seconds: float,
    out_dir: Path, retry_step: str = "hook",
) -> list[dict]:
    """Download source (kalau belum ada), deteksi segmen di hook_seconds awal, ambil 3 frame per segmen ke out_dir."""
    src = paths.source_mp4
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        if not src.exists():
            download_source(source["video_id"], src)
        end_s = min(hook_seconds, probe(src, "hook")["duration_s"] or 0.0)
        segs = segments(merge_cuts(detect_cuts(src, end_s)), end_s)
    except PipelineError as exc:
        raise PipelineError(
            retry_step, f"{exc.message}\nUlang step ini pakai: mayzfact run {source['video_id']} --from {retry_step}"
        ) from exc
    out = []
    for i, (start, end) in enumerate(segs):
        frames = [
            extract_frame(src, start + (end - start) * pos, out_dir / f"seg_{i + 1:02d}_{k}.jpg")
            for k, pos in enumerate(FRAME_POSITIONS)
        ]
        out.append({"index": i, "start_s": start, "end_s": end, "frames": frames,
                    "transcript": transcript_near(source["transcript"], start, end)})
    return out


def run_hook(
    paths: RunPaths, source: dict, deps: HookDeps, *, hook_seconds: float, exact_threshold: float, media_cache: Path
) -> dict:
    segs_info = prepare_source_segments(paths, source, deps.download_source, hook_seconds, paths.hook_dir)
    end_s = segs_info[-1]["end_s"] if segs_info else 0.0
    infos = [{k: s[k] for k in ("index", "start_s", "end_s", "transcript")} for s in segs_info]
    seg_frames = [s["frames"] for s in segs_info]
    segs = [(s["start_s"], s["end_s"]) for s in segs_info]
    deps.log(f"[hook] {len(segs)} segmen di {end_s:.1f} detik awal source")
    queries = deps.describe(infos, [frames[1] for frames in seg_frames]) if segs else {}
    skipped: dict[str, str] = {}
    used: set[tuple[str, str]] = set()
    results = []
    for info, frames in zip(infos, seg_frames):
        seg_vec = mean_unit(deps.encoder.images(frames))
        seg_queries = queries.get(info["index"], {"en": [], "zh": []})
        results.append(_match_segment(info, seg_vec, seg_queries, deps, skipped, used, paths, media_cache, exact_threshold))
    data = {
        "hook_seconds": hook_seconds,
        "skipped_platforms": [{"platform": name, "reason": reason} for name, reason in skipped.items()],
        "segments": results,
    }
    write_json_atomic(paths.hook_json, data)
    return data


def real_hook_deps(settings: Any, client: Any, stock: Any, encoder: Encoder, fetch_thumb: Callable, log: Callable) -> HookDeps:
    from mayzfact.platforms import browser
    from mayzfact.providers.gemini import GeminiScriptWriter
    from mayzfact.ytdlp import run_ytdlp, youtube_url

    shared = browser.SharedPlaywright()
    browsers = [
        browser.BrowserPlatform(name, client=client, headless=settings.browser_headless, playwright=shared, log=log)
        for name in settings.hook_platforms
    ]
    writer = GeminiScriptWriter(settings.gemini_api_keys, settings.gemini_model) if settings.gemini_api_keys else None

    def close() -> None:
        for platform in browsers:
            platform.close()
        shared.stop()

    return HookDeps(
        download_source=lambda video_id, dest: run_ytdlp(youtube_url(video_id), dest),
        encoder=encoder,
        describe=lambda infos, frames: describe_segments(writer, infos, frames, log),
        searchers=[*browsers, StockSearcher(stock, client, settings.fg_min_height_ratio)],
        fetch_thumb=fetch_thumb,
        log=log,
        close=close,
    )
