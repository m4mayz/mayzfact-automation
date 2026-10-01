"""Step timeline: detik → frame, tentuin layout tiap shot, tulis props buat Remotion."""

from __future__ import annotations

import math

from mayzfact.errors import PipelineError
from mayzfact.media import FRAME_H, FRAME_W, PHOTO_ZOOM, fg_height, layout_for
from mayzfact.store import RunPaths, write_json_atomic

FPS = 30


def to_frame(seconds: float, fps: int = FPS) -> int:
    return int(math.floor(seconds * fps + 0.5))


def build_timeline(clips: dict, audio_duration_s: float, fg_min_ratio: float) -> dict:
    shots = clips["shots"]
    if not shots:
        raise PipelineError("timeline", "clips.json kosong.")
    total = math.ceil(audio_duration_s * FPS - 1e-6)
    starts = [0] + [to_frame(s["start_s"]) for s in shots[1:]]
    entries = []
    for index, shot in enumerate(shots):
        end = starts[index + 1] if index + 1 < len(shots) else total
        if end <= starts[index]:
            raise PipelineError("timeline", f"Shot {index + 1} jadi 0 frame setelah dibulatin.")
        layout = layout_for(shot["width"], shot["height"])
        entry = {
            "src": shot["file"].replace("\\", "/"),
            "kind": shot["kind"],
            "layout": layout,
            "from": starts[index],
            "durationInFrames": end - starts[index],
        }
        if layout == "blur":
            entry["fgHeight"] = fg_height(shot["width"], shot["height"], fg_min_ratio)
        entries.append(entry)
    return {
        "fps": FPS,
        "width": FRAME_W,
        "height": FRAME_H,
        "durationInFrames": total,
        "audio": "voice.mp3",
        "photoZoom": PHOTO_ZOOM,
        "shots": entries,
    }


def run_timeline(paths: RunPaths, clips: dict, tts: dict, *, fg_min_ratio: float) -> dict:
    data = build_timeline(clips, tts["duration_s"], fg_min_ratio)
    write_json_atomic(paths.timeline_json, data)
    return data
