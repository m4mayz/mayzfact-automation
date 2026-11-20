import json
from typing import get_args

import httpx
import pytest
from pydantic import ValidationError

from mayzfact.config import Settings
from mayzfact.errors import PipelineError
from mayzfact.faktacuil import LEGACY_CTA_FORMATS, THEME_NOUNS_ID
from mayzfact.models import CtaQuiz, FaktaCuilCtaScene, FaktaCuilTheme, Script
from mayzfact.pipeline import Deps, run_pipeline
from mayzfact.steps.script import check_script, load_script
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import script_text, text_hash
from tests.factories import fake_alignment
from tests.faktacuil_fixtures import SOURCE_TEXT_EN, faktacuil_script
from tests.top3_fixtures import top3_script


@pytest.mark.parametrize("cta", ["none", "lucky", "subscribe", "emoji", "quiz", "lucky+quiz", "subscribe+quiz"])
def test_every_valid_combo_passes(cta):
    assert check_script(faktacuil_script(cta=cta), SOURCE_TEXT_EN)[0] == []


def test_schema_shapes():
    FaktaCuilCtaScene(format="emoji", emoji="📦")
    FaktaCuilCtaScene(format="lucky", theme="honey")
    for bad in [dict(format="emoji", emoji="box"), dict(format="emoji", emoji=""),
                dict(format="emoji", emoji="📦", theme="honey"), dict(format="lucky"),
                dict(format="lucky", theme="honey", emoji="📦"), dict(format="lucky", theme="honey", transform_word="x"),
                dict(format="question", theme="honey")]:
        with pytest.raises(ValidationError):
            FaktaCuilCtaScene(**bad)
    with pytest.raises(ValidationError):
        CtaQuiz(word="kardus", answer="2")


def test_faktacuil_scene_error_names_the_emoji_reason():
    raw = faktacuil_script().model_dump()
    with pytest.raises(ValidationError) as err:
        Script(**{**raw, "cta_scene": {"format": "emoji", "emoji": "box"}})
    msg = str(err.value)
    assert "emoji" in msg and "theme" not in msg


def test_faktacuil_scene_error_names_the_theme_reason():
    raw = faktacuil_script().model_dump()
    with pytest.raises(ValidationError) as err:
        Script(**{**raw, "cta_scene": {"format": "lucky"}})
    assert "theme" in str(err.value)


def test_top3_scene_error_names_the_top3_reason():
    raw = top3_script().model_dump()
    with pytest.raises(ValidationError) as err:
        Script(**{**raw, "cta_scene": {"theme": "honey"}})
    msg = str(err.value)
    assert "transform_word" in msg and "FaktaCuil" not in msg


def test_empty_queries_gets_only_one_message():
    data = faktacuil_script().model_dump()
    data["beats"][2]["queries"] = []
    problems = check_script(Script(**data), SOURCE_TEXT_EN)[0]
    assert sum("search queries" in p for p in problems) == 1


def test_load_script_reports_original_faktacuil_scene_reason(tmp_path):
    paths = RunPaths(tmp_path)
    write_json_atomic(paths.script_json, {**faktacuil_script().model_dump(),
                                          "cta_scene": {"format": "emoji", "emoji": "box"}})
    with pytest.raises(PipelineError) as err:
        load_script(paths)
    assert "emoji CTA needs one emoji character" in str(err.value)


def test_top3_still_requires_its_own_cta_scene():
    raw = top3_script().model_dump()
    for scene in [None, {"format": "lucky", "theme": "honey"}]:
        with pytest.raises(ValidationError):
            Script(**{**raw, "cta_scene": scene})
    with pytest.raises(ValidationError):
        Script(**{**raw, "cta_quiz": {"word": "water", "answer": 2}})


def test_theme_nouns_cover_every_sticker_theme():
    assert set(THEME_NOUNS_ID) == set(get_args(FaktaCuilTheme))


def test_faktacuil_without_cta_loads(tmp_path):
    paths = RunPaths(tmp_path)
    write_json_atomic(paths.script_json, faktacuil_script(cta="none").model_dump())
    assert load_script(paths).cta_scene is None


@pytest.mark.parametrize("scene", [
    {"theme": "honey", "transform_word": "berubah", "comment_text": "MADU"},
    *({"theme": "honey", "transform_word": "muncul", "comment_text": "MADU", "format": f} for f in LEGACY_CTA_FORMATS)])
def test_legacy_faktacuil_format_is_rejected_with_clear_message(tmp_path, scene):
    paths = RunPaths(tmp_path)
    raw = {**faktacuil_script().model_dump(), "cta_scene": scene}
    write_json_atomic(paths.script_json, raw)
    with pytest.raises(PipelineError) as err:
        load_script(paths)
    msg = str(err.value)
    assert scene.get("format", "question") in msg and "CTA v2" in msg and "lucky" in msg and "dibiarin" in msg
    assert json.loads(paths.script_json.read_text(encoding="utf-8")) == raw


