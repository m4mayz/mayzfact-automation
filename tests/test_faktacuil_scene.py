import math

import pytest

from mayzfact.cta import clean
from mayzfact.cta_scene import build_scene, faktacuil_cta_stop
from mayzfact.steps.timeline import FPS, _beat_of, _shot_entries
from mayzfact.timing import word_timings
from tests.faktacuil_fixtures import faktacuil_script, faktacuil_timeline_fixture


def v2(fmt):
    return faktacuil_script(cta=fmt).model_dump()


def scene_inputs(script=None, duration=25):
    script, alignment, clips = faktacuil_timeline_fixture(duration, script)
    total = math.ceil(duration * FPS - 1e-6)
    entries = _shot_entries(clips["shots"], total, 0.5)
    words = word_timings(alignment)
    return script, clips, entries, words, _beat_of(words, script["beats"]), total


def frame(words, token):
    return int(math.floor(next(w for w in words if clean(w["text"]) == token)["start_s"] * FPS + 0.5))


def build(script):
    script, clips, entries, words, beat_of, total = scene_inputs(script)
    return build_scene(script, clips["shots"], entries, words, beat_of, [], total)


def test_lucky_scene_has_like_stage_only():
    script = v2("lucky")
    scene = build(script)
    assert scene["style"] == "faktacuil" and scene["format"] == "lucky" and scene["theme"] == "honey"
    assert [s["kind"] for s in scene["stages"]] == ["like"] and [c["kind"] for c in scene["cues"]] == ["like"]
    assert "commentText" not in scene and "emoji" not in scene
    words = scene_inputs(script)[3]
    assert scene["stages"][0]["from"] == frame(words, "coba")


def test_subscribe_scene_cues_subscribe_word():
    script = v2("subscribe")
    scene = build(script)
    assert [c["kind"] for c in scene["cues"]] == ["like", "subscribe"]
    words = scene_inputs(script)[3]
    assert next(c for c in scene["cues"] if c["kind"] == "subscribe")["from"] == frame(words, "subscribe")
    like, sub = scene["stages"]
    assert like["from"] + like["durationInFrames"] == sub["from"]


def test_emoji_scene_runs_to_video_end():
    script = v2("emoji")
    scene = build(script)
    total = scene_inputs(script)[5]
    assert scene["from"] + scene["durationInFrames"] == total and scene["emoji"] == "🍯" and "theme" not in scene


def test_emoji_scene_clicks_on_emoji_word():
    script = v2("emoji")
    scene = build(script)
    words = scene_inputs(script)[3]
    cue = scene["cues"][0]
    assert cue["word"].strip(",?").lower() == "emoji" and cue["from"] == frame(words, "emoji")
    like = scene["stages"][0]
    assert like["from"] <= cue["from"] and like["triggerAt"] == cue["from"] - like["from"]


def test_subscribe_before_like_drops_stage_and_cue():
    script = v2("subscribe")
    script["beats"][4]["text"] = "Tapi subscribe dulu, coba tekan like,"
    scene = build(script)
    assert [s["kind"] for s in scene["stages"]] == ["like"]
    assert [c["kind"] for c in scene["cues"]] == ["like"]


def test_scene_is_none_without_cta_scene():
    s = v2("lucky")
    s["cta_scene"] = None
    assert build(s) is None


def test_faktacuil_scene_stops_when_answer_starts():
    script, clips, entries, words, beat_of, total = scene_inputs()
    scene = build_scene(script, clips["shots"], entries, words, beat_of, [], total)
    answer_start = next(e["from"] for e, s in zip(entries, clips["shots"]) if s["beat"] == 6)
    assert scene["from"] + scene["durationInFrames"] == answer_start
    assert faktacuil_cta_stop(clips["shots"], entries, {4, 5}, total) == answer_start


def test_faktacuil_cta_stop_falls_back_to_total():
    script, clips, entries, words, beat_of, total = scene_inputs()
    last = max(s["beat"] for s in clips["shots"])
    assert faktacuil_cta_stop(clips["shots"], entries, {last}, total) == total


def test_faktacuil_cta_markup_runs_in_node():
    import shutil
    import subprocess
    from pathlib import Path

    node = shutil.which("node")
    if not node:
        pytest.skip("Node dibutuhkan untuk tes komponen Remotion")
    root = Path(__file__).resolve().parents[1] / "remotion"
    result = subprocess.run([node, "tests/faktacuil-cta.cjs"], cwd=root, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "faktacuil cta: OK" in result.stdout
