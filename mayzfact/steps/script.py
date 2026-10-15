"""Step script: rewrite transcript jadi naskah baru (aturan + prompt)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Protocol

from mayzfact.countdown import parse_countdown
from mayzfact.emoji import allowed_emoji_line
from mayzfact.errors import PipelineError
from mayzfact.models import Script
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import clean_text, ngram_overlap, words

WORDS_PER_SECOND = 2.6
WORD_TOLERANCE = 0.15
PHOTO_SHARE_RANGE = (0.15, 0.45)
MAX_NGRAM_OVERLAP = 0.15
MAX_BEAT_WORDS = 10  # ±3.5 detik dengan 2.6 kata/detik
CTA_WORDS = ("like", "subscribe", "comment")  # kata pemicu animasi CTA; kalau source nyebut, naskah juga harus
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "rewrite.md"


def target_duration(source_duration_s: float, ratio: float, minimum_s: float) -> float:
    return max(minimum_s, ratio * source_duration_s)


def word_range(duration_s: float) -> tuple[int, int, int]:
    target = round(duration_s * WORDS_PER_SECOND)
    return target, math.ceil(target * (1 - WORD_TOLERANCE)), math.floor(target * (1 + WORD_TOLERANCE))


def normalize_script(script: Script) -> Script:
    """Bersihin teks & keyword, lalu paksa beat pertama jadi video."""
    beats = [
        b.model_copy(update={
            "text": clean_text(b.text), "queries": [q.strip() for q in b.queries if q.strip()],
            "subject": " ".join(b.subject.split()),
        })
        for b in script.beats
    ]
    if beats:
        beats[0] = beats[0].model_copy(update={"media": "video"})
    return Script(beats=beats, fallback_query=" ".join(script.fallback_query.split()))


def check_script(script: Script, source_text: str, duration_s: float,
                 bgm_choices: list[str] | None = None) -> tuple[list[str], float]:
    """Balikin (daftar masalah, overlap). Pesan pakai English biar bisa ditempel balik ke agent mana pun."""
    if not script.beats:
        return ["The script has no beats."], 0.0
    problems: list[str] = []
    full_text = " ".join(b.text for b in script.beats)
    count = len(words(full_text))
    _, low, high = word_range(duration_s)
    if not low <= count <= high:
        problems.append(f"The narration has {count} words; it must have between {low} and {high}.")
    share = sum(b.media == "photo" for b in script.beats) / len(script.beats)
    share_low, share_high = PHOTO_SHARE_RANGE
    if not share_low <= share <= share_high:
        problems.append(
            f"{share:.0%} of the beats use a photo; it must be between {share_low:.0%} and {share_high:.0%}."
        )
    for number, beat in enumerate(script.beats, start=1):
        if not beat.text:
            problems.append(f"Beat {number} has empty text.")
        beat_words = len(words(beat.text))
        if beat_words > MAX_BEAT_WORDS:
            problems.append(
                f"Beat {number} has {beat_words} words; split it so every beat has at most {MAX_BEAT_WORDS} words."
            )
        if not beat.queries:
            problems.append(f"Beat {number} has no search queries.")
    countdown_indices = [
        (i, parse_countdown(b.text))
        for i, b in enumerate(script.beats)
        if parse_countdown(b.text) and parse_countdown(b.text).number is not None
    ]
    for idx_in_list, (beat_idx, _) in enumerate(countdown_indices):
        next_beat_idx = (
            countdown_indices[idx_in_list + 1][0]
            if idx_in_list + 1 < len(countdown_indices)
            else len(script.beats)
        )
        explanation_count = next_beat_idx - (beat_idx + 1)
        if explanation_count < 2:
            problems.append(
                f"Countdown item '{script.beats[beat_idx].text.strip()}' has only {explanation_count} explanation beat(s); "
                f"each item must have at least 2 beats describing it."
            )
    if not script.fallback_query:
        problems.append("fallback_query is empty.")
    source_words = set(words(source_text))
    script_words = set(words(full_text))
    missing_cta = [w for w in CTA_WORDS if w in source_words and w not in script_words]
    if missing_cta:
        problems.append("The source asks viewers to " + " and ".join(missing_cta)
                        + f"; the script must use the exact word(s) {', '.join(missing_cta)} too (they trigger the on-screen CTA).")
    if bgm_choices is not None and script.bgm and script.bgm not in bgm_choices:
        problems.append(f"bgm {script.bgm!r} is not in assets/bgm. Choose one of: {', '.join(bgm_choices) or '(none)'}.")
    overlap = ngram_overlap(full_text, source_text)
    if overlap > MAX_NGRAM_OVERLAP:
        problems.append(
            f"{overlap:.0%} of the 4-word phrases are copied from the source; "
            f"keep it at or below {MAX_NGRAM_OVERLAP:.0%}. Rephrase more."
        )
    return problems, overlap


def build_user_prompt(
    source: dict,
    duration_s: float,
    photo_ratio: float,
    feedback: list[str] | None = None,
    previous: Script | None = None,
) -> str:
    target, low, high = word_range(duration_s)
    lines = [
        f"Source duration: {source['duration_s']:.1f} seconds.",
        f"Target narration: about {duration_s:.0f} seconds, about {target} words in total (allowed: {low}-{high}).",
        f'About {photo_ratio:.0%} of the beats should use media "photo". The first beat must use "video".',
        "",
        "Source transcript with timestamps:",
        *(f"[{s['start']:.1f}s] {s['text']}" for s in source["transcript"]),
    ]
    if feedback:
        lines += ["", "Your previous answer was rejected:", *(f"- {p}" for p in feedback)]
        if previous is not None:
            lines += ["Previous answer:", previous.model_dump_json()]
        lines.append("Write a corrected answer.")
    return "\n".join(lines)


class ScriptWriter(Protocol):
    def write(self, system: str, user: str) -> Script: ...


def generate_script(
    source: dict, writer: ScriptWriter, *, ratio: float, minimum_s: float, photo_ratio: float
) -> dict:
    duration_s = target_duration(source["duration_s"], ratio, minimum_s)
    source_text = " ".join(s["text"] for s in source["transcript"])
    system = PROMPT_PATH.read_text(encoding="utf-8") + "\n" + allowed_emoji_line()
    feedback: list[str] | None = None
    previous: Script | None = None
    problems: list[str] = []
    for _ in range(2):
        prompt = build_user_prompt(source, duration_s, photo_ratio, feedback, previous)
        script = normalize_script(writer.write(system, prompt))
        problems, overlap = check_script(script, source_text, duration_s)
        if not problems:
            target, _, _ = word_range(duration_s)
            return {
                "target_seconds": round(duration_s, 2),
                "target_words": target,
                "word_count": len(words(" ".join(b.text for b in script.beats))),
                "ngram_overlap": round(overlap, 3),
                "fallback_query": script.fallback_query,
                "beats": [b.model_dump() for b in script.beats],
            }
        feedback, previous = problems, script
    raise PipelineError("script", "Naskah dari Gemini masih gagal dicek setelah retry: " + " ".join(problems))


def run_script(
    paths: RunPaths, source: dict, writer: ScriptWriter, *, ratio: float, minimum_s: float, photo_ratio: float
) -> dict:
    data = generate_script(source, writer, ratio=ratio, minimum_s=minimum_s, photo_ratio=photo_ratio)
    write_json_atomic(paths.script_json, data)
    return data
