from mayzfact.models import Beat, Script
from mayzfact.steps.script import (
    build_user_prompt,
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


def test_user_prompt_has_targets_transcript_and_feedback():
    prompt = build_user_prompt(SOURCE, DURATION, 0.3)
    assert "about 110 words in total (allowed: 94-126)" in prompt
    assert "[2.5s] to this video" in prompt
    assert "30%" in prompt
    assert "rejected" not in prompt
    retry = build_user_prompt(SOURCE, DURATION, 0.3, feedback=["Too short."], previous=make_script(n_beats=1))
    assert "Your previous answer was rejected:" in retry
    assert "- Too short." in retry
    assert '"fallback_query":"ocean animals"' in retry


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
