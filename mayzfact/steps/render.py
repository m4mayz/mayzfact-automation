"""Step render: panggil Remotion CLI buat bikin final.mp4 dari timeline.json."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from mayzfact.config import PROJECT_ROOT
from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, tmp_path_for

REMOTION_DIR = PROJECT_ROOT / "remotion"
COMPOSITION_ID = "ShortVideo"


def render_command(npx: str, paths: RunPaths, output: Path) -> list[str]:
    return [
        npx, "remotion", "render", "src/index.ts", COMPOSITION_ID, str(output),
        f"--props={paths.timeline_json}", f"--public-dir={paths.root}", "--codec=h264",
    ]


def speed_command(src: Path, dest: Path, speed: float) -> list[str]:
    """Gambar + suara dipercepat bareng. atempo naikin tempo tanpa ngubah nada suara."""
    return [
        "ffmpeg", "-v", "error", "-y", "-i", str(src),
        "-filter_complex", f"[0:v]setpts=PTS/{speed:g}[v];[0:a]atempo={speed:g}[a]",
        "-map", "[v]", "-map", "[a]", "-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dest),
    ]


def speed_up(src: Path, dest: Path, speed: float) -> Path:
    tmp = tmp_path_for(dest)
    result = subprocess.run(speed_command(src, tmp, speed), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise PipelineError("render", f"ffmpeg gagal mempercepat video {speed:g}x: " + (result.stderr or "")[-1500:])
    os.replace(tmp, dest)
    return dest


def run_render(paths: RunPaths, remotion_dir: Path = REMOTION_DIR, *, speed: float = 1.0) -> Path:
    npx = shutil.which("npx")
    if npx is None:
        raise PipelineError("render", "npx nggak ketemu. Aktifin Node dulu: nvm use 22.23.1")
    if not (remotion_dir / "node_modules").exists():
        raise PipelineError("render", "Dependency Remotion belum ke-install. Jalanin: cd remotion && npm install")
    # speed_up juga pakai tmp_path_for(final.mp4) buat hasilnya, jadi output Remotion harus beda nama
    # (kalau sama, ffmpeg nolak: "same as Input").
    output = tmp_path_for(paths.final_mp4) if speed == 1.0 else paths.final_mp4.with_name("final.raw.mp4")
    result = subprocess.run(
        render_command(npx, paths, output),
        cwd=remotion_dir, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise PipelineError("render", "Remotion gagal:\n" + (result.stderr or result.stdout)[-2000:])
    if speed == 1.0:
        os.replace(output, paths.final_mp4)
        return paths.final_mp4
    try:  # Remotion render di kecepatan normal, terus satu video dipercepat (D-038)
        return speed_up(output, paths.final_mp4, speed)
    finally:
        output.unlink(missing_ok=True)
