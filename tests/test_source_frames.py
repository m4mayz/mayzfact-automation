import shutil

from mayzfact.errors import PipelineError
from mayzfact.source_frames import (
    _spread,
    prepare_source_segments,
    source_shot_frames,
    transcript_near,
)
from mayzfact.store import RunPaths

SOURCE = {"video_id": "abc", "duration_s": 2.0, "transcript": [{"text": "five ancient creatures", "start": 0.0, "duration": 2.0}]}


def test_prepare_source_segments_writes_frames_to_out_dir(tmp_path, cut_video, make_photo):
    paths = RunPaths(tmp_path / "run")
    segs = prepare_source_segments(paths, SOURCE, lambda vid, dest: shutil.copyfile(cut_video, dest) or dest, 10.0, paths.root / "plan")
    assert len(segs) == 2
    assert all(len(s["frames"]) == 3 and s["frames"][0].parent.name == "plan" for s in segs)
    assert segs[0]["transcript"] == "five ancient creatures"


def test_transcript_near():
    transcript = [{"text": "These are the top five", "start": 0.0, "duration": 2.0},
                  {"text": "horseshoe crab look", "start": 2.0, "duration": 2.0},
                  {"text": "later", "start": 9.0, "duration": 1.0}]
    assert transcript_near(transcript, 1.5, 3.0) == "These are the top five horseshoe crab look"
    assert transcript_near(transcript, 4.5, 8.0) == ""


def test_source_shot_frames_two_seeded_frames_per_cut(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "run")
    copy = lambda vid, dest: shutil.copyfile(cut_video, dest) or dest  # noqa: E731
    shots = source_shot_frames(paths, SOURCE, copy, log=lambda m: None)
    assert [(s["index"], s["start_s"], s["end_s"]) for s in shots] == [(0, 0.0, 1.0), (1, 1.0, 2.0)]
    assert [f["file"] for f in shots[0]["frames"]] == ["plan/ref_01_0.jpg", "plan/ref_01_1.jpg"]
    assert all((paths.root / f["file"]).exists()
               and s["start_s"] + 0.15 * (s["end_s"] - s["start_s"]) <= f["t"]
               <= s["end_s"] - 0.15 * (s["end_s"] - s["start_s"])
               for s in shots for f in s["frames"])
    assert source_shot_frames(paths, SOURCE, copy, log=lambda m: None) == shots  # seed video_id: sama tiap plan ulang
    other = source_shot_frames(paths, {**SOURCE, "video_id": "xyz"}, copy, log=lambda m: None)
    assert [f["t"] for s in other for f in s["frames"]] != [f["t"] for s in shots for f in s["frames"]]


def test_source_shot_frames_missing_source_returns_empty(tmp_path):
    def fail(vid, dest):
        raise PipelineError("source", "download gagal")

    logs = []
    assert source_shot_frames(RunPaths(tmp_path / "run"), SOURCE, fail, log=logs.append) == []
    assert logs


def test_spread_covers_whole_source():
    assert _spread(3, 60) == [0, 1, 2]
    picks = _spread(250, 60)
    assert len(picks) == 60 and picks[0] == 0 and picks[-1] == 249 and picks == sorted(set(picks))
