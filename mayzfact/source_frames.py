"""Frame source buat hook: deteksi segmen di detik awal source, 3 frame per segmen (dipakai step source + plan)."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Callable

from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import extract_frame, probe
from mayzfact.scenes import detect_cuts, merge_cuts, segments
from mayzfact.store import RunPaths

FRAME_POSITIONS = (0.25, 0.5, 0.75)
REF_FRAMES_PER_SHOT = 2
MAX_SOURCE_SHOTS = 60
REF_EDGE = 0.15  # frame nggak diambil di 15% pinggir shot, biar nggak kena transisi


def _spread(n: int, cap: int) -> list[int]:
    """Semua index kalau muat; selain itu `cap` index yang nyebar rata sampai ujung."""
    if n <= cap:
        return list(range(n))
    return [i * n // cap for i in range(cap)]


def source_shot_frames(
    paths: RunPaths, source: dict, download_source: Callable[[str, Path], Path],
    log: Callable[[str], None] = print,
) -> list[dict]:
    """Frame referensi dari shot source: cut detection seluruh source, 2 frame acak per shot, seed video_id.

    Cuma hiasan: download/deteksi gagal = `[]` + log, 1 shot gagal = shot itu dilewat.
    """
    src = paths.source_mp4
    paths.root.mkdir(parents=True, exist_ok=True)
    try:
        if not src.exists():
            download_source(source["video_id"], src)
        total = probe(src, "source")["duration_s"] or 0.0
        segs = segments(merge_cuts(detect_cuts(src, total)), total)
    except Exception as exc:
        message = exc.message if isinstance(exc, PipelineError) else f"{type(exc).__name__}: {exc}"
        log(f"[plan] frame referensi source dilewat: {message.splitlines()[0][:160]}")
        return []
    rng = random.Random(source["video_id"])
    out = []
    for index in _spread(len(segs), MAX_SOURCE_SHOTS):
        start, end = segs[index]
        length = end - start
        times = sorted(rng.uniform(start + REF_EDGE * length, end - REF_EDGE * length)
                       for _ in range(REF_FRAMES_PER_SHOT))
        frames = []
        try:
            for k, t in enumerate(times):
                t = min(t, max(0.0, total - 0.05))
                dest = paths.plan_dir / f"ref_{index + 1:02d}_{k}.jpg"
                extract_frame(src, t, dest)
                frames.append({"file": dest.relative_to(paths.root).as_posix(), "t": round(t, 2)})
        except Exception as exc:
            log(f"[plan] frame shot source {index + 1} dilewat: {exc}")
            continue
        out.append({"index": index, "start_s": start, "end_s": end, "frames": frames})
    return out


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
