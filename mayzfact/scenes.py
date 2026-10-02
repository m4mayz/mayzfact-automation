"""Deteksi cut di awal video source, terus pecah jadi segmen (spec Fase 2 4.1)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from mayzfact.errors import PipelineError

SCENE_THRESHOLD = 0.25
MIN_CUT_GAP_S = 0.4
MIN_SEGMENT_S = 0.5
_PTS = re.compile(r"pts_time:([0-9.]+)")


def detect_cuts(path: Path, max_s: float) -> list[float]:
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-t", f"{max_s:.3f}", "-i", str(path), "-an",
            "-vf", f"scale=320:-2,select='gt(scene,{SCENE_THRESHOLD})',showinfo", "-f", "null", "-",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise PipelineError("hook", f"Scene detect gagal:\n{result.stderr[-1500:]}")
    return [float(t) for t in _PTS.findall(result.stderr)]


def merge_cuts(times: list[float], min_gap: float = MIN_CUT_GAP_S) -> list[float]:
    """Cut yang rapat (transisi whip-blur) jadi 1. Wakilnya cut terakhir, pas shot baru udah kelihatan penuh."""
    groups: list[list[float]] = []
    for t in sorted(times):
        if groups and t - groups[-1][-1] < min_gap:
            groups[-1].append(t)
        else:
            groups.append([t])
    return [round(group[-1], 3) for group in groups]


def segments(cuts: list[float], end_s: float, min_len: float = MIN_SEGMENT_S) -> list[tuple[float, float]]:
    bounds = [0.0] + [c for c in cuts if 0 < c < end_s] + [end_s]
    return [
        (round(a, 3), round(b, 3)) for a, b in zip(bounds, bounds[1:]) if b - a >= min_len - 1e-9
    ]
