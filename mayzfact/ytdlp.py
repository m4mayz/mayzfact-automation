"""Download video pakai yt-dlp: video source YouTube dan klip platform login."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from mayzfact.errors import PipelineError
from mayzfact.store import tmp_path_for

FORMAT = "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b"


def youtube_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def ytdlp_command(url: str, dest: Path, cookies: Path | None = None) -> list[str]:
    cmd = [
        sys.executable, "-m", "yt_dlp", "--no-playlist", "--quiet", "--no-warnings", "--no-progress",
        "-f", FORMAT, "--merge-output-format", "mp4", "-o", str(dest),
    ]
    if cookies is not None:
        cmd += ["--cookies", str(cookies)]
    return cmd + [url]


def run_ytdlp(url: str, dest: Path, *, cookies: Path | None = None, step: str = "hook") -> Path:
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_path_for(dest)
    result = subprocess.run(
        ytdlp_command(url, tmp, cookies), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise PipelineError(step, f"yt-dlp gagal download {url}:\n{(result.stderr or result.stdout)[-800:]}")
    tmp.replace(dest)
    return dest
