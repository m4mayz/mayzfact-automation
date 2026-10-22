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


BOX_TAIL_S = 0.1  # box subjek ditutup segini setelah nama subjek selesai diucapin (source i2xag)
BOX_MIN_S = 0.5  # nama subjek pendek: box tetap tampil minimal segini


def tighten_countdown(slots: list[ShotSlot], beats: list[dict], alignment: dict) -> list[ShotSlot]:
    """Box subjek di card ditutup pas nama subjek selesai, terus langsung klip berikutnya (D-038, niru source i2xag).

    Shot beat countdown dipendekin, shot pertama beat berikutnya mulai lebih awal (ngisi jeda sisa beat countdown).
    """
    texts = beat_texts(beats)
    words = word_timings(alignment)
    offsets = beat_offsets(texts)

    def word_at(char: int) -> int | None:
        return next((k for k, w in enumerate(words) if w["char_start"] <= char <= w["char_end"]), None)

    out = list(slots)
    for i, slot in enumerate(out[:-1]):
        countdown = parse_countdown(texts[slot.beat])
        nxt = out[i + 1]
        if not countdown or nxt.beat != slot.beat + 1:
            continue
        number_word = word_at(offsets[slot.beat] + countdown.number_end)
        last_word = word_at(offsets[slot.beat] + len(texts[slot.beat].rstrip()) - 1)
        if number_word is None or last_word is None or number_word + 1 > last_word:
            continue
        name_start = words[number_word + 1]["start_s"]
        end = round(max(words[last_word]["end_s"] + BOX_TAIL_S, name_start + BOX_MIN_S), 3)
        if slot.start_s < end < slot.end_s - 0.05:
            out[i] = replace(slot, end_s=end)
            out[i + 1] = replace(nxt, start_s=end)
    return out
