"""Step clips: pecah beat jadi shot, pilih klip stock per shot, download + normalisasi."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import urlparse

import httpx

from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import normalize_video, probe
from mayzfact.matching import hook_slot_map, rerank_key
from mayzfact.media import downscale_factor, pick_rendition, tier
from mayzfact.net import download
from mayzfact.photo import normalize_photo
from mayzfact.providers.types import Candidate
from mayzfact.shots import ShotSlot, beat_subjects, split_shots  # noqa: F401
from mayzfact.steps.fetch import normalize_local  # noqa: F401
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import beat_texts
from mayzfact.timing import beat_timings

PROVIDER_ORDER = {"pexels": 0, "pixabay": 1}
MIN_EXTRA_S = 0.5
MAX_PICK_ATTEMPTS = 3
# ponytail: batas dari 1 run i2xag (foto nyambung 0.094-0.163, video meleset 0.003-0.093); kalibrasi ulang kalau model ganti
RELEVANCE_MIN = 0.10
# "Number five, horseshoe crab." / "Number 3: the platypus!" → subjek yang lagi dibahas


class MediaSearch(Protocol):
    def candidates(self, kind: str, query: str) -> list[Candidate]: ...


class Scorer(Protocol):
    def score(self, text: str, candidates: list[Candidate]) -> list[float]: ...


def _usable(candidates: list[Candidate], used: set[tuple[str, str]], min_duration_s: float) -> list[Candidate]:
    return [
        c
        for c in candidates
        if (c.provider, c.id) not in used and c.renditions and (c.kind == "photo" or (c.duration_s or 0) >= min_duration_s)
    ]




def choose_candidate(
    candidates: list[Candidate], used: set[tuple[str, str]], min_duration_s: float, fg_min_ratio: float
) -> Candidate | None:
    usable = _usable(candidates, used, min_duration_s)
    if not usable:
        return None
    return min(usable, key=lambda c: (tier(c, fg_min_ratio), c.rank, PROVIDER_ORDER.get(c.provider, 9)))




def _best_scored(
    kind: str,
    queries: list[str],
    search: MediaSearch,
    used: set[tuple[str, str]],
    min_duration_s: float,
    fg_min_ratio: float,
    scorer: Scorer,
    subject: str | None = None,
) -> tuple[Candidate, str, float] | None:
    """Kandidat terbaik dari semua query satu grup.

    Dinilai pakai nama subjek (misalnya "sturgeon") kalau ada: query lengkap kayak "sturgeon river underwater"
    bikin SigLIP nyocokin pemandangan sungainya, bukan hewannya. Tanpa subjek, pakai query yang nemuin kandidat.
    """
    seen: set[tuple[str, str]] = set()
    scored: list[tuple[Candidate, str, float]] = []
    for query in queries:
        fresh = [c for c in _usable(search.candidates(kind, query), used, min_duration_s) if (c.provider, c.id) not in seen]
        seen.update((c.provider, c.id) for c in fresh)
        if fresh:
            scored += [(c, query, score) for c, score in zip(fresh, scorer.score(subject or query, fresh))]
    if not scored:
        return None
    return min(scored, key=lambda item: rerank_key(item[2], tier(item[0], fg_min_ratio), PROVIDER_ORDER.get(item[0].provider, 9)))


def pick_for_slot(
    slot: ShotSlot,
    beat: dict,
    fallback_query: str,
    search: MediaSearch,
    used: set[tuple[str, str]],
    fg_min_ratio: float,
    scorer: Scorer | None = None,
    subject: str | None = None,
) -> tuple[Candidate, str]:
    other = "photo" if slot.media == "video" else "video"
    # Shot ke-2, ke-3 dari beat yang sama mulai dari query berikutnya, biar visualnya nggak seragam.
    queries = list(beat["queries"])
    if queries:
        start = slot.part % len(queries)
        queries = queries[start:] + queries[:start]
    groups = [(slot.media, queries), (other, queries), (slot.media, [fallback_query]), (other, [fallback_query])]
    min_duration = slot.duration_s + MIN_EXTRA_S
    if scorer is None:
        for kind, group_queries in groups:
            for query in group_queries:
                found = choose_candidate(search.candidates(kind, query), used, min_duration, fg_min_ratio)
                if found is not None:
                    return found, query
    else:
        weak: tuple[Candidate, str, float] | None = None
        for kind, group_queries in groups:
            best = _best_scored(kind, group_queries, search, used, min_duration, fg_min_ratio, scorer, subject)
            if best is None:
                continue
            if best[2] >= RELEVANCE_MIN:
                return best[0], best[1]
            # Skor rendah (misalnya video hewan langka yang nggak ada di stock): coba grup berikutnya
            # (biasanya foto hewan yang sama), terus ambil yang skornya paling tinggi.
            if weak is None or best[2] > weak[2]:
                weak = best
        if weak is not None:
            return weak[0], weak[1]
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




def _hook_entry(slot: ShotSlot, segment: dict, paths: RunPaths, fg_min_ratio: float, log: Callable[[str], None]) -> dict | None:
    winner = segment["winner"]
    try:
        out = normalize_local(slot.index, slot.start_s, slot.end_s, paths.root / winner["file"], winner["kind"],
                              winner["offset_s"], paths, fg_min_ratio)
    except PipelineError as exc:
        log(f"[clips] hook segmen {segment['index'] + 1} gagal dipakai, pakai klip biasa: {exc.message}")
        return None
    return {
        "index": slot.index, "beat": slot.beat, "start_s": slot.start_s, "end_s": slot.end_s, **out,
        "provider": winner["provider"], "provider_id": winner["provider_id"],
        "page_url": winner["page_url"], "author": winner["author"],
        "query": f"hook:{segment['index']}", "hook_segment": segment["index"], "match": winner["label"],
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
    hook: dict | None = None,
    scorer: Scorer | None = None,
    hook_seconds: float = 10.0,
) -> dict:
    timings = beat_timings(beat_texts(script["beats"]), tts["alignment"], tts["duration_s"])
    slots = split_shots(timings, script["beats"], max_shot_s)
    paths.clips_dir.mkdir(parents=True, exist_ok=True)
    for old in paths.clips_dir.glob("shot_*"):
        old.unlink()
    subjects = beat_subjects(script["beats"])
    winners = [segment for segment in (hook or {}).get("segments", []) if segment.get("winner")]
    hook_map = hook_slot_map(slots, len(winners), hook_seconds)
    used: set[tuple[str, str]] = {(s["winner"]["provider"], s["winner"]["provider_id"]) for s in winners}
    shots = []
    for slot in slots:
        if slot.index in hook_map:
            entry = _hook_entry(slot, winners[hook_map[slot.index]], paths, fg_min_ratio, log)
            if entry is not None:
                log(f"[clips] shot {slot.index + 1}/{len(slots)}: hook {entry['provider']} {entry['provider_id']} ({entry['match']})")
                shots.append(entry)
                continue
        beat = script["beats"][slot.beat]
        for attempt in range(MAX_PICK_ATTEMPTS):
            candidate, query = pick_for_slot(
                slot, beat, script["fallback_query"], search, used, fg_min_ratio, scorer, subjects[slot.beat]
            )
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
