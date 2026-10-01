import pytest

from mayzfact.errors import PipelineError
from mayzfact.steps.timeline import build_timeline, run_timeline, to_frame
from mayzfact.store import RunPaths, read_json


def shot(file, kind, start_s, width, height):
    return {"file": file, "kind": kind, "start_s": start_s, "width": width, "height": height}


CLIPS = {
    "shots": [
        shot("clips/shot_01.mp4", "video", 0.0, 1080, 1920),
        shot("clips/shot_02.jpg", "photo", 2.4, 1600, 1000),
        shot("clips/shot_03.mp4", "video", 4.4, 1920, 1080),
    ]
}


def test_to_frame_rounds_half_up():
    assert to_frame(0.0) == 0
    assert to_frame(2.4) == 72
    assert to_frame(0.0167) == 1
    assert to_frame(0.0166) == 0


def test_build_timeline_frames_layouts_and_total():
    timeline = build_timeline(CLIPS, audio_duration_s=6.5, fg_min_ratio=0.5)
    assert (timeline["fps"], timeline["width"], timeline["height"], timeline["durationInFrames"]) == (30, 1080, 1920, 195)
    assert (timeline["audio"], timeline["photoZoom"]) == ("voice.mp3", 1.08)
    assert timeline["shots"] == [
        {"src": "clips/shot_01.mp4", "kind": "video", "layout": "full", "from": 0, "durationInFrames": 72},
        {"src": "clips/shot_02.jpg", "kind": "photo", "layout": "blur", "from": 72, "durationInFrames": 60, "fgHeight": 960},
        {"src": "clips/shot_03.mp4", "kind": "video", "layout": "blur", "from": 132, "durationInFrames": 63, "fgHeight": 960},
    ]
    assert sum(s["durationInFrames"] for s in timeline["shots"]) == timeline["durationInFrames"]


def test_backslash_paths_become_forward_slashes():
    timeline = build_timeline({"shots": [shot("clips\\shot_01.mp4", "video", 0.0, 1080, 1920)]}, 2.0, 0.5)
    assert timeline["shots"][0]["src"] == "clips/shot_01.mp4"


def test_zero_frame_shot_is_an_error():
    clips = {"shots": [shot("clips/a.mp4", "video", 0.0, 1080, 1920), shot("clips/b.mp4", "video", 0.01, 1080, 1920)]}
    with pytest.raises(PipelineError, match="0 frame"):
        build_timeline(clips, 2.0, 0.5)


def test_run_timeline_writes_json(tmp_path):
    paths = RunPaths(tmp_path)
    data = run_timeline(paths, CLIPS, {"duration_s": 6.5}, fg_min_ratio=0.5)
    assert read_json(paths.timeline_json) == data
