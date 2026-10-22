"""Step timeline: detik → frame, tentuin layout tiap shot, caption per kata + card countdown, tulis props buat Remotion."""

from __future__ import annotations

import math
import re
from typing import Any, Callable

from mayzfact.countdown import parse_countdown
from mayzfact.cta import _EDGE_PUNCT, SUBSCRIBE, is_like_cta
from mayzfact.cta import clean as _clean
from mayzfact.errors import PipelineError
from mayzfact.media import FRAME_H, FRAME_W, PHOTO_ZOOM, fg_height, layout_for
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import beat_texts
from mayzfact.timing import beat_offsets, beat_timings, word_timings
from mayzfact.voice_onset import snap_word_starts

FPS = 30
CAPTION_HOLD_S = 0.4  # kata terakhir tetap tampil sebentar pas jeda
CAPTION_WHITE = "#ffffff"
CAPTION_COLORS = ("#22d3ee", "#4ade80", "#facc15")
LONG_WORD = 6
SFX_VOLUME = {"hook": 0.8, "number": 0.9, "subject": 0.7, "cut": 0.35, "overlay": 0.35, "emoji": 0.6, "click": 0.8}
SFX_LEAD_FRAMES = 3  # whoosh mulai sedikit sebelum gambar ganti (puncak whoosh-clean di ±0.1 detik)
# Pembuka = bagian "masuk" transisi antar scene di source i2xag: scene muncul hampir putih + blur vertikal,
# cepat tajam, terangnya pudar ke normal. Barengan SFX hook.
INTRO_FRAMES = 7
OVERLAY_COLORS = ("#ff2a2a", "#ffd400")
CIRCLE_EVERY = 5  # tiap overlay ke-5 jadi lingkaran, sisanya panah (kayak source)
# Panah/lingkaran muncul (bareng quick-ting) dan selesai fade 0.5 detik sebelum ganti klip.
OVERLAY_DELAY_FRAMES = 6
OVERLAY_END_GAP_FRAMES = 15
OVERLAY_MIN_FRAMES = 15
# Emoji animasi (Fase 3C-2): muncul di kata pemicunya, tampil sampai akhir beat (maks 2.5 detik).
EMOJI_MAX_FRAMES = 75
EMOJI_MIN_FRAMES = 20
EMOJI_FIT_FRAMES = 30  # kata pemicu mepet card/CTA: mulainya dimajuin sampai emoji dapat ±1 detik
# CTA ngikutin source i2xag frame per frame: like 16 frame (klik di frame 3), subscribe 27 frame (klik di frame 13).
CTA_FRAMES = {"like": 16, "subscribe": 27}
CTA_CLICK = {"like": 4, "subscribe": 14}
CLICK_LEAD_FRAMES = 3  # puncak bunyi mouse-click di ±0.1 detik
NUMBER_LEAD_FRAMES = 6  # angka masuk ±0.2 detik sebelum "Number" kedengeran, biar card nggak kosong kelamaan
BGM_VOLUME = 0.12
BGM_FADE_FRAMES = 30
TAIL_FRAMES = 6  # klip dipotong durasi shot + 0.2 detik (normalize_local)


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


def _word_at(words: list[dict], char: int) -> int | None:
    return next((i for i, w in enumerate(words) if w["char_start"] <= char <= w["char_end"]), None)


