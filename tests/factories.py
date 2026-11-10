"""Pembuat data palsu buat test."""

from __future__ import annotations

import subprocess
from pathlib import Path


def fake_alignment(text: str, total_s: float) -> dict:
    """Alignment ala ElevenLabs: tiap karakter dapat jatah waktu yang sama."""
    step = total_s / max(1, len(text))
    return {
        "characters": list(text),
        "character_start_times_seconds": [round(i * step, 4) for i in range(len(text))],
        "character_end_times_seconds": [round((i + 1) * step, 4) for i in range(len(text))],
    }


def stream_types(path: Path) -> list[str]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


