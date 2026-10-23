"""Step timeline: detik → frame, tentuin layout tiap shot, caption per kata + card countdown, tulis props buat Remotion."""

from __future__ import annotations

import math
import random
import re
from typing import Any, Callable

from mayzfact.countdown import parse_countdown
from mayzfact.cta import _EDGE_PUNCT, SUBSCRIBE, is_like_cta
from mayzfact.cta import clean as _clean
from mayzfact.errors import PipelineError
from mayzfact.media import (
    FRAME_H,
    FRAME_W,
    PHOTO_ZOOM,
    cover_box,
    fg_height,
    layout_for,
    screen_box,
)
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import beat_texts
from mayzfact.timing import beat_offsets, beat_timings, word_timings
from mayzfact.voice_onset import snap_word_starts

FPS = 30
CAPTION_HOLD_S = 0.4  # kata terakhir tetap tampil sebentar pas jeda
CAPTION_WHITE = "#ffffff"
CAPTION_COLORS = ("#22d3ee", "#4ade80", "#facc15")
LONG_WORD = 6
SFX_VOLUME = {"hook": 0.8, "number": 0.9, "subject": 0.7, "cut": 0.4, "overlay": 0.35, "emoji": 0.6, "click": 0.8,
              "item_reveal": 0.7, "riser": 1.0, "hook_cut": 0.4}