def _countdown(beats: list[dict], alignment: dict, words: list[dict], audio_duration_s: float, entries: list[dict],
               total: int, log: Callable[[str], None]) -> tuple[list[dict], list[tuple[float, float]], set[str]]:
    """Card per beat countdown + rentang detik beat countdown (buat ngumpetin caption) + kata-kata nama subjek.

    Angka muncul sedikit sebelum "Number" kedengeran (numberAt), subject card mulai pas nama subjeknya kedengeran.
    """
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
        card_end = min(to_frame(timing["end_s"]), total)
        first = _word_at(words, offset)
        number_word = _word_at(words, offset + countdown.number_end)
        number_at = max(0, to_frame(words[first]["start_s"]) - number_from - NUMBER_LEAD_FRAMES) if first is not None else 0
        after = number_word + 1 if number_word is not None else None
        if after is not None and after < len(words) and words[after]["start_s"] < timing["end_s"]:
            card_from = to_frame(words[after]["start_s"])
        else:
            card_from = to_frame(float(ends[offset + countdown.number_end]))
        card_from = min(max(card_from, number_from + number_at + 1), card_end - 1)
        shot = next(e for e in reversed(entries) if e["from"] <= card_from)
        clip_frames = shot["durationInFrames"] + TAIL_FRAMES
        if card_from - shot["from"] + (card_end - card_from) > clip_frames:  # run lama: beat countdown kepotong 2 shot
            log(f"[timeline] klip card #{countdown.number} lebih pendek dari card-nya; "
                "beat countdown ini masih kepotong. Ulang pakai --from plan.")
        cards.append({
            "number": countdown.number, "label": countdown.subject.upper(),
            "numberFrom": number_from, "numberAt": number_at, "numberDuration": max(1, card_from - number_from),
            "cardFrom": card_from, "cardDuration": max(1, card_end - card_from),
            "src": shot["src"], "kind": shot["kind"], "clipOffset": card_from - shot["from"],
        })
    return cards, spans, subject_words


def _captions(words: list[dict], audio_duration_s: float, spans: list[tuple[float, float]], subject_words: set[str],
              total: int) -> list[dict]:
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


def _sound(audio: dict | None, entries: list[dict], countdown: list[dict], overlays: list[dict],
           emojis: list[dict], cta: list[dict]) -> tuple[dict | None, list[dict]]:
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
        add("number", card["numberFrom"] + card["numberAt"] - SFX_LEAD_FRAMES)
        add("subject", card["cardFrom"] - SFX_LEAD_FRAMES)
    for entry in entries[1:]:
        covered = any(c["numberFrom"] <= entry["from"] < c["cardFrom"] + c["cardDuration"] for c in countdown)
        if not covered:  # pergantian ke card udah punya bunyi sendiri
            add("cut", entry["from"] - SFX_LEAD_FRAMES)
    for overlay in overlays:
        add("overlay", overlay["from"])
    for emoji in emojis:
        add("emoji", emoji["from"])
    for action in cta:
        add("click", action["from"] + action["clickAt"] - CLICK_LEAD_FRAMES)
    sfx.sort(key=lambda s: s["from"])
    return bgm, sfx


def _point_ranges(timings: list[dict], marks: dict | None) -> list[tuple[int, int]] | None:
    """Rentang frame beat point (beat point yang nyambung digabung). None = nggak ada info tanda → semua shot."""
    if marks is None or not timings:
        return None
    ranges: list[tuple[int, int]] = []
    for timing, mark in zip(timings, marks["beats"]):
        if not mark.get("point"):
            continue
        start, end = to_frame(timing["start_s"]), to_frame(timing["end_s"])
        if ranges and ranges[-1][1] >= start:
            ranges[-1] = (ranges[-1][0], end)
        else:
            ranges.append((start, end))
    return ranges


def _overlays(detections: dict | None, entries: list[dict], countdown: list[dict],
              point_ranges: list[tuple[int, int]] | None) -> list[dict]:
    if not detections:
        return []
    out = []
    for entry in entries:
        points = (detections.get(entry["src"]) or {}).get("points")
        covered = any(c["numberFrom"] <= entry["from"] < c["cardFrom"] + c["cardDuration"] for c in countdown)
        if not points or covered:
            continue
        entry_end = entry["from"] + entry["durationInFrames"]
        windows = [(entry["from"], entry_end)] if point_ranges is None else [
            (max(entry["from"], a), min(entry_end, b)) for a, b in point_ranges if a < entry_end and b > entry["from"]]
        for start, end in windows:  # klip panjang (hook nyambung) bisa nutup beberapa beat point
            begin = start + OVERLAY_DELAY_FRAMES
            duration = end - OVERLAY_END_GAP_FRAMES - begin
            if duration < OVERLAY_MIN_FRAMES:
                continue
            number = len(out) + 1
            out.append({
                "type": "circle" if number % CIRCLE_EVERY == 0 else "arrow",
                "color": OVERLAY_COLORS[len(out) % len(OVERLAY_COLORS)],
                "from": begin, "durationInFrames": duration,
                "keyframes": [{"frame": entry["from"] + to_frame(p["t"]) - begin, "x": p["x"], "y": p["y"], "w": p["w"], "h": p["h"]}
                              for p in points],
            })
    return out


