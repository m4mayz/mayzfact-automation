"""Pembuat data palsu buat test."""

from __future__ import annotations

import subprocess
from pathlib import Path

from mayzfact.models import Beat, Script


def make_script(n_beats: int = 11, photo_every: int = 3, words_per_beat: int = 10) -> Script:
    """Naskah dengan kata unik (w0x0, w0x1, ...) biar overlap ke source selalu 0."""
    beats = [
        Beat(
            text=" ".join(f"w{i}x{j}" for j in range(words_per_beat)) + ".",
            media="photo" if i % photo_every == 1 else "video",
            queries=[f"query {i}", "animal close up"],
        )
        for i in range(n_beats)
    ]
    return Script(beats=beats)


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


