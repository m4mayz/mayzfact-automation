"""Wrapper tipis ffmpeg/ffprobe."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from mayzfact.errors import PipelineError
from mayzfact.store import tmp_path_for


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


def normalize_video(src: Path, dest: Path, *, start_s: float, duration_s: float, scale: float) -> None:
    """Potong, ubah ke 30fps H.264 yuv420p tanpa audio, resize pakai faktor `scale` (dimensi dibikin genap)."""
    vf = f"scale=trunc(iw*{scale:.6f}/2)*2:trunc(ih*{scale:.6f}/2)*2:flags=lanczos,fps=30,format=yuv420p"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_path_for(dest)
    _run(
        [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{start_s:.3f}", "-i", str(src), "-t", f"{duration_s:.3f}",
            "-an", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-movflags", "+faststart", str(tmp),
        ],
        "clips",
    )
    os.replace(tmp, dest)


def extract_frame(src: Path, t: float, dest: Path, width: int = 448) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1",
         "-vf", f"scale={width}:-2", "-q:v", "3", str(dest)],
        "hook",
    )
    return dest


def sample_frames(src: Path, dest_dir: Path, *, every_s: float, max_s: float, width: int = 448) -> list[tuple[float, Path]]:
    """Frame tiap every_s detik dari max_s detik pertama. Balikin [(detik, path)]."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    for old in dest_dir.glob("f_*.jpg"):
        old.unlink()
    _run(
        ["ffmpeg", "-y", "-v", "error", "-t", f"{max_s:.3f}", "-i", str(src),
         "-vf", f"fps=1/{every_s},scale={width}:-2", "-q:v", "4", str(dest_dir / "f_%04d.jpg")],
        "hook",
    )
    return [(round(i * every_s, 3), path) for i, path in enumerate(sorted(dest_dir.glob("f_*.jpg")))]
