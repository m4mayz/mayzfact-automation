"""Pecah beat jadi shot (maks max_shot_s per shot) dan cari subjek yang lagi dibahas tiap beat."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from mayzfact.countdown import parse_countdown
from mayzfact.text import beat_texts
from mayzfact.timing import beat_offsets, word_timings


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


def tighten_countdown(slots: list[ShotSlot], beats: list[dict], alignment: dict, box_s: float) -> list[ShotSlot]:
    """Box subjek di card cuma box_s detik setelah nama subjek mulai kedengeran, terus langsung klip berikutnya (D-038).

    Shot beat countdown dipendekin, shot pertama beat berikutnya mulai lebih awal (ngisi sisa beat countdown).
    """
    texts = beat_texts(beats)
    words = word_timings(alignment)
    offsets = beat_offsets(texts)
    out = list(slots)
    for i, slot in enumerate(out[:-1]):
        countdown = parse_countdown(texts[slot.beat])
        nxt = out[i + 1]
        if not countdown or nxt.beat != slot.beat + 1:
            continue
        number_char = offsets[slot.beat] + countdown.number_end
        after = next((k + 1 for k, w in enumerate(words) if w["char_start"] <= number_char <= w["char_end"]), None)
        if after is None or after >= len(words):
            continue
        end = round(words[after]["start_s"] + box_s, 3)
        if slot.start_s < end < slot.end_s - 0.05:
            out[i] = replace(slot, end_s=end)
            out[i + 1] = replace(nxt, start_s=end)
    return out
