"""Frame source buat hook: deteksi segmen di detik awal source, 3 frame per segmen (dipakai step source + plan)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import extract_frame, probe
from mayzfact.scenes import detect_cuts, merge_cuts, segments
from mayzfact.store import RunPaths

FRAME_POSITIONS = (0.25, 0.5, 0.75)


def transcript_near(transcript: list[dict], start_s: float, end_s: float) -> str:
    return " ".join(s["text"] for s in transcript if s["start"] < end_s and s["start"] + s["duration"] > start_s)


def prepare_source_segments(
    paths: RunPaths, source: dict, download_source: Callable[[str, Path], Path], hook_seconds: float,
    out_dir: Path, retry_step: str = "hook",
) -> list[dict]:
    """Download source (kalau belum ada), deteksi segmen di hook_seconds awal, ambil 3 frame per segmen ke out_dir."""
    src = paths.source_mp4
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        if not src.exists():
            download_source(source["video_id"], src)
        end_s = min(hook_seconds, probe(src, "hook")["duration_s"] or 0.0)
        segs = segments(merge_cuts(detect_cuts(src, end_s)), end_s)
    except PipelineError as exc:
        raise PipelineError(
            retry_step, f"{exc.message}\nUlang step ini pakai: mayzfact run {source['video_id']} --from {retry_step}"
        ) from exc
    out = []
    for i, (start, end) in enumerate(segs):
        frames = [
            extract_frame(src, start + (end - start) * pos, out_dir / f"seg_{i + 1:02d}_{k}.jpg")
            for k, pos in enumerate(FRAME_POSITIONS)
        ]
        out.append({"index": i, "start_s": start, "end_s": end, "frames": frames,
                    "transcript": transcript_near(source["transcript"], start, end)})
    return out
