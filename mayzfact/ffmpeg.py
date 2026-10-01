"""Wrapper tipis ffmpeg/ffprobe."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mayzfact.errors import PipelineError


def _run(cmd: list[str], step: str) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise PipelineError(step, f"{cmd[0]} gagal:\n{result.stderr[-1500:]}")
    return result.stdout


def probe(path: Path, step: str) -> dict:
    """Ukuran stream video pertama (kalau ada) + durasi file."""
    out = _run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(path)],
        step,
    )
    data = json.loads(out)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    duration = data.get("format", {}).get("duration")
    return {
        "width": video.get("width"),
        "height": video.get("height"),
        "duration_s": float(duration) if duration not in (None, "N/A") else None,
    }


def audio_duration(path: Path) -> float:
    duration = probe(path, "tts")["duration_s"]
    if not duration:
        raise PipelineError("tts", f"Durasi {path.name} nggak kebaca.")
    return duration
