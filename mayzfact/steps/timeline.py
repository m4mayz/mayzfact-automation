"""Step timeline: detik → frame, tentuin layout tiap shot, caption per kata + card countdown, tulis props buat Remotion."""

from __future__ import annotations

import math
import re
from typing import Callable

from mayzfact.countdown import parse_countdown
from mayzfact.errors import PipelineError
from mayzfact.media import FRAME_H, FRAME_W, PHOTO_ZOOM, fg_height, layout_for
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import beat_texts
from mayzfact.timing import beat_offsets, beat_timings, word_timings

FPS = 30
CAPTION_HOLD_S = 0.4  # kata terakhir tetap tampil sebentar pas jeda
CAPTION_WHITE = "#ffffff"
CAPTION_COLORS = ("#22d3ee", "#4ade80", "#facc15")
LONG_WORD = 6
_EDGE_PUNCT = re.compile(r"^[^\w']+|[^\w']+$")


def to_frame(seconds: float, fps: int = FPS) -> int:
    return int(math.floor(seconds * fps + 0.5))


def _shot_entries(shots: list[dict], total: int, fg_min_ratio: float) -> list[dict]:
    starts = [0] + [to_frame(s["start_s"]) for s in shots[1:]]
    entries = []
    for index, shot in enumerate(shots):
        end = starts[index + 1] if index + 1 < len(shots) else total
        if end <= starts[index]:
            raise PipelineError("timeline", f"Shot {index + 1} jadi 0 frame setelah dibulatin.")
        layout = layout_for(shot["width"], shot["height"])
        entry = {
            "src": shot["file"].replace("\\", "/"),
            "kind": shot["kind"],
            "layout": layout,
            "from": starts[index],
            "durationInFrames": end - starts[index],
        }
        if layout == "blur":
            entry["fgHeight"] = fg_height(shot["width"], shot["height"], fg_min_ratio)
        entries.append(entry)
    return entries


def _countdown(beats: list[dict], alignment: dict, audio_duration_s: float, entries: list[dict],
               total: int) -> tuple[list[dict], list[tuple[float, float]], set[str]]:
    """Card per beat countdown + rentang detik beat countdown (buat ngumpetin caption) + kata-kata nama subjek."""
    texts = beat_texts(beats)
    timings = beat_timings(texts, alignment, audio_duration_s)
    ends = alignment["character_end_times_seconds"]
    cards, spans, subject_words = [], [], set()
    for text, offset, timing in zip(texts, beat_offsets(texts), timings):
        countdown = parse_countdown(text)
        if not countdown:
            continue
        subject_words |= {w.lower() for w in re.findall(r"[\w']+", countdown.subject)}
        if countdown.number is None:
            continue
        spans.append((timing["start_s"], timing["end_s"]))
        number_from = to_frame(timing["start_s"])
        card_from = to_frame(float(ends[offset + countdown.number_end]))
        card_end = min(to_frame(timing["end_s"]), total)
        shot = next(e for e in reversed(entries) if e["from"] <= card_from)
        cards.append({
            "number": countdown.number, "label": countdown.subject.upper(),
            "numberFrom": number_from, "numberDuration": max(1, card_from - number_from),
            "cardFrom": card_from, "cardDuration": max(1, card_end - card_from),
            "src": shot["src"], "kind": shot["kind"], "clipOffset": card_from - shot["from"],
        })
    return cards, spans, subject_words


def _captions(alignment: dict, audio_duration_s: float, spans: list[tuple[float, float]], subject_words: set[str],
              total: int) -> list[dict]:
    words = word_timings(alignment)
    captions = []
    colored = 0
    for index, word in enumerate(words):
        if any(start <= word["start_s"] < end for start, end in spans):
            continue
        text = _EDGE_PUNCT.sub("", word["text"])
        if not text:
            continue
        next_start = words[index + 1]["start_s"] if index + 1 < len(words) else audio_duration_s
        start = to_frame(word["start_s"])
        end = min(to_frame(min(next_start, word["end_s"] + CAPTION_HOLD_S)), total)
        color = CAPTION_WHITE
        if len(text) >= LONG_WORD or text.lower() in subject_words:
            color = CAPTION_COLORS[colored % len(CAPTION_COLORS)]
            colored += 1
        captions.append({"text": text.upper(), "from": start, "durationInFrames": max(1, end - start), "color": color})
    return captions


def build_timeline(
    clips: dict,
    audio_duration_s: float,
    fg_min_ratio: float,
    *,
    script: dict | None = None,
    alignment: dict | None = None,
    log: Callable[[str], None] = print,
) -> dict:
    shots = clips["shots"]
    if not shots:
        raise PipelineError("timeline", "clips.json kosong.")
    total = math.ceil(audio_duration_s * FPS - 1e-6)
    entries = _shot_entries(shots, total, fg_min_ratio)
    countdown: list[dict] = []
    captions: list[dict] = []
    if script and alignment:
        try:
            countdown, spans, subject_words = _countdown(script["beats"], alignment, audio_duration_s, entries, total)
            captions = _captions(alignment, audio_duration_s, spans, subject_words, total)
        except PipelineError as exc:  # caption/card cuma hiasan: timeline tetap jadi tanpa itu
            log(f"[timeline] caption & countdown dilewat: {exc.message.splitlines()[0]}")
            countdown, captions = [], []
    return {
        "fps": FPS,
        "width": FRAME_W,
        "height": FRAME_H,
        "durationInFrames": total,
        "audio": "voice.mp3",
        "photoZoom": PHOTO_ZOOM,
        "shots": entries,
        "countdown": countdown,
        "captions": captions,
    }


def run_timeline(paths: RunPaths, clips: dict, tts: dict, *, fg_min_ratio: float, script: dict | None = None,
                 log: Callable[[str], None] = print) -> dict:
    data = build_timeline(clips, tts["duration_s"], fg_min_ratio, script=script, alignment=tts.get("alignment"), log=log)
    write_json_atomic(paths.timeline_json, data)
    return data
