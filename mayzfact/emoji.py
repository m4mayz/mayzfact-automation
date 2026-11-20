"""Emoji animasi Noto (Lottie, CC BY 4.0) buat overlay di atas caption (spec Fase 3C-2)."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Callable

import httpx

from mayzfact.config import PROJECT_ROOT
from mayzfact.errors import PipelineError
from mayzfact.net import download

EMOJI_DIR = PROJECT_ROOT / "assets" / "emoji"
NOTO_LOTTIE = "https://fonts.gstatic.com/s/e/notoemoji/latest/{cp}/lottie.json"

# Emoji yang boleh dipakai agent di naskah. Semua udah dicek ada versi animasinya di Noto (2026-10-14).
EMOJI = {
    "🧐": "1f9d0", "🤨": "1f928", "🤯": "1f92f", "🫢": "1fae2", "🍀": "1f340", "😱": "1f631", "😮": "1f62e",
    "👀": "1f440", "🔥": "1f525", "💀": "1f480", "🤔": "1f914", "😳": "1f633", "😲": "1f632", "🤩": "1f929",
    "😨": "1f628", "🥶": "1f976", "😂": "1f602", "💯": "1f4af", "👍": "1f44d", "🦖": "1f996", "🌊": "1f30a",
    "⚡": "26a1", "😴": "1f634", "🫣": "1fae3", "😬": "1f62c", "🤓": "1f913", "😎": "1f60e", "🥺": "1f97a",
}


def _valid_lottie(path: Path) -> bool:
    """Lottie dasar: JSON object dengan `layers` list. Server yang balikin HTML jangan sampai masuk cache."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and isinstance(data.get("layers"), list)


def _fetch_lottie(emoji_dir: Path, client: httpx.Client, cp: str, log: Callable[[str], None],
                  sleep: Callable[[float], None]) -> Path | None:
    """Download + validasi; None = isinya bukan Lottie (file kotor nggak disimpan)."""
    dest = emoji_dir / f"{cp}.json"
    if dest.exists():
        if _valid_lottie(dest):
            return dest
        dest.unlink(missing_ok=True)  # cache lama HTML/rusak: buang, coba download lagi
    emoji_dir.mkdir(parents=True, exist_ok=True)
    raw = dest.with_name(dest.name + ".raw")
    raw.unlink(missing_ok=True)  # sisa run yang mati di tengah jangan dianggap cache
    try:
        download(client, NOTO_LOTTIE.format(cp=cp), raw, step="timeline", sleep=sleep)
    except PipelineError:
        raw.unlink(missing_ok=True)
        raw.with_name(raw.name + ".part").unlink(missing_ok=True)
        raise
    if not _valid_lottie(raw):
        log(f"[timeline] emoji {cp} bukan Lottie valid, dilewat")
        raw.unlink(missing_ok=True)
        return None
    os.replace(raw, dest)
    return dest


def ensure_emoji(emoji_dir: Path, client: httpx.Client, codepoints: list[str], log: Callable[[str], None],
                 sleep: Callable[[float], None] = time.sleep) -> dict[str, Path]:
    """Download Lottie yang belum ada. Yang gagal/dirty dilewat (emoji-nya nggak tampil, video tetap jadi).

    Kalau fonts.gstatic nggak bisa dihubungi, sisanya langsung dilewat: emoji cuma hiasan, jangan bikin pipeline nunggu.
    """
    out: dict[str, Path] = {}
    for cp in codepoints:
        try:
            path = _fetch_lottie(emoji_dir, client, cp, log, sleep)
        except PipelineError as exc:
            if isinstance(exc.__cause__, httpx.TransportError):
                log(f"[timeline] fonts.gstatic nggak bisa dihubungi, emoji yang belum ke-download dilewat: {exc.message[:120]}")
                break
            log(f"[timeline] emoji {cp} gagal di-download, dilewat: {exc.message[:120]}")
            continue
        if path is not None:
            out[cp] = path
    return out


def emoji_codepoint(char: str) -> str:
    """Codepoint Noto dari karakter emoji: "📦" → "1f4e6", "❤️" → "2764_fe0f"."""
    return "_".join(f"{ord(c):x}" for c in char)


def prepare_cta_emoji(run_root: Path, cta_scene: dict | None, *, client: httpx.Client, emoji_dir: Path,
                      log: Callable[[str], None], sleep: Callable[[float], None] = time.sleep) -> str | None:
    """Siapin Lottie Noto buat emoji CTA FaktaCuil. None = format lain atau Lottie nggak ada (pakai emoji statis)."""
    if not cta_scene or cta_scene.get("format") != "emoji" or not cta_scene.get("emoji"):
        return None
    emoji = cta_scene["emoji"]
    codepoints = [emoji_codepoint(emoji)]
    plain = codepoints[0].replace("_fe0f", "")  # Noto sering nyimpen tanpa variation selector
    if plain != codepoints[0]:
        codepoints.append(plain)
    for cp in codepoints:
        try:
            src = _fetch_lottie(emoji_dir, client, cp, log, sleep)
        except PipelineError as exc:
            if isinstance(exc.__cause__, httpx.TransportError):  # offline: jangan nunggu emoji berikutnya
                log(f"[timeline] fonts.gstatic nggak bisa dihubungi, emoji CTA pakai emoji statis: {exc.message[:120]}")
                return None
            continue
        if src is None:
            continue
        target = run_root / "emoji" / f"{cp}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        return f"emoji/{cp}.json"
    log(f"[timeline] PERINGATAN: Lottie Noto buat emoji {'+'.join(f'U+{ord(c):04X}' for c in emoji)} "
        f"({codepoints[0]}) nggak ada, CTA pakai emoji statis.")
    return None
