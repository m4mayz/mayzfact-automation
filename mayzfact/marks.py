"""Tanda per beat: point (panah/lingkaran), emoji + kata pemicunya (spec Fase 3C-2 bagian 2).

Tandanya ditulis agent langsung di script.json. Naskah lama tanpa field itu = tanpa panah/emoji.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Callable

import httpx

from mayzfact.countdown import parse_countdown
from mayzfact.emoji import EMOJI, ensure_emoji
from mayzfact.store import RunPaths

_WORD = re.compile(r"[\w']+")


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


def prepare_marks(
    paths: RunPaths, script: dict, *, client: httpx.Client, emoji_dir: Path, log: Callable[[str], None],
) -> dict:
    """{"beats": [tanda per beat], "emoji": {emoji: "emoji/<cp>.json"}}. Lottie yang kepakai di-copy ke folder run."""
    marks = normalize_marks(script["beats"], script["beats"])
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
