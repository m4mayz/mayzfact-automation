"""Emoji animasi Noto (Lottie, CC BY 4.0) buat overlay di atas caption (spec Fase 3C-2)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import httpx

from mayzfact.config import PROJECT_ROOT
from mayzfact.errors import PipelineError
from mayzfact.net import download

EMOJI_DIR = PROJECT_ROOT / "assets" / "emoji"
NOTO_LOTTIE = "https://fonts.gstatic.com/s/e/notoemoji/latest/{cp}/lottie.json"

# Emoji yang boleh dipilih Gemini. Semua udah dicek ada versi animasinya di Noto (2026-10-14).
EMOJI = {
    "🧐": "1f9d0", "🤨": "1f928", "🤯": "1f92f", "🫢": "1fae2", "🍀": "1f340", "😱": "1f631", "😮": "1f62e",
    "👀": "1f440", "🔥": "1f525", "💀": "1f480", "🤔": "1f914", "😳": "1f633", "😲": "1f632", "🤩": "1f929",
    "😨": "1f628", "🥶": "1f976", "😂": "1f602", "💯": "1f4af", "👍": "1f44d", "🦖": "1f996", "🌊": "1f30a",
    "⚡": "26a1", "😴": "1f634", "🫣": "1fae3", "😬": "1f62c", "🤓": "1f913", "😎": "1f60e", "🥺": "1f97a",
}


def allowed_emoji_line() -> str:
    return "Allowed emoji: " + " ".join(EMOJI)


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