def _beat_of(words: list[dict], beats: list[dict]) -> list[int]:
    """Index beat buat tiap kata (dari posisi karakter di teks gabungan)."""
    texts = beat_texts(beats)
    starts = beat_offsets(texts)
    out = []
    for word in words:
        index = 0
        for i, offset in enumerate(starts):
            if word["char_start"] >= offset:
                index = i
        out.append(index)
    return out


def _cta(words: list[dict], beat_of: list[int], total: int) -> list[dict]:
    """Like/subscribe pas narasinya ngajak. Subscribe nunggu like selesai, dan dua-duanya muat sebelum video habis."""
    out: list[dict] = []
    used: set[int] = set()
    for k, word in enumerate(words):
        start = to_frame(word["start_s"])
        if _clean(word["text"]) not in SUBSCRIBE or (out and start < out[-1]["from"] + out[-1]["durationInFrames"]):
            continue
        likes = [j for j in range(k) if beat_of[j] == beat_of[k] and j not in used and is_like_cta([w["text"] for w in words], j)]
        like_from = to_frame(words[likes[-1]]["start_s"]) if likes else None
        sub_from = start if like_from is None else max(start, like_from + CTA_FRAMES["like"])
        sub_from = min(sub_from, total - CTA_FRAMES["subscribe"])  # flip terakhirnya jangan kepotong akhir video
        if like_from is not None:
            used.add(likes[-1])
            out.append({"kind": "like", "from": min(like_from, sub_from - CTA_FRAMES["like"]),
                        "durationInFrames": CTA_FRAMES["like"], "clickAt": CTA_CLICK["like"]})
        out.append({"kind": "subscribe", "from": sub_from, "durationInFrames": CTA_FRAMES["subscribe"],
                    "clickAt": CTA_CLICK["subscribe"]})
    return out


def _emojis(words: list[dict], beat_of: list[int], marks: dict | None, cta: list[dict], countdown: list[dict],
            total: int) -> list[dict]:
    """Emoji muncul di kata pemicunya dan boleh nyebrang ke beat berikutnya (kayak 🍀 di source), maksimal 2.5 detik.

    Berhenti sebelum emoji berikutnya, card countdown berikutnya, CTA, atau akhir video. Kalau nabrak CTA, mulai setelah
    CTA. Kalau kata pemicunya mepet card/CTA, mulainya dimajuin ke kata sebelumnya di beat itu (kayak 🤯 di source).
    """
    if not marks:
        return []

    def stop(frame: int) -> int:
        return min([total] + [c["numberFrom"] for c in countdown if c["numberFrom"] > frame]
                   + [c["from"] for c in cta if c["from"] > frame])

    def hits_cta(begin: int, end: int) -> bool:
        return any(c["from"] < end and begin < c["from"] + c["durationInFrames"] for c in cta)

    starts = []
    for index, mark in enumerate(marks["beats"]):
        src = marks.get("emoji", {}).get(mark.get("emoji") or "")
        in_beat = [w for w, b in zip(words, beat_of) if b == index]
        if not src or not in_beat:
            continue
        at = next((i for i, w in enumerate(in_beat)
                   if mark.get("emoji_word") and mark["emoji_word"] in re.findall(r"[\w']+", w["text"].lower())), 0)
        start = to_frame(in_beat[at]["start_s"])
        for action in sorted(cta, key=lambda c: c["from"]):
            if action["from"] <= start < action["from"] + action["durationInFrames"]:
                start = action["from"] + action["durationInFrames"]
        while at > 0 and stop(start) - start < EMOJI_FIT_FRAMES:
            earlier = to_frame(in_beat[at - 1]["start_s"])
            if hits_cta(earlier, start):
                break
            at, start = at - 1, earlier
        starts.append((start, src))
    starts.sort()
    out = []
    for i, (start, src) in enumerate(starts):
        if any(c["numberFrom"] <= start < c["cardFrom"] + c["cardDuration"] for c in countdown):
            continue  # jatuh di atas card countdown
        end = min([start + EMOJI_MAX_FRAMES, stop(start)] + [s for s, _ in starts[i + 1:i + 2]])
        if end - start >= EMOJI_MIN_FRAMES:
            out.append({"src": src, "from": start, "durationInFrames": end - start})
    return out


