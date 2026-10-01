"""Step clips: pecah beat jadi shot, pilih klip stock per shot, download + normalisasi."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import urlparse

import httpx

from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import normalize_video, probe
from mayzfact.media import downscale_factor, pick_rendition, tier
from mayzfact.net import download
from mayzfact.photo import normalize_photo
from mayzfact.providers.types import Candidate
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import beat_texts
from mayzfact.timing import beat_timings

PROVIDER_ORDER = {"pexels": 0, "pixabay": 1}
MIN_EXTRA_S = 0.5
MAX_PICK_ATTEMPTS = 3


@dataclass(frozen=True)
class ShotSlot:
    index: int
    beat: int
    start_s: float
    end_s: float
    media: str
    part: int = 0  # urutan shot di dalam beat-nya (0 = shot pertama)

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


class MediaSearch(Protocol):
    def candidates(self, kind: str, query: str) -> list[Candidate]: ...


def split_shots(timings: list[dict], beats: list[dict], max_shot_s: float) -> list[ShotSlot]:
    slots: list[ShotSlot] = []
    for beat_index, (timing, beat) in enumerate(zip(timings, beats, strict=True)):
        start, end = timing["start_s"], timing["end_s"]
        count = max(1, math.ceil((end - start) / max_shot_s - 1e-9))
        step = (end - start) / count
        for k in range(count):
            shot_start = start + k * step
            shot_end = end if k == count - 1 else start + (k + 1) * step
            slots.append(ShotSlot(len(slots), beat_index, round(shot_start, 3), round(shot_end, 3), beat["media"], k))
    return slots


def choose_candidate(
    candidates: list[Candidate], used: set[tuple[str, str]], min_duration_s: float, fg_min_ratio: float
) -> Candidate | None:
    usable = [
        c
        for c in candidates
        if (c.provider, c.id) not in used
        and c.renditions
        and (c.kind == "photo" or (c.duration_s or 0) >= min_duration_s)
    ]
    if not usable:
        return None
    return min(usable, key=lambda c: (tier(c, fg_min_ratio), c.rank, PROVIDER_ORDER.get(c.provider, 9)))


def pick_for_slot(
    slot: ShotSlot,
    beat: dict,
    fallback_query: str,
    search: MediaSearch,
    used: set[tuple[str, str]],
    fg_min_ratio: float,
) -> tuple[Candidate, str]:
    other = "photo" if slot.media == "video" else "video"
    # Shot ke-2, ke-3 dari beat yang sama mulai dari query berikutnya, biar visualnya nggak seragam.
    queries = list(beat["queries"])
    if queries:
        start = slot.part % len(queries)
        queries = queries[start:] + queries[:start]
    attempts = (
        [(slot.media, q) for q in queries]
        + [(other, q) for q in queries]
        + [(slot.media, fallback_query), (other, fallback_query)]
    )
    min_duration = slot.duration_s + MIN_EXTRA_S
    for kind, query in attempts:
        found = choose_candidate(search.candidates(kind, query), used, min_duration, fg_min_ratio)
        if found is not None:
            return found, query
    raise PipelineError(
        "clips",
        f'Beat {slot.beat + 1} ("{beat["text"][:50]}") nggak dapet klip video/foto sama sekali, termasuk pakai fallback_query.',
    )


def materialize(
    slot: ShotSlot,
    candidate: Candidate,
    query: str,
    paths: RunPaths,
    client: httpx.Client,
    media_cache: Path,
    fg_min_ratio: float,
) -> dict:
    rendition = pick_rendition(candidate, fg_min_ratio)
    default_ext = ".mp4" if candidate.kind == "video" else ".jpg"
    suffix = Path(urlparse(rendition.url).path).suffix.lower() or default_ext
    raw_name = f"{candidate.provider}_{candidate.kind}_{candidate.id}_{rendition.width}x{rendition.height}{suffix}"
    raw = download(client, rendition.url, media_cache / raw_name, step="clips")
    try:
        if candidate.kind == "video":
            dest = paths.clips_dir / f"shot_{slot.index + 1:02d}.mp4"
            start = 0.5 if (candidate.duration_s or 0) >= slot.duration_s + 1.0 else 0.0
            scale = downscale_factor(rendition.width, rendition.height, fg_min_ratio)
            normalize_video(raw, dest, start_s=start, duration_s=slot.duration_s + 0.2, scale=scale)
            info = probe(dest, "clips")
            width, height = info["width"], info["height"]
        else:
            dest = paths.clips_dir / f"shot_{slot.index + 1:02d}.jpg"
            width, height = normalize_photo(raw, dest, fg_min_ratio=fg_min_ratio)
    except (PipelineError, OSError, ValueError) as exc:
        # File rusak jangan dipakai ulang dari cache di run berikutnya.
        raw.unlink(missing_ok=True)
        raise PipelineError("clips", f"File {raw.name} nggak bisa diproses: {exc}") from exc
    return {
        "index": slot.index,
        "beat": slot.beat,
        "start_s": slot.start_s,
        "end_s": slot.end_s,
        "kind": candidate.kind,
        "file": f"clips/{dest.name}",
        "width": width,
        "height": height,
        "provider": candidate.provider,
        "provider_id": candidate.id,
        "page_url": candidate.page_url,
        "author": candidate.author,
        "query": query,
    }


def run_clips(
    paths: RunPaths,
    script: dict,
    tts: dict,
    search: MediaSearch,
    client: httpx.Client,
    *,
    max_shot_s: float,
    fg_min_ratio: float,
    media_cache: Path,
    log: Callable[[str], None] = print,
) -> dict:
    timings = beat_timings(beat_texts(script["beats"]), tts["alignment"], tts["duration_s"])
    slots = split_shots(timings, script["beats"], max_shot_s)
    paths.clips_dir.mkdir(parents=True, exist_ok=True)
    for old in paths.clips_dir.glob("shot_*"):
        old.unlink()
    used: set[tuple[str, str]] = set()
    shots = []
    for slot in slots:
        beat = script["beats"][slot.beat]
        for attempt in range(MAX_PICK_ATTEMPTS):
            candidate, query = pick_for_slot(slot, beat, script["fallback_query"], search, used, fg_min_ratio)
            used.add((candidate.provider, candidate.id))
            log(f"[clips] shot {slot.index + 1}/{len(slots)}: {candidate.provider} {candidate.kind} {candidate.id} ({query})")
            try:
                shots.append(materialize(slot, candidate, query, paths, client, media_cache, fg_min_ratio))
                break
            except PipelineError as exc:
                # Link mati / file rusak: ganti ke kandidat berikutnya, jangan stop seluruh step.
                if attempt == MAX_PICK_ATTEMPTS - 1:
                    raise
                log(f"[clips] {candidate.provider} {candidate.id} gagal dipakai, ganti klip: {exc.message[:120]}")
    data = {"shots": shots}
    write_json_atomic(paths.clips_json, data)
    return data
