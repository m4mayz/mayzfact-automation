import shutil

from mayzfact.steps.plan import run_plan
from mayzfact.store import RunPaths, read_json
from tests.factories import fake_alignment

SCRIPT = {
    "beats": [
        {"text": "Look at this.", "media": "video", "queries": ["crab"], "subject": ""},
        {"text": "Number five, horseshoe crab.", "media": "photo", "queries": ["fossil", "crab"]},
    ],
    "fallback_query": "animals",
}
TTS = {"duration_s": 3.0, "alignment": fake_alignment("Look at this. Number five, horseshoe crab.", 2.4)}
SOURCE = {"video_id": "abc", "duration_s": 2.0, "transcript": [{"text": "five ancient creatures", "start": 0.0, "duration": 2.0}]}


def plan_with(tmp_path, cut_video, hook_seconds):
    paths = RunPaths(tmp_path / "run")
    data = run_plan(
        paths, SCRIPT, TTS, SOURCE, max_shot_s=2.5, hook_seconds=hook_seconds,
        download_source=lambda vid, dest: shutil.copyfile(cut_video, dest) or dest,
        describe=lambda infos, frames: {0: {"en": ["horseshoe crab beach"], "zh": ["鲎 海滩"]}},
        translate=lambda queries: {"fossil": "化石", "crab": "螃蟹"},
        log=lambda m: None,
    )
    return paths, data


def test_plan_marks_hook_shots_with_reference_frames(tmp_path, cut_video):
    paths, data = plan_with(tmp_path, cut_video, hook_seconds=1.5)
    assert read_json(paths.shots_plan_json) == data
    first, second = data["shots"]
    assert first["hook_segment"] == 0
    assert first["keywords"] == {"en": ["horseshoe crab beach"], "zh": ["鲎 海滩"]}
    assert len(first["ref_frames"]) == 3 and (paths.root / first["ref_frames"][0]).exists()
    assert second["hook_segment"] is None and second["ref_frames"] == []
    assert second["keywords"] == {"en": ["fossil", "crab"], "zh": ["化石", "螃蟹"]}
    assert second["subject"] == "horseshoe crab"
    assert (second["start_s"], second["end_s"], second["text"]) == (first["end_s"], 3.0, "Number five, horseshoe crab.")
    assert data["segments"][0]["frames"][0] == "plan/seg_01_0.jpg"


def test_plan_without_hook_area(tmp_path, cut_video):
    _, data = plan_with(tmp_path, cut_video, hook_seconds=0.0)
    assert all(shot["hook_segment"] is None for shot in data["shots"])


def test_plan_groups_shots_by_context(tmp_path, cut_video):
    _, data = plan_with(tmp_path, cut_video, hook_seconds=1.5)
    assert [s["group"] for s in data["shots"]] == ["hook", "horseshoe-crab"]
    assert data["groups"] == [
        {"id": "hook", "label": "HOOK", "shots": [0], "keywords": {"en": ["horseshoe crab beach"], "zh": ["鲎 海滩"]}},
        {"id": "horseshoe-crab", "label": "horseshoe crab", "shots": [1], "keywords": {"en": ["fossil", "crab"], "zh": ["化石", "螃蟹"]}},
    ]
    _, data = plan_with(tmp_path / "b", cut_video, hook_seconds=0.0)
    assert [s["group"] for s in data["shots"]] == ["beat-1", "horseshoe-crab"]
    assert data["groups"][0]["label"] == "beat 1"