def build_timeline(
    clips: dict,
    audio_duration_s: float,
    fg_min_ratio: float,
    *,
    script: dict | None = None,
    alignment: dict | None = None,
    audio: dict | None = None,
    overlays: dict | None = None,
    marks: dict | None = None,
    voice_envelope: Any = None,
    log: Callable[[str], None] = print,
) -> dict:
    shots = clips["shots"]
    if not shots:
        raise PipelineError("timeline", "clips.json kosong.")
    total = math.ceil(audio_duration_s * FPS - 1e-6)
    entries = _shot_entries(shots, total, fg_min_ratio)
    countdown: list[dict] = []
    captions: list[dict] = []
    emojis: list[dict] = []
    cta: list[dict] = []
    timings: list[dict] = []
    if script and alignment:
        try:
            words = word_timings(alignment)
            if voice_envelope is not None:
                words = snap_word_starts(words, voice_envelope)
            countdown, spans, subject_words = _countdown(script["beats"], alignment, words, audio_duration_s, entries, total, log)
            captions = _captions(words, audio_duration_s, spans, subject_words, total)
            timings = beat_timings(beat_texts(script["beats"]), alignment, audio_duration_s)
            beat_of = _beat_of(words, script["beats"])
            cta = _cta(words, beat_of, total)
            emojis = _emojis(words, beat_of, marks, cta, countdown, total)
        except (PipelineError, IndexError, KeyError) as exc:  # caption/card cuma hiasan: timeline tetap jadi tanpa itu
            reason = exc.message.splitlines()[0] if isinstance(exc, PipelineError) else f"alignment nggak lengkap ({exc!r})"
            log(f"[timeline] caption & countdown dilewat: {reason}")
            countdown, captions, emojis, cta, timings = [], [], [], [], []
    shown = _overlays(overlays, entries, countdown, _point_ranges(timings, marks))
    bgm, sfx = _sound(audio, entries, countdown, shown, emojis, cta)
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
        "overlays": shown,
        "emojis": emojis,
        "cta": cta,
        "bgm": bgm,
        "sfx": sfx,
        "intro": {"durationInFrames": INTRO_FRAMES} if audio and "hook" in audio.get("sfx", {}) else None,
    }


def run_timeline(paths: RunPaths, clips: dict, tts: dict, *, fg_min_ratio: float, script: dict | None = None,
                 audio: dict | None = None, overlays: dict | None = None, marks: dict | None = None,
                 log: Callable[[str], None] = print) -> dict:
    envelope = None
    if paths.voice_mp3.exists():
        from mayzfact.voice_onset import voice_envelope

        try:
            envelope = voice_envelope(paths.voice_mp3)
        except Exception as exc:  # cuma buat ngepasin timing caption/card; tanpa ini tetap jalan pakai alignment
            log(f"[timeline] energi suara gagal dibaca, timing pakai alignment: {exc}")
    data = build_timeline(clips, tts["duration_s"], fg_min_ratio, script=script, alignment=tts.get("alignment"),
                          audio=audio, overlays=overlays, marks=marks, voice_envelope=envelope, log=log)
    write_json_atomic(paths.timeline_json, data)
    return data
