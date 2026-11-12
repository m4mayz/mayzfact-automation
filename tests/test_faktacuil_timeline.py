import pytest

from mayzfact.config import Settings
from mayzfact.pipeline import run_pipeline
from mayzfact.steps.timeline import CAPTION_KEYWORD, build_timeline, to_frame
from mayzfact.store import RunPaths, read_json
from mayzfact.timing import word_timings
from tests.faktacuil_fixtures import (
    faktacuil_script,
    faktacuil_timeline_fixture,
)
from tests.test_faktacuil_pipeline import write_faktacuil_run
from tests.test_pipeline import QUIET, VIDEO_ID, build_world

AUDIO_ALL_SFX = {"bgm": None, "bgm_main": "audio/bgm/main.mp3", "riser_s": 2.0, "sfx": {
    "hook": "audio/sfx/hook.mp3", "hook_cut": "audio/sfx/hook_cut.mp3", "hook_extra_gasp": "audio/sfx/gasp.mp3",
    "cut": "audio/sfx/cut.mp3", "click": "audio/sfx/click.mp3", "extra_oof": "audio/sfx/oof.mp3",
    "number": "audio/sfx/number.mp3", "subject": "audio/sfx/subject.mp3", "item_reveal": "audio/sfx/reveal.mp3",
    "riser": "audio/sfx/riser.mp3", "emoji": "audio/sfx/emoji.mp3", "overlay": "audio/sfx/overlay.mp3"}}
KEYWORDS = {"kardus", "kucing"}  # keyword di faktacuil_script


def timeline(audio=AUDIO_ALL_SFX, script=None, **kwargs):
    script, alignment, clips = faktacuil_timeline_fixture(25, script)
    return build_timeline(clips, 25, 0.5, script=script, alignment=alignment, audio=audio, log=lambda m: None, **kwargs)


def test_faktacuil_timeline_shape():
    tl = timeline()
    assert tl["captionStyle"] == "faktacuil"
    assert tl["countdown"] == [] and tl["overlays"] == [] and tl["emojis"] == []
    assert tl["intro"] == {"durationInFrames": 7} and tl["flashes"] == [] and tl["transitions"] == []
    srcs = [s["src"] for s in tl["sfx"]]
    assert "audio/sfx/hook.mp3" in srcs and "audio/sfx/hook_cut.mp3" not in srcs
    assert "audio/sfx/gasp.mp3" not in srcs and "audio/sfx/riser.mp3" not in srcs
    assert srcs.count("audio/sfx/click.mp3") == 1  # 1 klik di kata like
    assert "audio/sfx/cut.mp3" in srcs


def test_faktacuil_click_lands_on_like_word():
    script, alignment, clips = faktacuil_timeline_fixture(25)
    like = next(w for w in word_timings(alignment) if w["text"].strip(",").lower() == "like")
    tl = timeline()
    click = next(s for s in tl["sfx"] if s["src"] == "audio/sfx/click.mp3")
    assert abs(click["from"] - to_frame(like["start_s"])) <= 8  # klik di kata like, bukan di "like-mu"
    scene = tl["ctaScene"]
    assert scene["from"] <= click["from"] < scene["from"] + scene["durationInFrames"]


def test_top3_timeline_has_no_caption_style():
    from tests.test_cta_scene import timeline_fixture

    script, alignment, clips = timeline_fixture()
    tl = build_timeline(clips, 20, 0.5, script=script, alignment=alignment)
    assert "captionStyle" not in tl


def test_faktacuil_caption_colors_only_keywords():
    tl = timeline()
    colored = {c["text"] for c in tl["captions"] if c["color"] != "#ffffff"}
    assert colored == {kw.upper() for kw in KEYWORDS}
    assert all(c["color"] in ("#ffffff", CAPTION_KEYWORD) for c in tl["captions"])
    assert CAPTION_KEYWORD == "#FFC53D"


def test_faktacuil_long_words_are_not_colored():
    script = faktacuil_script().model_dump()
    script["beats"][2]["text"] = "Padahal membersihkannya susah banget,"
    script["beats"][2]["keyword"] = ""
    tl = timeline(script=script)
    assert next(c for c in tl["captions"] if c["text"] == "MEMBERSIHKANNYA")["color"] == "#ffffff"


def test_faktacuil_single_bgm_whole_video():
    tl = timeline({"bgm": None, "bgm_main": "audio/bgm/main.mp3", "sfx": {}})
    assert tl["bgm"] == [{"src": "audio/bgm/main.mp3", "from": 0, "durationInFrames": tl["durationInFrames"],
                          "volume": 0.06, "fadeOutFrames": 30}]  # FAKTACUIL_BGM_VOLUME: BGM ~14 dB di bawah voice


def test_faktacuil_ignores_marks_and_overlays_passed_in():
    script, alignment, clips = faktacuil_timeline_fixture(25)
    marks = {"beats": [dict(point=True, emoji="x", emoji_word="") for _ in script["beats"]], "emoji": {"x": "x.json"}}
    detections = {s["file"]: {"points": [dict(t=0, x=300, y=600, w=200, h=200)]} for s in clips["shots"]}
    tl = build_timeline(clips, 25, 0.5, script=script, alignment=alignment, marks=marks, overlays=detections,
                        audio=AUDIO_ALL_SFX, log=lambda m: None)
    assert tl["emojis"] == [] and tl["overlays"] == []


@pytest.fixture
def world(tmp_path, long_mp3, make_video, make_photo):
    return build_world(tmp_path, long_mp3, 30.0, make_video, make_photo)


def test_pipeline_skips_marks_and_overlay_for_faktacuil(world):
    write_faktacuil_run(RunPaths(world.runs / VIDEO_ID))

    def forbidden(*args, **kwargs):
        pytest.fail("marks/overlay nggak boleh dipanggil buat FaktaCuil")

    world.deps.marks, world.deps.overlay = forbidden, forbidden
    paths = run_pipeline(VIDEO_ID, settings=Settings(elevenlabs_api_keys=("k",)), deps=world.deps,
                         runs_dir=world.runs, no_render=True, **QUIET)
    tl = read_json(paths.timeline_json)
    assert tl["captionStyle"] == "faktacuil" and tl["emojis"] == [] and tl["overlays"] == []


def test_faktacuil_ignores_hook_segments_in_clips():
    script, alignment, clips = faktacuil_timeline_fixture(25)
    for shot in clips["shots"][:2]:
        shot["hook_segment"] = 0  # run lama/kotor: nggak boleh bikin flash atau SFX hook_cut
    tl = build_timeline(clips, 25, 0.5, script=script, alignment=alignment, audio=AUDIO_ALL_SFX, log=lambda m: None)
    srcs = [s["src"] for s in tl["sfx"]]
    assert tl["flashes"] == [] and "audio/sfx/hook_cut.mp3" not in srcs and "audio/sfx/gasp.mp3" not in srcs
