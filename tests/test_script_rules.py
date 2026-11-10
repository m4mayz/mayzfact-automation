from mayzfact.models import Beat, Script
from mayzfact.steps.script import check_script, normalize_script
from tests.top3_fixtures import SOURCE_TEXT, top3_script


def test_old_script_with_fallback_query_still_loads_and_passes():
    raw = {**top3_script().model_dump(), "fallback_query": "animals"}  # naskah lama sebelum field ini dicabut
    script = Script.model_validate(raw)
    assert not hasattr(script, "fallback_query")
    assert check_script(script, SOURCE_TEXT)[0] == []


def test_script_without_fallback_query_is_valid():
    raw = top3_script().model_dump()
    raw.pop("fallback_query", None)
    assert check_script(Script.model_validate(raw), SOURCE_TEXT)[0] == []


def test_photo_share_outside_range_is_reported():
    script = top3_script()
    for beat in script.beats[1:]:
        beat.media = "photo"
    problems, _ = check_script(script, SOURCE_TEXT)
    assert any("photo" in p for p in problems)


def test_copied_phrases_are_reported():
    script = top3_script()
    script.beats[2].text = "Frozen winter Number four archerfish Water jets Number three basilisk lizards"
    script.beats[3].text = "jets Number three basilisk lizards They sprint over water Number two"
    script.beats[5].text = "They sprint over water Number two immortal jellyfish Their life cycle"
    problems, overlap = check_script(script, SOURCE_TEXT)
    assert overlap > 0.15
    assert any("copied" in p for p in problems)


def test_empty_queries_are_reported():
    script = top3_script()
    script = script.model_copy(
        update={
            "beats": [script.beats[0].model_copy(update={"queries": []}), *script.beats[1:]],
        }
    )
    problems, _ = check_script(script, SOURCE_TEXT)
    assert "Beat 1 has no search queries." in problems


def test_normalize_script_cleans_text_and_forces_first_video():
    raw = top3_script().model_copy(update={
        "beats": [
            Beat(text="It’s  here —now", media="photo", queries=[" crab ", " "]),
            Beat(text="Second", media="photo", queries=["fossil"]),
        ],
    })
    script = normalize_script(raw)
    assert script.beats[0].text == "It's here, now"
    assert script.beats[0].media == "video"
    assert script.beats[0].queries == ["crab"]
    assert script.beats[1].media == "photo"


def test_long_beat_is_reported():
    script = top3_script()
    long_beat = script.beats[1].model_copy(update={"text": " ".join(f"x{j}" for j in range(12)) + "."})
    script = script.model_copy(update={"beats": [script.beats[0], long_beat, *script.beats[2:]]})
    problems, _ = check_script(script, SOURCE_TEXT)
    assert any(p.startswith("Beat 2 has 12 words") for p in problems)


def test_normalize_script_keeps_subject_trimmed():
    raw = top3_script().model_copy(update={
        "beats": [Beat(text="Number five, horseshoe crab.", media="video", queries=["crab"], subject="  horseshoe crab ")],
    })
    assert normalize_script(raw).beats[0].subject == "horseshoe crab"
    assert Beat(text="x", media="video", queries=["q"]).subject == ""


def test_countdown_item_with_fewer_than_two_explanation_beats_is_reported():
    script = top3_script()
    del script.beats[6]
    problems, _ = check_script(script, SOURCE_TEXT)
    assert any("Number two" in p and "explanation beat" in p for p in problems)


def test_cta_words_from_source_must_survive():
    script = top3_script()
    script.beats[8].text = "or say 'nope'."
    source = SOURCE_TEXT + " Comment below, then like the video and subscribe."
    problems, _ = check_script(script, source)
    assert any("The source asks viewers to" in p and "comment" in p for p in problems)


def test_bgm_must_exist_when_choices_known():
    script = top3_script().model_copy(update={"bgm": "epic.mp3"})
    problems, _ = check_script(script, SOURCE_TEXT, bgm_choices=["mystery.mp3"])
    assert any("epic.mp3" in p for p in problems)
    assert not [p for p in check_script(script, SOURCE_TEXT, bgm_choices=["epic.mp3"])[0] if "bgm" in p.lower()]
    assert not [p for p in check_script(script, SOURCE_TEXT)[0] if "bgm" in p.lower()]  # choices None = nggak dicek


def test_script_accepts_new_optional_fields():
    data = top3_script().model_dump()
    data["beats"][0]["queries_zh"] = ["螳螂虾"]
    data["bgm"] = "mystery.mp3"
    data["hook_queries"] = {"0": {"en": ["bird on tower"], "zh": ["鸟 塔"]}}
    script = Script(**data)
    assert script.hook_queries["0"].zh == ["鸟 塔"] and script.beats[0].queries_zh == ["螳螂虾"]
    assert Script(**top3_script().model_dump()).bgm == ""


def test_normalize_script_keeps_bgm_and_hook_queries():
    script = Script(**{**top3_script().model_dump(), "bgm": "epic.mp3", "hook_queries": {"0": {"en": ["x"], "zh": []}}})
    out = normalize_script(script)
    assert out.bgm == "epic.mp3" and out.hook_queries["0"].en == ["x"]


def test_countdown_announcements_do_not_count_as_copied():
    _, overlap = check_script(top3_script(), SOURCE_TEXT)
    assert overlap == 0.0  # "Number N, subject" wajib sama persis, jadi nggak dihitung sebagai jiplakan
