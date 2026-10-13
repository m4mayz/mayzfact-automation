import shutil

import pytest

from mayzfact.steps.plan import run_plan, subject_ranges
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


def plan_with(tmp_path, cut_video, hook_seconds, source=SOURCE):
    paths = RunPaths(tmp_path / "run")
    data = run_plan(
        paths, SCRIPT, TTS, source, max_shot_s=2.5, hook_seconds=hook_seconds,
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
        {"id": "hook", "label": "HOOK", "shots": [0], "keywords": {"en": ["horseshoe crab beach"], "zh": ["鲎 海滩"]}, "ref_frames": []},
        {"id": "horseshoe-crab", "label": "horseshoe crab", "shots": [1], "keywords": {"en": ["fossil", "crab"], "zh": ["化石", "螃蟹"]}, "ref_frames": []},
    ]
    _, data = plan_with(tmp_path / "b", cut_video, hook_seconds=0.0)
    assert [s["group"] for s in data["shots"]] == ["beat-1", "horseshoe-crab"]
    assert data["groups"][0]["label"] == "beat 1"


I2XAG = [
    {"text": "These are the top five ancient creatures", "start": 0.0, "duration": 4.1},
    {"text": "video ends. Number five, horseshoe crab.", "start": 15.8, "duration": 4.4},
    {"text": "this thing survived way too much. Number", "start": 26.0, "duration": 4.8},
    {"text": "four, nautilus. Wait, look at that", "start": 28.8, "duration": 3.8},
    {"text": "works. Number two, sturgeon. Look at", "start": 46.9, "duration": 4.4},
]


def test_subject_ranges_run_from_mention_to_next_subject():
    ranges = subject_ranges(I2XAG, ["horseshoe crab", "chambered nautilus", "sturgeon", "tardigrade"], 70.8)
    assert ranges["horseshoe crab"][0] == pytest.approx(18.6, abs=0.3)
    assert ranges["horseshoe crab"][1] == ranges["chambered nautilus"][0]
    assert ranges["chambered nautilus"][0] == pytest.approx(29.4, abs=0.3)
    assert ranges["sturgeon"][1] == 70.8
    assert "tardigrade" not in ranges


def test_plan_gives_source_frames_to_content_groups(tmp_path, cut_video):
    source = {**SOURCE, "transcript": [{"text": "intro words", "start": 0.0, "duration": 0.8},
                                       {"text": "Number five, horseshoe crab.", "start": 0.8, "duration": 1.0}]}
    paths, data = plan_with(tmp_path, cut_video, hook_seconds=1.5, source=source)
    crab = data["groups"][1]
    assert crab["ref_frames"] == ["plan/horseshoe-crab_0.jpg", "plan/horseshoe-crab_1.jpg", "plan/horseshoe-crab_2.jpg"]
    assert all((paths.root / f).exists() for f in crab["ref_frames"])
    assert data["groups"][0]["ref_frames"] == []


def test_subject_ranges_skip_intro_lists_and_partial_words():
    transcript = [
        {"text": "I feel these ancient creatures, the horseshoe crab and the coelacanth, are wild", "start": 0.0, "duration": 6.0},
        {"text": "Number five, eel. Slippery.", "start": 20.0, "duration": 4.0},
        {"text": "Number four, horseshoe crab.", "start": 40.0, "duration": 4.0},
        {"text": "Number three, coelacanth.", "start": 60.0, "duration": 4.0},
    ]
    ranges = subject_ranges(transcript, ["eel", "horseshoe crab", "coelacanth"], 120.0)
    assert 20.0 <= ranges["eel"][0] < 24.0
    assert 40.0 <= ranges["horseshoe crab"][0] < 44.0
    assert 60.0 <= ranges["coelacanth"][0] < 64.0 and ranges["coelacanth"][1] == 120.0
    assert subject_ranges(transcript, ["  "], 120.0) == {}


def test_group_of_reserves_hook_and_ignores_blank_subject():
    from mayzfact.steps.plan import group_of

    base = {"hook_segment": None, "beat": 2}
    assert group_of({**base, "subject": "Hook"}) == ("subject-hook", "Hook")
    assert group_of({**base, "subject": "   "}) == ("beat-3", "beat 3")


def test_plan_marks_countdown_shots(tmp_path, cut_video):
    _, data = plan_with(tmp_path, cut_video, hook_seconds=0.0)
    assert [s["countdown"] for s in data["shots"]] == [None, 5]
