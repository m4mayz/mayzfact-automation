import pytest

from mayzfact.errors import PipelineError
from mayzfact.models import Beat
from mayzfact.steps.script import load_script
from mayzfact.store import RunPaths, write_json_atomic
from tests.faktacuil_fixtures import faktacuil_script
from tests.top3_fixtures import top3_script


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
