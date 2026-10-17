"""Download video pakai yt-dlp: video source YouTube dan link klip manual."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from mayzfact.errors import PipelineError
from mayzfact.store import tmp_path_for

FORMAT = "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b"
TIMEOUT_S = 600


def youtube_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def ytdlp_command(url: str, dest: Path) -> list[str]:
    return [
        sys.executable, "-m", "yt_dlp", "--no-playlist", "--quiet", "--no-warnings", "--no-progress",
        "-f", FORMAT, "--merge-output-format", "mp4", "-o", str(dest), url,
    ]


def _cleanup(tmp: Path) -> None:
    # yt-dlp ninggalin file .part / .fNNN.mp4 dengan prefix yang sama kalau gagal di tengah.
    for leftover in tmp.parent.glob(f"{tmp.stem}*"):
        leftover.unlink(missing_ok=True)


def run_ytdlp(
    url: str,
    dest: Path,
    *,
    step: str = "source",
    timeout_s: float = TIMEOUT_S,
) -> Path:
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_path_for(dest)
    try:
        result = subprocess.run(
            ytdlp_command(url, tmp),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        _cleanup(tmp)
        raise PipelineError(step, f"yt-dlp timeout ({timeout_s:.0f} detik) waktu download {url}") from exc
    if result.returncode != 0 or not tmp.exists():
        _cleanup(tmp)
        raise PipelineError(step, f"yt-dlp gagal download {url}:\n{(result.stderr or result.stdout)[-800:]}")
    tmp.replace(dest)
    return dest
