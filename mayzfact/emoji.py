"""Emoji animasi Noto (Lottie, CC BY 4.0) buat overlay di atas caption (spec Fase 3C-2)."""

from __future__ import annotations

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


def ensure_emoji(emoji_dir: Path, client: httpx.Client, codepoints: list[str], log: Callable[[str], None],
                 sleep: Callable[[float], None] = time.sleep) -> dict[str, Path]:
    """Download Lottie yang belum ada. Yang gagal dilewat (emoji-nya nggak tampil, video tetap jadi).

    Kalau fonts.gstatic nggak bisa dihubungi, sisanya langsung dilewat: emoji cuma hiasan, jangan bikin pipeline nunggu.
    """
    out: dict[str, Path] = {}
    for cp in codepoints:
        try:
            out[cp] = download(client, NOTO_LOTTIE.format(cp=cp), emoji_dir / f"{cp}.json", step="timeline", sleep=sleep)
        except PipelineError as exc:
            if isinstance(exc.__cause__, httpx.TransportError):
                log(f"[timeline] fonts.gstatic nggak bisa dihubungi, emoji yang belum ke-download dilewat: {exc.message[:120]}")
                break
            log(f"[timeline] emoji {cp} gagal di-download, dilewat: {exc.message[:120]}")
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
            src = download(client, NOTO_LOTTIE.format(cp=cp), emoji_dir / f"{cp}.json", step="timeline", sleep=sleep)
        except PipelineError as exc:
            if isinstance(exc.__cause__, httpx.TransportError):  # offline: jangan nunggu emoji berikutnya
                log(f"[timeline] fonts.gstatic nggak bisa dihubungi, emoji CTA pakai emoji statis: {exc.message[:120]}")
                return None
            continue
        target = run_root / "emoji" / f"{cp}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        return f"emoji/{cp}.json"
    log(f"[timeline] PERINGATAN: Lottie Noto buat emoji {emoji} ({codepoints[0]}) nggak ada, CTA pakai emoji statis.")
    return None