def test_legacy_faktacuil_run_is_rejected_before_outputs_are_deleted(tmp_path):
    paths = RunPaths(tmp_path / "abcdefghijk")
    raw = {**faktacuil_script().model_dump(),
           "cta_scene": {"theme": "honey", "transform_word": "muncul", "comment_text": "MADU", "format": "escape"}}
    write_json_atomic(paths.script_json, raw)
    write_json_atomic(paths.source_json, dict(duration_s=90, transcript=[dict(text=SOURCE_TEXT_EN)]))
    text = script_text(raw["beats"])
    write_json_atomic(paths.tts_json, dict(duration_s=25, text_sha256=text_hash(text), alignment=fake_alignment(text, 25)))
    paths.voice_mp3.write_bytes(b"paid-audio")
    write_json_atomic(paths.shots_plan_json, dict(shots=[]))
    write_json_atomic(paths.clips_json, dict(shots=[]))
    write_json_atomic(paths.timeline_json, dict(shots=[]))
    paths.final_mp4.write_bytes(b"existing-video")
    before = {p.name: p.read_bytes() for p in paths.root.iterdir()}

    def forbidden(*a, **kw):
        pytest.fail("run lama harus berhenti sebelum dependency jalan")

    deps = Deps(fetch_transcript=forbidden, tts=forbidden, http=httpx.Client, render=forbidden,
                plan=forbidden, fetch=forbidden)
    with pytest.raises(PipelineError, match="CTA v2"):
        run_pipeline("abcdefghijk", settings=Settings(), from_step="timeline", no_render=True,
                     deps=deps, runs_dir=tmp_path)
    assert before == {p.name: p.read_bytes() for p in paths.root.iterdir()}
    assert json.loads(paths.script_json.read_text(encoding="utf-8")) == raw


@pytest.mark.parametrize("cta,mutate,needle", [
    ("lucky", lambda d: d["beats"][5].update(text="jika beruntung bisa muncul singa."), "name the sticker object"),
    ("lucky", lambda d: d["beats"][5].update(text="jika beruntung bisa dapat madu."), "must say 'muncul'"),
    ("lucky", lambda d: d["beats"][5].update(text="muncul madu, subscribe ya."), "must invite exactly one like"),
    ("subscribe", lambda d: d["beats"][5].update(text="nanti muncul madu kalau berhasil."), "must ask to subscribe"),
    ("emoji", lambda d: d["beats"][-1].update(text="Tapi mengapa ada emoji madu saat tekan like."), "must say 'emoji'"),
    ("emoji", lambda d: d.update(cta_quiz={"word": "kardus", "answer": 2}), "cannot be combined"),
    ("none", lambda d: d.update(cta_scene={"format": "lucky", "theme": "honey"}), "no CTA beat"),
    ("lucky", lambda d: d.update(cta_scene=None), "no cta_scene"),
    ("quiz", lambda d: d.update(cta_quiz=None), "cta_quiz and the quiz beat"),
    ("quiz", lambda d: d["cta_quiz"].update(answer=3), "Set answer to 2"),
    ("quiz", lambda d: d["beats"][2].update(text=d["beats"][2]["text"].replace("kardus", "kotak")), "at least twice"),
    ("quiz", lambda d: d["beats"].append({**d["beats"][-2]}), "last beat"),
    ("lucky+quiz", lambda d: d["beats"].__delitem__(slice(7, 9)), "two answer beats"),
    ("lucky", lambda d: d["beats"][2].update(queries=["猫 纸箱", "cat box"]), "ASCII only"),
    ("lucky", lambda d: d["beats"][2].update(queries=["cat box"]), "at least 2 search queries"),
])
def test_faktacuil_rule_violations(cta, mutate, needle):
    data = faktacuil_script(cta=cta).model_dump()
    mutate(data)
    assert any(needle in p for p in check_script(Script(**data), SOURCE_TEXT_EN)[0])


@pytest.mark.parametrize("cta", ["emoji", "quiz", "none"])
def test_end_cta_and_no_cta_skip_structure_rules(cta):
    data = faktacuil_script(cta=cta).model_dump()
    data["beats"].pop(2)  # buang beat salah kaprah
    problems = check_script(Script(**data), SOURCE_TEXT_EN)[0]
    assert not any("misconception" in p or "two answer beats" in p for p in problems)


def test_queries_zh_is_ignored_for_faktacuil():
    data = faktacuil_script().model_dump()
    for beat in data["beats"]:
        beat["queries_zh"] = ["猫"]
    assert check_script(Script(**data), SOURCE_TEXT_EN)[0] == []


def test_like_in_quiz_beat_is_allowed():
    data = faktacuil_script(cta="quiz").model_dump()
    data["beats"][-1]["text"] = "Nah coba tebak berapa kali aku bilang kardus, like?"
    assert check_script(Script(**data), SOURCE_TEXT_EN)[0] == []


def test_subscribe_must_come_after_the_like_invite():
    data = faktacuil_script(cta="subscribe").model_dump()
    data["beats"][4]["text"] = "Tapi subscribe dulu, coba tekan like,"
    problems = check_script(Script(**data), SOURCE_TEXT_EN)[0]
    assert any("must ask to subscribe after the like invite" in p for p in problems)
