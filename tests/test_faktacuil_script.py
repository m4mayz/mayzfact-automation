import pytest

from mayzfact.errors import PipelineError
from mayzfact.faktacuil import faktacuil_word_range
from mayzfact.models import Beat, Script
from mayzfact.steps.script import check_script, load_script
from mayzfact.store import RunPaths, write_json_atomic
from tests.faktacuil_fixtures import SOURCE_TEXT_EN, faktacuil_script
from tests.top3_fixtures import SOURCE_TEXT, top3_script


def test_faktacuil_mode_loads(tmp_path):
    paths = RunPaths(tmp_path)
    write_json_atomic(paths.script_json, faktacuil_script().model_dump())
    assert load_script(paths).narration_mode == "faktacuil"


def test_unknown_mode_still_rejected_with_both_modes_named(tmp_path):
    paths = RunPaths(tmp_path)
    write_json_atomic(paths.script_json, {**top3_script().model_dump(), "narration_mode": "source"})
    with pytest.raises(PipelineError) as exc:
        load_script(paths)
    assert "narration_mode" in exc.value.message and '"top3"' in exc.value.message and '"faktacuil"' in exc.value.message


def test_keyword_defaults_empty():
    assert Beat(text="a", media="video", queries=["q"]).keyword == ""


def test_fixture_has_expected_shape():
    script = faktacuil_script()
    assert len(script.beats) == 9
    assert sum(len(b.text.split()) for b in script.beats) == 69
    assert [b.keyword for b in script.beats if b.keyword] == ["kardus", "kucing"]


def test_valid_faktacuil_script_passes():
    assert check_script(faktacuil_script(), SOURCE_TEXT_EN)[0] == []


def test_word_range_at_default_speed():
    assert faktacuil_word_range(1.1) == (69, 55, 82)


@pytest.mark.parametrize("mutate,needle", [
    (lambda b: b[0].update(text="Kucing suka masuk kardus,"), 'open with "Kenapa"'),
    (lambda b: b[4].update(text="Tapi coba tekan like dan subscribe,"), "must not ask to subscribe"),
    (lambda b: b[5].update(text="apakah like-mu berubah jadi singa?"), "does not match the narrated transformation"),
    (lambda b: b[2].update(point=True), "point=false"),
    (lambda b: b[3].update(emoji="😱", emoji_word="keras"), "empty emoji fields"),
    (lambda b: b[2].update(keyword="gajah"), "keyword"),
    (lambda b: b[1].update(text="Number one, kardus."), '"Number N," countdown'),
])
def test_faktacuil_rules(mutate, needle):
    data = faktacuil_script().model_dump()
    mutate(data["beats"])
    assert any(needle in p for p in check_script(Script(**data), SOURCE_TEXT_EN)[0])


def test_cta_needs_misconception_before_and_two_answer_beats_after():
    data = faktacuil_script().model_dump()
    data["beats"] = data["beats"][:2] + data["beats"][4:7]  # buang salah kaprah + 1 jawaban
    problems = check_script(Script(**data), SOURCE_TEXT_EN)[0]
    assert any("misconception" in p for p in problems) and any("two answer beats" in p for p in problems)


def test_transform_word_in_hook_is_not_cta():
    data = faktacuil_script().model_dump()
    data["beats"][0]["text"] = "Kenapa warna kucing bisa berubah,"
    assert check_script(Script(**data), SOURCE_TEXT_EN)[0] == []


def test_word_count_outside_range_reports_bounds(monkeypatch):
    monkeypatch.setattr("mayzfact.faktacuil.FAKTACUIL_RAW_WPS", 2.0)  # rentang jadi 44-66, fixture 69 kata
    assert any("between 44 and 66" in p for p in check_script(faktacuil_script(), SOURCE_TEXT_EN)[0])


def test_hyphenated_keyword_allowed():
    data = faktacuil_script().model_dump()
    data["beats"][6]["text"] = "Ternyata kardus mirip sarang kupu-kupu,"
    data["beats"][6]["keyword"] = "kupu-kupu"
    assert not any("keyword" in p for p in check_script(Script(**data), SOURCE_TEXT_EN)[0])


def test_top3_rejects_keyword():
    s = top3_script()
    s.beats[2].keyword = "water"
    assert "Top 3 beats must not set keyword." in check_script(s, SOURCE_TEXT)[0]


@pytest.mark.parametrize("mutate,needle", [
    (lambda b: b[5].update(text="apakah like-mu berubah jadi madu."), "does not match the narrated transformation"),
    (lambda b: b[4].update(subject="cat"), "CTA beat 5 must have an empty subject"),
    (lambda b: b[5].update(keyword="madu"), "Beat 6 keyword"),
    (lambda b: b[1].update(text="masuk ke kardus yang sempit,"), 'open with "Kenapa"'),
])
def test_faktacuil_rules_edge_cases(mutate, needle):
    data = faktacuil_script().model_dump()
    mutate(data["beats"])
    assert any(needle in p for p in check_script(Script(**data), SOURCE_TEXT_EN)[0])


def test_approved_word_count_overrides_faktacuil_range():
    data = faktacuil_script().model_dump()
    data["approved_word_count"] = 50
    assert any("between 50 and 50" in p for p in check_script(Script(**data), SOURCE_TEXT_EN)[0])


def test_word_range_ignores_float_noise():
    assert faktacuil_word_range(0.56) == (35, 28, 42)  # 20 * 1.4 = 28.000000000000004
