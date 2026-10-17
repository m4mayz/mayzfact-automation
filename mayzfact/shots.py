"""Pecah beat jadi shot (maks max_shot_s per shot) dan cari subjek yang lagi dibahas tiap beat."""

from __future__ import annotations

import math
from dataclasses import dataclass

from mayzfact.countdown import parse_countdown


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


def split_shots(timings: list[dict], beats: list[dict], max_shot_s: float) -> list[ShotSlot]:
    slots: list[ShotSlot] = []
    for beat_index, (timing, beat) in enumerate(zip(timings, beats, strict=True)):
        start, end = timing["start_s"], timing["end_s"]
        count = 1 if parse_countdown(beat.get("text", "")) else max(1, math.ceil((end - start) / max_shot_s - 1e-9))
        step = (end - start) / count
        for k in range(count):
            shot_start = start + k * step
            shot_end = end if k == count - 1 else start + (k + 1) * step
            slots.append(ShotSlot(len(slots), beat_index, round(shot_start, 3), round(shot_end, 3), beat["media"], k))
    return slots


def beat_subjects(beats: list[dict]) -> list[str | None]:
    """Hewan/objek yang lagi dibahas tiap beat: field `subject`, atau dari beat countdown, terus dibawa ke beat berikutnya."""
    current: str | None = None
    out: list[str | None] = []
    for beat in beats:
        countdown = parse_countdown(beat.get("text", ""))
        if beat.get("subject"):
            current = beat["subject"].strip()
        elif countdown:
            current = countdown.subject.lower()
        out.append(current)
    return out
