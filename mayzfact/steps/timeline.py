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
SFX_VOLUME = {"hook": 0.8, "number": 0.9, "subject": 0.7, "cut": 0.35}
SFX_LEAD_FRAMES = 3  # whoosh mulai sedikit sebelum gambar ganti
# Pembuka ngikutin source i2xag: frame 0-1 "cover" (still dari caption berwarna pertama, biar jadi thumbnail),
# frame 2-6 video mulai zoom-in + blur terus zoom out ke normal. Barengan SFX hook.
INTRO_COVER_FRAMES = 2
INTRO_FRAMES = 7
INTRO_COVER_DEFAULT = 45  # 1.5 detik, kalau nggak ada caption berwarna
CAPTION_SETTLE_FRAMES = 4  # caption udah tajam (animasi masuk 3 frame)
BGM_VOLUME = 0.12
BGM_FADE_FRAMES = 30
TAIL_FRAMES = 6  # klip dipotong durasi shot + 0.2 detik (normalize_local)
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
               total: int, log: Callable[[str], None]) -> tuple[list[dict], list[tuple[float, float]], set[str]]:
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
        clip_frames = shot["durationInFrames"] + TAIL_FRAMES
        if card_from - shot["from"] + (card_end - card_from) > clip_frames:  # run lama: beat countdown kepotong 2 shot
            log(f"[timeline] klip card #{countdown.number} lebih pendek dari card-nya; "
                "beat countdown ini masih kepotong. Ulang pakai --from plan (manual) atau --from clips (auto).")
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


def _sound(audio: dict | None, entries: list[dict], countdown: list[dict]) -> tuple[dict | None, list[dict]]:
    if not audio:
        return None, []
    bgm = {"src": audio["bgm"], "volume": BGM_VOLUME, "fadeOutFrames": BGM_FADE_FRAMES} if audio.get("bgm") else None
    files = audio.get("sfx", {})
    sfx: list[dict] = []

    def add(event: str, frame: int) -> None:
        if event in files:
            sfx.append({"src": files[event], "from": max(0, frame), "volume": SFX_VOLUME[event]})

    add("hook", 0)
    for card in countdown:
        add("number", card["numberFrom"])
        add("subject", card["cardFrom"] - SFX_LEAD_FRAMES)
    for entry in entries[1:]:
        covered = any(c["numberFrom"] <= entry["from"] < c["cardFrom"] + c["cardDuration"] for c in countdown)
        if not covered:  # pergantian ke card udah punya bunyi sendiri
            add("cut", entry["from"] - SFX_LEAD_FRAMES)
    sfx.sort(key=lambda s: s["from"])
    return bgm, sfx


def _intro(captions: list[dict]) -> dict:
    colored = next((c for c in captions if c["color"] != CAPTION_WHITE), None)
    cover = colored["from"] + CAPTION_SETTLE_FRAMES if colored else INTRO_COVER_DEFAULT
    return {"coverFrames": INTRO_COVER_FRAMES, "durationInFrames": INTRO_FRAMES, "coverFrame": cover}


def build_timeline(
    clips: dict,
    audio_duration_s: float,
    fg_min_ratio: float,
    *,
    script: dict | None = None,
    alignment: dict | None = None,
    audio: dict | None = None,
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
            countdown, spans, subject_words = _countdown(script["beats"], alignment, audio_duration_s, entries, total, log)
            captions = _captions(alignment, audio_duration_s, spans, subject_words, total)
        except (PipelineError, IndexError, KeyError) as exc:  # caption/card cuma hiasan: timeline tetap jadi tanpa itu
            reason = exc.message.splitlines()[0] if isinstance(exc, PipelineError) else f"alignment nggak lengkap ({exc!r})"
            log(f"[timeline] caption & countdown dilewat: {reason}")
            countdown, captions = [], []
    bgm, sfx = _sound(audio, entries, countdown)
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
        "bgm": bgm,
        "sfx": sfx,
        "intro": _intro(captions) if audio and "hook" in audio.get("sfx", {}) else None,
    }


def run_timeline(paths: RunPaths, clips: dict, tts: dict, *, fg_min_ratio: float, script: dict | None = None,
                 audio: dict | None = None, log: Callable[[str], None] = print) -> dict:
    data = build_timeline(clips, tts["duration_s"], fg_min_ratio, script=script, alignment=tts.get("alignment"),
                          audio=audio, log=log)
    write_json_atomic(paths.timeline_json, data)
    return data
