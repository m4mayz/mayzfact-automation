import pytest

from mayzfact.errors import PipelineError
from mayzfact.steps.timeline import build_timeline, run_timeline, to_frame
from mayzfact.store import RunPaths, read_json
from tests.factories import fake_alignment


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


SCRIPT = {"beats": [{"text": "Look at this creature."}, {"text": "Number five, horseshoe crab."}, {"text": "It is old."}]}
ALIGN = fake_alignment("Look at this creature. Number five, horseshoe crab. It is old.", 6.2)
CD_CLIPS = {"shots": [shot("clips/shot_01.mp4", "video", 0.0, 1080, 1920), shot("clips/shot_02.mp4", "video", 2.3, 1080, 1920),
                      shot("clips/shot_03.jpg", "photo", 5.2, 1080, 1920)]}


def test_countdown_card_covers_countdown_beat():
    timeline = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN)
    assert timeline["countdown"] == [{
        "number": 5, "label": "HORSESHOE CRAB", "numberFrom": 69, "numberDuration": 33,
        "cardFrom": 102, "cardDuration": 54, "src": "clips/shot_02.mp4", "kind": "video", "clipOffset": 33,
    }]
    assert len(timeline["shots"]) == 3


def test_captions_one_word_each_outside_countdown():
    captions = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN)["captions"]
    assert [(c["text"], c["from"], c["durationInFrames"]) for c in captions] == [
        ("LOOK", 0, 15), ("AT", 15, 9), ("THIS", 24, 15), ("CREATURE", 39, 30),
        ("IT", 156, 9), ("IS", 165, 9), ("OLD", 174, 21),
    ]
    colors = {c["text"]: c["color"] for c in captions}
    assert colors["LOOK"] == colors["IT"] == "#ffffff" and colors["CREATURE"] == "#22d3ee"


def test_caption_colors_cycle_and_subject_words_are_colored():
    script = {"beats": [{"text": "Number two, eel."}, {"text": "The eel is enormous and ancient."}]}
    align = fake_alignment("Number two, eel. The eel is enormous and ancient.", 4.9)
    captions = build_timeline({"shots": [shot("clips/a.mp4", "video", 0.0, 1080, 1920)]}, 5.0, 0.5, script=script, alignment=align)["captions"]
    assert [(c["text"], c["color"]) for c in captions] == [
        ("THE", "#ffffff"), ("EEL", "#22d3ee"), ("IS", "#ffffff"), ("ENORMOUS", "#4ade80"), ("AND", "#ffffff"), ("ANCIENT", "#facc15")]


def test_unknown_number_has_no_card_and_keeps_captions():
    script = {"beats": [{"text": "Number eleven, x."}]}
    timeline = build_timeline({"shots": [shot("clips/a.mp4", "video", 0.0, 1080, 1920)]}, 2.0, 0.5,
                              script=script, alignment=fake_alignment("Number eleven, x.", 1.7))
    assert timeline["countdown"] == []
    assert [c["text"] for c in timeline["captions"]] == ["NUMBER", "ELEVEN", "X"]


def test_without_script_or_with_bad_alignment_timeline_still_builds():
    plain = build_timeline(CLIPS, 6.5, 0.5)
    assert plain["captions"] == [] and plain["countdown"] == []
    logs = []
    bad = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=fake_alignment("beda total", 1.0), log=logs.append)
    assert bad["captions"] == [] and bad["countdown"] == [] and logs


def test_warns_when_card_runs_past_its_clip():
    split = {"shots": [shot("clips/shot_01.mp4", "video", 0.0, 1080, 1920), shot("clips/shot_02.mp4", "video", 2.3, 1080, 1920),
                       shot("clips/shot_02b.mp4", "video", 4.0, 1080, 1920), shot("clips/shot_03.jpg", "photo", 5.2, 1080, 1920)]}
    logs = []
    timeline = build_timeline(split, 6.5, 0.5, script=SCRIPT, alignment=ALIGN, log=logs.append)
    assert timeline["countdown"][0]["src"] == "clips/shot_02.mp4"
    assert any("--from" in line for line in logs)
    logs.clear()
    build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN, log=logs.append)
    assert logs == []


def test_short_end_times_fall_back_without_crash():
    bad = {**ALIGN, "character_end_times_seconds": ALIGN["character_end_times_seconds"][:5]}
    timeline = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=bad, log=lambda m: None)
    assert timeline["captions"] == [] and timeline["countdown"] == []


AUDIO = {"bgm": "audio/bgm/mystery.mp3", "sfx": {"hook": "audio/sfx/h.mp3", "number": "audio/sfx/n.mp3",
                                                 "subject": "audio/sfx/s.mp3", "cut": "audio/sfx/c.mp3"}}


def test_sfx_and_bgm_placement():
    timeline = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN, audio=AUDIO)
    assert timeline["bgm"] == {"src": "audio/bgm/mystery.mp3", "volume": 0.12, "fadeOutFrames": 30}
    # shot ke-2 ketutup card → nggak dapat "cut"; card dapat "number" + "subject"; shot ke-3 dapat "cut" 3 frame sebelum ganti.
    assert timeline["sfx"] == [
        {"src": "audio/sfx/h.mp3", "from": 0, "volume": 0.8},
        {"src": "audio/sfx/n.mp3", "from": 69, "volume": 0.9},
        {"src": "audio/sfx/s.mp3", "from": 99, "volume": 0.7},
        {"src": "audio/sfx/c.mp3", "from": 153, "volume": 0.35},
    ]


def test_cut_sfx_on_plain_shots_and_missing_audio():
    timeline = build_timeline(CLIPS, 6.5, 0.5, audio={"bgm": None, "sfx": {"cut": "audio/sfx/c.mp3"}})
    assert timeline["bgm"] is None
    assert [s["from"] for s in timeline["sfx"]] == [69, 129]
    plain = build_timeline(CLIPS, 6.5, 0.5)
    assert plain["bgm"] is None and plain["sfx"] == []