FLASH_FRAMES = 3  # flash putih di pergantian klip hook (barengan camera flash)
EXTRA_PREFIX = "extra_"  # SFX tambahan acak di transisi klik (sfx.json: extra_oof, extra_punch, ...)
EXTRA_VOLUME = 0.3  # Akmal: klik + SFX tambahan jangan terlalu keras (dulu 0,6)
EXTRA_VOLUME_BY_EVENT = {"extra_punch": 0.15}  # file punch ±6 dB lebih keras dari yang lain
HOOK_EXTRA_PREFIX = "hook_extra_"  # 1 SFX acak tambahan tiap ganti klip di hook, barengan camera flash (sfx.json)
HOOK_EXTRA_VOLUME = 0.3  # kata Akmal (awalnya 0,4)
BGM_SWITCH_FADE_FRAMES = 8  # BGM hook pudar cepat pas ganti ke BGM utama (riser nutupin)
SFX_LEAD_FRAMES = 3  # SFX transisi mulai sedikit sebelum gambar ganti (puncaknya di ±0.1 detik)
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
NUMBER_SFX_LEAD_FRAMES = 9  # fire whoosh baru kedengeran ±0.28 detik, puncaknya pas api di kartu lagi gede
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
               total: int, log: Callable[[str], None], beat_starts: list[int] = ()) -> tuple[list[dict], list[tuple[float, float]], set[str]]:
    """Card per beat countdown + rentang detik beat countdown (buat ngumpetin caption) + kata-kata nama subjek.

    Angka muncul bareng kartunya (numberAt 0) pas "Number" kedengeran, subject card mulai pas nama subjeknya kedengeran.
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
        # kartu + angka (+ SFX api) mulai pas "Number" kedengeran, bukan di awal beat versi alignment (Akmal)
        first_word = _word_at(words, offset)
        heard = words[first_word]["start_s"] if first_word is not None else timing["start_s"]
        number_from = to_frame(heard if timing["start_s"] <= heard < timing["end_s"] else timing["start_s"])
        card_end = min(to_frame(timing["end_s"]), total)
        number_word = _word_at(words, offset + countdown.number_end)
        number_at = 0  # angka muncul bareng kartunya (source i2xag)
        after = number_word + 1 if number_word is not None else None
        if after is not None and after < len(words) and words[after]["start_s"] < timing["end_s"]:
            card_from = to_frame(words[after]["start_s"])
        else:
            card_from = to_frame(float(ends[offset + countdown.number_end]))
        # plan bisa motong / manjangin box subjek: card habis pas shot beat berikutnya mulai
        next_start = min((f for f in beat_starts if f > card_from), default=None)
        if next_start is not None:
            card_end = min(next_start, total)
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
           emojis: list[dict], cta: list[dict], hook_end: int, total: int, same_clip: set[int] = frozenset()
           ) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """BGM (hook + utama), SFX, frame transisi magic reveal, dan flash putih di pergantian klip hook."""
    if not audio:
        return [], [], [], []
    files = audio.get("sfx", {})
    sfx: list[dict] = []
    reveals: list[dict] = []
    flashes: list[dict] = []

    onset = audio.get("sfx_onset", {})

    def add(event: str, frame: int, align_to: str | None = None) -> None:
        if event in files:
            volume = (HOOK_EXTRA_VOLUME if event.startswith(HOOK_EXTRA_PREFIX)
                      else EXTRA_VOLUME_BY_EVENT.get(event, EXTRA_VOLUME) if event.startswith(EXTRA_PREFIX)
                      else SFX_VOLUME[event])
            if align_to:  # SFX tumpukan mulai kedengeran barengan SFX utamanya (contoh punch: hening 0,36 dtk di depan)
                frame -= round((onset.get(event, 0.0) - onset.get(align_to, 0.0)) * FPS)
            sfx.append({"src": files[event], "from": max(0, frame), "volume": volume})

    # BGM hook sampai "Number" pertama, terus BGM utama sampai akhir. Riser habis pas di titik ganti itu.
    switch = countdown[0]["numberFrom"] if countdown else hook_end
    bgm: list[dict] = []
    if audio.get("bgm") and audio.get("bgm_main") and 0 < switch < total:
        bgm = [{"src": audio["bgm"], "from": 0, "durationInFrames": switch, "volume": BGM_VOLUME,
                "fadeOutFrames": BGM_SWITCH_FADE_FRAMES},
               {"src": audio["bgm_main"], "from": switch, "durationInFrames": total - switch, "volume": BGM_VOLUME,
                "fadeOutFrames": BGM_FADE_FRAMES}]
        if audio.get("riser_s"):  # ujung bunyi riser pas kartu angka pertama muncul (api + whoosh)
            add("riser", switch - round(audio["riser_s"] * FPS))
    elif audio.get("bgm") or audio.get("bgm_main"):
        bgm = [{"src": audio.get("bgm") or audio["bgm_main"], "from": 0, "durationInFrames": total, "volume": BGM_VOLUME,
                "fadeOutFrames": BGM_FADE_FRAMES}]

    add("hook", 0)
    for card in countdown:
        add("number", card["numberFrom"] + card["numberAt"] - NUMBER_SFX_LEAD_FRAMES)
        add("subject", card["cardFrom"] - SFX_LEAD_FRAMES)

    # Pergantian klip setelah hook (D-038): klip pertama habis card = magic reveal + efek pembuka (box subjek di card
    # bunyi "subject" = check mark), sisanya klik + 1 SFX tambahan acak (atau nggak ada). Seed tetap biar render ulang sama.
    extras = sorted(event for event in files if event.startswith(EXTRA_PREFIX))
    hook_extras = sorted(event for event in files if event.startswith(HOOK_EXTRA_PREFIX))
    rng = random.Random(len(entries))
    hook_rng = random.Random(len(entries) + 1)  # rng sendiri biar pilihan SFX setelah hook nggak ikut geser
    since_card = None  # urutan klip sejak card terakhir habis
    for entry in entries[1:]:
        covered = any(c["numberFrom"] <= entry["from"] < c["cardFrom"] + c["cardDuration"] for c in countdown)
        if covered:  # masuk card udah punya bunyi sendiri
            since_card = 0
            continue
        if since_card is not None:
            since_card += 1
        if entry["from"] in same_clip and since_card != 1:  # klip yang sama lanjut: bukan transisi
            continue
        if entry["from"] < hook_end:  # di dalam hook: camera flash + 1 SFX hook acak + flash putih
            if "hook_cut" in files:
                add("hook_cut", entry["from"] - SFX_LEAD_FRAMES)
                if hook_extras:
                    add(hook_rng.choice(hook_extras), entry["from"] - SFX_LEAD_FRAMES, align_to="hook_cut")
                flashes.append({"from": entry["from"], "durationInFrames": FLASH_FRAMES})
            continue
        frame = entry["from"] - SFX_LEAD_FRAMES
        if since_card == 1 and "item_reveal" in files:
            add("item_reveal", frame)
            reveals.append({"from": entry["from"], "durationInFrames": INTRO_FRAMES})
        else:
            add("cut", frame)
            pick = rng.choice([None, *extras]) if extras else None
            if pick:
                add(pick, frame, align_to="cut")
    for overlay in overlays:
        add("overlay", overlay["from"])
    for emoji in emojis:
        add("emoji", emoji["from"])
    for action in cta:
        add("click", action["from"] + action["clickAt"] - CLICK_LEAD_FRAMES)
    sfx.sort(key=lambda s: s["from"])
    return bgm, sfx, reveals, flashes


SUBJECT_BOX = 820  # ukuran box klip di SubjectCard.tsx


def _add_blurs(blurs: dict, shots: list[dict], entries: list[dict], countdown: list[dict], fg_min_ratio: float) -> None:
    """Kotak blur teks (0..1 per klip) → piksel layar di tiap shot, dan piksel box di card yang nampilin klip itu."""
    size = {s["file"].replace("\\", "/"): (s["width"], s["height"]) for s in shots}
    found = {k.replace("\\", "/"): v for k, v in blurs.items()}
    for entry in entries:
        if entry["src"] in found:
            w, h = size[entry["src"]]
            entry["blurs"] = [dict(zip(("x", "y", "w", "h"), screen_box(tuple(b), w, h, fg_min_ratio=fg_min_ratio)))
                              for b in found[entry["src"]]]
    for card in countdown:
        if card["src"] in found:
            w, h = size[card["src"]]
            card["blurs"] = [cover_box(tuple(b), w, h, SUBJECT_BOX, SUBJECT_BOX) for b in found[card["src"]]]


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
    blurs: dict | None = None,
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
            # frame shot yang mulai beat baru (clips.json nyimpen beat-nya); dipakai buat ujung box subjek
            beat_starts = [e["from"] for i, (e, s) in enumerate(zip(entries, shots))
                           if i and s.get("beat") is not None and s.get("beat") != shots[i - 1].get("beat")]
            countdown, spans, subject_words = _countdown(script["beats"], alignment, words, audio_duration_s, entries, total, log,
                                                         beat_starts)
            captions = _captions(words, audio_duration_s, spans, subject_words, total)
            timings = beat_timings(beat_texts(script["beats"]), alignment, audio_duration_s)
            beat_of = _beat_of(words, script["beats"])
            cta = _cta(words, beat_of, total)
            emojis = _emojis(words, beat_of, marks, cta, countdown, total)
        except (PipelineError, IndexError, KeyError) as exc:  # caption/card cuma hiasan: timeline tetap jadi tanpa itu
            reason = exc.message.splitlines()[0] if isinstance(exc, PipelineError) else f"alignment nggak lengkap ({exc!r})"
            log(f"[timeline] caption & countdown dilewat: {reason}")
            countdown, captions, emojis, cta, timings = [], [], [], [], []
    _add_blurs(blurs or {}, shots, entries, countdown, fg_min_ratio)
    shown = _overlays(overlays, entries, countdown, _point_ranges(timings, marks))
    hook_end = max((e["from"] + e["durationInFrames"] for e, s in zip(entries, shots) if s.get("hook_segment") is not None),
                   default=0)
    # shot yang ngelanjutin link/klip yang sama kayak shot sebelumnya nggak dapat bunyi/efek transisi
    same_clip = {e["from"] for i, (e, s) in enumerate(zip(entries, shots))
                 if i and s.get("page_url") and s.get("page_url") == shots[i - 1].get("page_url")}
    bgm, sfx, reveals, flashes = _sound(audio, entries, countdown, shown, emojis, cta, hook_end, total, same_clip)
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
        "transitions": reveals,
        "flashes": flashes,
    }


def run_timeline(paths: RunPaths, clips: dict, tts: dict, *, fg_min_ratio: float, script: dict | None = None,
                 audio: dict | None = None, overlays: dict | None = None, marks: dict | None = None,
                 blurs: dict | None = None, log: Callable[[str], None] = print) -> dict:
    envelope = None
    if paths.voice_mp3.exists():
        from mayzfact.voice_onset import voice_envelope

        try:
            envelope = voice_envelope(paths.voice_mp3)
        except Exception as exc:  # cuma buat ngepasin timing caption/card; tanpa ini tetap jalan pakai alignment
            log(f"[timeline] energi suara gagal dibaca, timing pakai alignment: {exc}")
    data = build_timeline(clips, tts["duration_s"], fg_min_ratio, script=script, alignment=tts.get("alignment"),
                          audio=audio, overlays=overlays, marks=marks, voice_envelope=envelope, blurs=blurs, log=log)
    write_json_atomic(paths.timeline_json, data)
    return data
