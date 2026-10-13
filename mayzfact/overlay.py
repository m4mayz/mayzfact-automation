"""Posisi subjek per shot (OWLv2) dalam koordinat layar 1080x1920, buat panah/lingkaran (spec Fase 3C-1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from mayzfact.countdown import parse_countdown
from mayzfact.ffmpeg import extract_frame
from mayzfact.media import FRAME_H, FRAME_W, fg_height, layout_for
from mayzfact.steps.clips import beat_subjects
from mayzfact.store import RunPaths, read_json, write_json_atomic

MIN_SCORE = 0.12
MIN_VALID = 0.5
SAMPLE_EVERY_S = 1.0
DETECT_WIDTH = 960


def screen_box(box: tuple[float, float, float, float], width: int, height: int, *, fg_min_ratio: float) -> tuple[int, int, int, int]:
    """Kotak (0..1 di frame klip) → (x, y, w, h) piksel di layar 1080x1920, ngikutin layout full/blur."""
    if layout_for(width, height) == "full":
        area_y, area_h = 0, FRAME_H
    else:
        area_h = fg_height(width, height, fg_min_ratio)
        area_y = (FRAME_H - area_h) // 2
    scale = max(FRAME_W / width, area_h / height)  # objectFit cover
    off_x = (FRAME_W - width * scale) / 2
    off_y = area_y + (area_h - height * scale) / 2
    x0, y0, x1, y1 = box
    return (round(off_x + x0 * width * scale), round(off_y + y0 * height * scale),
            round((x1 - x0) * width * scale), round((y1 - y0) * height * scale))


def fill_points(points: list[dict | None]) -> list[dict] | None:
    """Titik hilang diisi titik valid terdekat. None kalau titik valid kurang dari setengah."""
    valid = [i for i, p in enumerate(points) if p]
    if not points or len(valid) < MIN_VALID * len(points):
        return None
    return [dict(points[min(valid, key=lambda v: abs(v - i))]) for i in range(len(points))]


def sample_times(kind: str, duration_s: float) -> list[float]:
    if kind != "video":
        return [0.0]
    times = []
    t = SAMPLE_EVERY_S / 2
    while t < duration_s:
        times.append(round(t, 3))
        t += SAMPLE_EVERY_S
    return times or [round(duration_s / 2, 3)]


def shot_query(clip: dict, beats: list[dict], subjects: list[str | None], plan: dict | None) -> str | None:
    if subjects[clip["beat"]]:
        return subjects[clip["beat"]]
    if plan:
        for shot in plan.get("shots", []):
            if shot["index"] == clip["index"] and shot.get("keywords", {}).get("en"):
                return shot["keywords"]["en"][0]
    queries = beats[clip["beat"]].get("queries") or []
    return queries[0] if queries else None


def prepare_overlays(
    paths: RunPaths, clips: dict, script: dict, plan: dict | None, detector: Any, *, fg_min_ratio: float,
    log: Callable[[str], None],
) -> dict[str, dict]:
    """{file: {"key", "points": [{"t", "x", "y", "w", "h"}] | None}}. Hasil di-cache di overlays.json."""
    beats = script["beats"]
    subjects = beat_subjects(beats)
    cache_path = paths.root / "overlays.json"
    cache = read_json(cache_path) if cache_path.exists() else {}
    out: dict[str, dict] = {}
    for clip in clips["shots"]:
        countdown = parse_countdown(beats[clip["beat"]].get("text", ""))
        if countdown and countdown.number is not None:
            continue  # shot ini ketutup card countdown
        query = shot_query(clip, beats, subjects, plan)
        source = paths.root / clip["file"]
        if not query or not source.exists():
            continue
        stat = source.stat()
        key = f"{stat.st_size}-{stat.st_mtime_ns}-{query}"
        if cache.get(clip["file"], {}).get("key") == key:
            out[clip["file"]] = cache[clip["file"]]
            continue
        times = sample_times(clip["kind"], clip["end_s"] - clip["start_s"])
        found: list[dict | None] = []
        for i, t in enumerate(times):
            image = source if clip["kind"] != "video" else extract_frame(
                source, t, paths.root / "overlay" / f"{Path(clip['file']).stem}_{i:02d}.jpg", width=DETECT_WIDTH)
            hit = detector.best_box(image, query)
            if hit and hit[0] >= MIN_SCORE:
                x, y, w, h = screen_box(hit[1], clip["width"], clip["height"], fg_min_ratio=fg_min_ratio)
                found.append({"x": x, "y": y, "w": w, "h": h})
            else:
                found.append(None)
        filled = fill_points(found)
        points = [dict(p, t=t) for p, t in zip(filled, times)] if filled else None
        points = [{"t": p["t"], "x": p["x"], "y": p["y"], "w": p["w"], "h": p["h"]} for p in points] if points else None
        out[clip["file"]] = {"key": key, "points": points}
        log(f"[timeline] overlay {clip['file']} ({query}): " + (f"{len(times)} titik" if points else "subjek nggak kedeteksi, tanpa panah"))
    write_json_atomic(cache_path, out)
    return out
