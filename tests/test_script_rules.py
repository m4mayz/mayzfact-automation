from mayzfact.models import Beat, Script
from mayzfact.steps.script import (
    check_script,
    normalize_script,
    target_duration,
    word_range,
)
from tests.factories import make_script

SOURCE = {
    "video_id": "i2xag_1OJfM",
    "duration_s": 70.8,
    "transcript": [
        {"text": "These are the top five ancient creatures that still exist today.", "start": 0.0, "duration": 2.5},
        {"text": "to this video", "start": 2.5, "duration": 1.8},
    ],
}
SOURCE_TEXT = " ".join(s["text"] for s in SOURCE["transcript"])
DURATION = target_duration(70.8, 0.6, 32)


def test_target_duration_and_word_range():
    assert round(DURATION, 2) == 42.48
    assert target_duration(40, 0.6, 32) == 32
    assert word_range(DURATION) == (110, 94, 126)


def test_good_script_has_no_problems():
    problems, overlap = check_script(make_script(), SOURCE_TEXT, DURATION)
    assert problems == []
    assert overlap == 0.0


def test_word_count_outside_range_is_reported():
    problems, _ = check_script(make_script(words_per_beat=5), SOURCE_TEXT, DURATION)
    assert any("words" in p for p in problems)


def test_photo_share_outside_range_is_reported():
    problems, _ = check_script(make_script(photo_every=1), SOURCE_TEXT, DURATION)
    assert any("photo" in p for p in problems)


def test_copied_phrases_are_reported():
    copied = Script(
        beats=[Beat(text=SOURCE_TEXT, media="video", queries=["crab"])] * 10,
        fallback_query="animals",
    )
    problems, overlap = check_script(copied, SOURCE_TEXT, DURATION)
    # Nggak persis 1.0: kalimat yang diulang bikin 4-gram lintas kalimat yang nggak ada di source.
    assert overlap > 0.5
    assert any("copied" in p for p in problems)


def test_empty_queries_and_fallback_are_reported():
    script = make_script()
    script = script.model_copy(
        update={
            "beats": [script.beats[0].model_copy(update={"queries": []}), *script.beats[1:]],
            "fallback_query": "",
        }
    )
    problems, _ = check_script(script, SOURCE_TEXT, DURATION)
    assert "Beat 1 has no search queries." in problems
    assert "fallback_query is empty." in problems


def test_normalize_script_cleans_text_and_forces_first_video():
    raw = Script(
        beats=[
            Beat(text="It’s  here —now", media="photo", queries=[" crab ", " "]),
            Beat(text="Second", media="photo", queries=["fossil"]),
        ],
        fallback_query="  ocean  ",
    )
    script = normalize_script(raw)
    assert script.beats[0].text == "It's here, now"
    assert script.beats[0].media == "video"
    assert script.beats[0].queries == ["crab"]
    assert script.beats[1].media == "photo"
    assert script.fallback_query == "ocean"



def test_long_beat_is_reported():
    script = make_script()
    long_beat = script.beats[1].model_copy(update={"text": " ".join(f"x{j}" for j in range(12)) + "."})
    script = script.model_copy(update={"beats": [script.beats[0], long_beat, *script.beats[2:]]})
    problems, _ = check_script(script, SOURCE_TEXT, DURATION)
    assert any(p.startswith("Beat 2 has 12 words") for p in problems)


def test_normalize_script_keeps_subject_trimmed():
    raw = Script(beats=[Beat(text="Number five, horseshoe crab.", media="video", queries=["crab"], subject="  horseshoe crab ")], fallback_query="ocean")
    assert normalize_script(raw).beats[0].subject == "horseshoe crab"
    assert Beat(text="x", media="video", queries=["q"]).subject == ""


def test_countdown_item_with_fewer_than_two_explanation_beats_is_reported():
    beats = [
        Beat(text="Here are five ancient creatures still alive!", media="video", queries=["creatures"]),
        Beat(text="Number five, horseshoe crab.", media="photo", queries=["crab"]),
        Beat(text="It looks like a prehistoric tank.", media="video", queries=["crab crawling"]),
        Beat(text="Number four, nautilus.", media="photo", queries=["nautilus"]),
        Beat(text="It floated before dinosaurs existed.", media="video", queries=["nautilus swim"]),
        Beat(text="Its spiral shell is pure geometry.", media="video", queries=["nautilus shell"]),
        Beat(text="Number one, common kestrel.", media="photo", queries=["kestrel"]),
        Beat(text="It hovers motionless in the wind.", media="video", queries=["kestrel hover"]),
        Beat(text="Its eyes track tiny mice below.", media="video", queries=["kestrel hunting"]),
    ]
    script = Script(beats=beats, fallback_query="ancient creatures")
    problems, _ = check_script(script, SOURCE_TEXT, DURATION)
    assert any("Number five" in p and "explanation beat" in p for p in problems)
    # Number four and Number one have 2 explanation beats, so they should not be reported
    assert not any("Number four" in p for p in problems)
    assert not any("Number one" in p for p in problems)


def test_cta_words_from_source_must_survive():
    script = make_script()
    source = "Comment below, then like the video and subscribe. Number five, mantis shrimp."
    problems, _ = check_script(script, source, DURATION)
    assert any("subscribe" in p and "like" in p for p in problems)
    script.beats[1] = script.beats[1].model_copy(update={"text": "Smash like, comment, and subscribe now!"})
    problems, _ = check_script(script, source, DURATION)
    assert not [p for p in problems if "subscribe" in p]


def test_bgm_must_exist_when_choices_known():
    script = make_script().model_copy(update={"bgm": "epic.mp3"})
    problems, _ = check_script(script, SOURCE_TEXT, DURATION, bgm_choices=["mystery.mp3"])
    assert any("epic.mp3" in p for p in problems)
    assert not [p for p in check_script(script, SOURCE_TEXT, DURATION, bgm_choices=["epic.mp3"])[0] if "bgm" in p.lower()]
    assert not [p for p in check_script(script, SOURCE_TEXT, DURATION)[0] if "bgm" in p.lower()]  # choices None = nggak dicek


def test_script_accepts_new_optional_fields():
    data = make_script().model_dump()
    data["beats"][0]["queries_zh"] = ["螳螂虾"]
    data["bgm"] = "mystery.mp3"
    data["hook_queries"] = {"0": {"en": ["bird on tower"], "zh": ["鸟 塔"]}}
    script = Script(**data)
    assert script.hook_queries["0"].zh == ["鸟 塔"] and script.beats[0].queries_zh == ["螳螂虾"]
    assert Script(**make_script().model_dump()).bgm == ""  # naskah lama tanpa field baru tetap kebaca


def test_normalize_script_keeps_bgm_and_hook_queries():
    script = Script(**{**make_script().model_dump(), "bgm": "epic.mp3", "hook_queries": {"0": {"en": ["x"], "zh": []}}})
    out = normalize_script(script)
    assert out.bgm == "epic.mp3" and out.hook_queries["0"].en == ["x"]
