"""Beat countdown "Number five, horseshoe crab." → angka + subjek (spec Fase 3A bagian 2)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from mayzfact.text import clean_text

# Titik cuma dianggap pemisah kalau diikutin spasi, biar "Number 1.5 million…" nggak kebaca countdown.
_PATTERN = re.compile(r"^\s*number\s+(\w+)\s*(?:[,:\-–]|\.(?=\s))\s*(?:the\s+)?(.+?)\s*[.!?]*\s*$", re.IGNORECASE)
_WORDS = {w: i for i, w in enumerate(["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"], 1)}


@dataclass(frozen=True)
class Countdown:
    number: int | None  # None = angkanya nggak dikenal, card nggak dibikin
    subject: str
    number_end: int  # index karakter terakhir token angka di teks beat


def parse_countdown(text: str) -> Countdown | None:
    """Teks di-clean dulu (em dash jadi koma, dst), jadi hasilnya sama di teks mentah maupun teks TTS.

    number_end berlaku buat teks yang udah di-clean, yaitu teks yang dipakai alignment.
    """
    match = _PATTERN.match(clean_text(text or ""))
    if not match:
        return None
    token = match.group(1).lower()
    number = _WORDS.get(token) or (int(token) if token.isdigit() and 0 < int(token) < 100 else None)
    return Countdown(number, match.group(2).strip(), match.end(1) - 1)
