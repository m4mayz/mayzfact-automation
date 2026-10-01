"""Pembuat data palsu buat test."""

from __future__ import annotations

import subprocess
from pathlib import Path

from mayzfact.models import Beat, Script
from mayzfact.providers.types import Candidate, Rendition


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
    return Script(beats=beats, fallback_query="ocean animals")


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


def cand(
    provider: str,
    id: str,
    kind: str = "video",
    width: int = 1080,
    height: int = 1920,
    duration_s: float | None = 20.0,
    rank: int = 0,
    url: str | None = None,
) -> Candidate:
    ext = "mp4" if kind == "video" else "jpg"
    return Candidate(
        provider=provider,
        id=id,
        kind=kind,
        duration_s=duration_s if kind == "video" else None,
        page_url=f"https://{provider}.test/{id}",
        author="tester",
        renditions=(Rendition(url or f"https://cdn.test/{provider}_{id}.{ext}", width, height),),
        rank=rank,
    )
