"""Tanda per beat: point (panah/lingkaran), emoji + kata pemicunya (spec Fase 3C-2 bagian 2).

Naskah baru udah bawa tanda dari prompt rewrite. Naskah lama (suaranya udah dikunci) ditandain Gemini belakangan
tanpa ngubah teks; hasilnya di-cache di annotations.json dengan key hash teks naskah.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Callable

import httpx

from mayzfact.countdown import parse_countdown
from mayzfact.emoji import EMOJI, allowed_emoji_line, ensure_emoji
from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, read_json, write_json_atomic
from mayzfact.text import script_text, text_hash

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "mark_beats.md"
_WORD = re.compile(r"[\w']+")
_NONE = {"point": False, "emoji": "", "emoji_word": ""}


def _clean_word(word: str) -> str:
    match = _WORD.search(word.lower())
    return match.group(0) if match else ""


def normalize_marks(beats: list[dict], raw: list[dict]) -> list[dict]:
    """Emoji di luar daftar dibuang, beat countdown tanpa emoji, emoji_word harus kata yang ada di beat itu."""
    out = []
    for i, beat in enumerate(beats):
        mark = raw[i] if i < len(raw) and isinstance(raw[i], dict) else {}
        countdown = parse_countdown(beat.get("text", ""))
        emoji = mark.get("emoji") or ""
        if emoji not in EMOJI or (countdown and countdown.number is not None):
            emoji = ""
        word = _clean_word(mark.get("emoji_word") or "") if emoji else ""
        if word not in {w.lower() for w in _WORD.findall(beat.get("text", ""))}:
            word = ""
        out.append({"point": bool(mark.get("point")), "emoji": emoji, "emoji_word": word})
    return out


def _ask_gemini(beats: list[dict], writer: Any) -> list[dict]:
    from mayzfact.models import BeatMarks

    system = PROMPT_PATH.read_text(encoding="utf-8") + "\n" + allowed_emoji_line()
    contents = json.dumps([{"index": i, "text": b["text"]} for i, b in enumerate(beats)], ensure_ascii=False)
    result = writer.generate(system, contents, BeatMarks, step="timeline")
    raw: list[dict] = [{} for _ in beats]
    for item in result.items:
        if 0 <= item.index < len(beats):
            raw[item.index] = item.model_dump()
    return raw


def beat_marks(paths: RunPaths, script: dict, writer: Any, *, log: Callable[[str], None]) -> list[dict]:
    beats = script["beats"]
    if beats and all("point" in b for b in beats):  # naskah baru: tanda udah dari prompt rewrite
        return normalize_marks(beats, beats)
    cache_path = paths.root / "annotations.json"
    key = text_hash(script_text(beats))
    if cache_path.exists():
        cached = read_json(cache_path)
        if cached.get("key") == key:
            return normalize_marks(beats, cached["beats"])
    if writer is None:
        log("[timeline] Gemini nggak ada, beat nggak ditandain (tanpa panah/emoji)")
        return [dict(_NONE) for _ in beats]
    try:
        marks = normalize_marks(beats, _ask_gemini(beats, writer))
    except PipelineError as exc:
        log(f"[timeline] Gemini gagal nandain beat, tanpa panah/emoji: {exc.message[:120]}")
        return [dict(_NONE) for _ in beats]
    write_json_atomic(cache_path, {"key": key, "beats": marks})
    return marks


def prepare_marks(
    paths: RunPaths, script: dict, *, writer: Any, client: httpx.Client, emoji_dir: Path, log: Callable[[str], None],
) -> dict:
    """{"beats": [tanda per beat], "emoji": {emoji: "emoji/<cp>.json"}}. Lottie yang kepakai di-copy ke folder run."""
    marks = beat_marks(paths, script, writer, log=log)
    wanted = sorted({m["emoji"] for m in marks if m["emoji"]})
    files = ensure_emoji(emoji_dir, client, [EMOJI[e] for e in wanted], log)
    out: dict[str, str] = {}
    for emoji in wanted:
        source = files.get(EMOJI[emoji])
        if source is None:
            continue
        dest = paths.root / "emoji" / source.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        out[emoji] = dest.relative_to(paths.root).as_posix()
    return {"beats": marks, "emoji": out}
