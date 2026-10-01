"""Step clips: pecah beat jadi shot, pilih klip stock per shot, download + normalisasi."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from mayzfact.errors import PipelineError
from mayzfact.media import tier
from mayzfact.providers.types import Candidate

PROVIDER_ORDER = {"pexels": 0, "pixabay": 1}
MIN_EXTRA_S = 0.5


@dataclass(frozen=True)
class ShotSlot:
    index: int
    beat: int
    start_s: float
    end_s: float
    media: str

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
            slots.append(ShotSlot(len(slots), beat_index, round(shot_start, 3), round(shot_end, 3), beat["media"]))
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
    attempts = (
        [(slot.media, q) for q in beat["queries"]]
        + [(other, q) for q in beat["queries"]]
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


def select_clips(
    slots: list[ShotSlot], beats: list[dict], fallback_query: str, search: MediaSearch, fg_min_ratio: float
) -> list[tuple[ShotSlot, Candidate, str]]:
    used: set[tuple[str, str]] = set()
    picks: list[tuple[ShotSlot, Candidate, str]] = []
    for slot in slots:
        candidate, query = pick_for_slot(slot, beats[slot.beat], fallback_query, search, used, fg_min_ratio)
        used.add((candidate.provider, candidate.id))
        picks.append((slot, candidate, query))
    return picks
