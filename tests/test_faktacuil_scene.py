import math

from mayzfact.cta import clean
from mayzfact.cta_scene import build_scene, faktacuil_cta_stop
from mayzfact.steps.timeline import FPS, _beat_of, _shot_entries
from mayzfact.timing import word_timings
from tests.faktacuil_fixtures import faktacuil_timeline_fixture


def scene_inputs(script=None, duration=25):
    script, alignment, clips = faktacuil_timeline_fixture(duration, script)
    total = math.ceil(duration * FPS - 1e-6)
    entries = _shot_entries(clips["shots"], total, 0.5)
    words = word_timings(alignment)
    return script, clips, entries, words, _beat_of(words, script["beats"]), total


def frame(words, token):
    return int(math.floor(next(w for w in words if clean(w["text"]) == token)["start_s"] * FPS + 0.5))


def test_faktacuil_scene_has_like_and_transform_only():
    script, clips, entries, words, beat_of, total = scene_inputs()
    scene = build_scene(script, clips["shots"], entries, words, beat_of, [], total)
    assert [s["kind"] for s in scene["stages"]] == ["like", "transform"]
    assert {c["kind"] for c in scene["cues"]} == {"like", "transform"}
    like_cue = next(c for c in scene["cues"] if c["kind"] == "like")
    assert like_cue["word"].strip(",").lower() == "like"
    assert like_cue["from"] == frame(words, "like")  # bukan "like-mu" di beat gimmick
    assert scene["stages"][0]["from"] == frame(words, "coba")  # stage mulai di "coba"
    assert scene["stages"][1]["from"] == frame(words, "berubah")


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


def test_faktacuil_scene_ignores_subscribe_and_comment_words():
    script, *_ = scene_inputs()
    script["beats"][4]["text"] = "Tapi coba tekan like dulu, subscribe komen,"
    script, clips, entries, words, beat_of, total = scene_inputs(script)
    scene = build_scene(script, clips["shots"], entries, words, beat_of, [], total)
    assert [s["kind"] for s in scene["stages"]] == ["like", "transform"]
    assert {c["kind"] for c in scene["cues"]} == {"like", "transform"}
