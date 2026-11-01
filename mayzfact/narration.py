"""Kontrak naskah Top 3; helper murni, tanpa API atau perubahan file run."""
from __future__ import annotations

import math
import re

from mayzfact.countdown import COUNTDOWN_DELIMITER, Countdown, parse_countdown
from mayzfact.cta import cta_kinds
from mayzfact.models import Script
from mayzfact.text import clean_text


def validate_video_speed(video_speed: float) -> None:
    if not math.isfinite(video_speed) or video_speed <= 0:
        raise ValueError('video_speed must be positive and finite.')


def top3_word_range(video_speed: float) -> tuple[int, int, int]:
    validate_video_speed(video_speed)
    scale = video_speed / 1.1
    return round(80 * scale), math.ceil(76 * scale), math.floor(84 * scale)


def source_countdown_entries(source_text: str) -> list[tuple[Countdown, int]]:
    """Heading dan offset di teks clean, termasuk heading lintas chunk."""
    text = clean_text(source_text)
    headings = re.finditer(rf"\bnumber\s+(\w+)\s*{COUNTDOWN_DELIMITER}\s*([^.!?]+)[.!?]?(?=\s|$)", text, re.I)
    return [(c, m.start()) for m in headings if (c := parse_countdown(f"Number {m[1]}, {m[2]}.")) and c.number is not None]


def source_countdowns(source_text: str) -> list[Countdown]:
    return [c for c, _ in source_countdown_entries(source_text)]


def top3_problems(script: Script, source_text: str) -> list[str]:
    found = [c for b in script.beats if (c := parse_countdown(b.text)) and c.number is not None]
    problems = []
    if [c.number for c in found] != [3, 2, 1]:
        problems.append('Top 3 requires exactly Number three, Number two, Number one in that order.')
    original = source_countdowns(source_text)
    for number in [3, 2, 1]:
        source = [c for c in original if c.number == number]
        if len(source) != 1:
            problems.append(f'Top 3 source must have exactly one heading for Number {number}.')
            continue
        target = [c for c in found if c.number == number]
        norm = lambda s: ' '.join(s.casefold().split())
        if len(target) == 1 and norm(target[0].subject) != norm(source[0].subject):
            problems.append(f'Top 3 Number {number} subject must match the original source: {source[0].subject}.')
    indices = [(i, c) for i, b in enumerate(script.beats) if (c := parse_countdown(b.text)) and c.number is not None]
    for i, c in indices:
        name = {3: 'three', 2: 'two', 1: 'one'}.get(c.number)
        if name and script.beats[i].text != f'Number {name}, {c.subject}.':
            problems.append('Top 3 announcements must use Number N, [subject]. with the number spelled out.')
    ctas = cta_beat_indices(script.beats)
    one = next((i for i, c in indices if c.number == 1), None)
    if one is None or not 1 <= len(ctas) <= 2 or ctas != list(range(one - len(ctas), one)):
        problems.append('Top 3 CTA must be one contiguous block of 1-2 beats immediately before Number one.')
    have = cta_kinds_for_beats([script.beats[i] for i in ctas])
    if have != {'like', 'subscribe', 'comment'}:
        problems.append('Top 3 CTA must invite viewers to like, subscribe, and comment.')
    first = indices[0][0] if indices else len(script.beats)
    hook = ' '.join(b.text for b in script.beats[:first])
    if re.search(r'\b(?:these|top)\s+(?:five|5|four|4)\b', hook, re.I):
        problems.append('Top 3 hook must describe three items, not five or four.')
    return problems


def cta_beat_indices(beats: list) -> list[int]:
    """Beat CTA eksplisit; dipakai bersama oleh validasi, plan, dan audit operator."""
    return [i for i, b in enumerate(beats) if cta_kinds(b['text'] if isinstance(b, dict) else b.text)]


def cta_kinds_for_beats(beats: list) -> set[str]:
    return set().union(*(cta_kinds(b['text'] if isinstance(b, dict) else b.text) for b in beats))
