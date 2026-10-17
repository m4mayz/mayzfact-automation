import shutil

from mayzfact.source_frames import prepare_source_segments, transcript_near
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
