import json

import httpx
import pytest
from pydantic import ValidationError

from mayzfact.config import Settings
from mayzfact.errors import PipelineError
from mayzfact.models import CtaScene, Script
from mayzfact.pipeline import Deps, run_pipeline
from mayzfact.steps.script import load_script
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import script_text, text_hash
from tests.factories import fake_alignment
from tests.top3_fixtures import SOURCE_TEXT, top3_script


def write_script(paths, **changes):
    raw = {**top3_script().model_dump(), **changes}
    for key, value in changes.items():
        if value is None:
            raw.pop(key)
    write_json_atomic(paths.script_json, raw)
    return raw


@pytest.mark.parametrize('mode', [None, 'source'])
def test_old_format_is_rejected_with_clear_message(tmp_path, mode):
    paths = RunPaths(tmp_path)
    write_script(paths, narration_mode=mode, cta_scene=None)
    with pytest.raises(PipelineError) as err:
        load_script(paths)
    message = str(err.value)
    for part in ['format lama', 'narration_mode', '"top3"', 'D-050', 'run baru']:
        assert part in message, message


def test_top3_without_scene_is_rejected_with_clear_message(tmp_path):
    paths = RunPaths(tmp_path)
    write_script(paths, cta_scene=None)
    with pytest.raises(PipelineError, match='cta_scene') as err:
        load_script(paths)
    assert 'D-050' in str(err.value)


def test_word_theme_and_label_are_gone():
    base = dict(transform_word='turn', comment_text='HONEY')
    with pytest.raises(ValidationError):
        CtaScene(theme='word', label='HONEY', **base)
    with pytest.raises(ValidationError):
        CtaScene(theme='honey', label='', **base)
    with pytest.raises(ValidationError):
        Script(beats=[], cta_scene=CtaScene(theme='honey', **base))  # narration_mode wajib


def test_old_run_with_paid_voice_is_rejected_before_outputs_are_deleted(tmp_path):
    paths = RunPaths(tmp_path/'abcdefghijk')
    raw = write_script(paths, narration_mode=None, cta_scene=None)
    write_json_atomic(paths.source_json, dict(duration_s=90, transcript=[dict(text=SOURCE_TEXT)]))
    text = script_text(raw['beats'])
    write_json_atomic(paths.tts_json, dict(duration_s=38.5, text_sha256=text_hash(text),
                                          alignment=fake_alignment(text, 38.5)))
    paths.voice_mp3.write_bytes(b'paid-audio')
    paths.final_mp4.write_bytes(b'existing-video')
    write_json_atomic(paths.shots_plan_json, dict(shots=[]))
    before = {p.name: p.read_bytes() for p in paths.root.iterdir()}

    def forbidden(*a, **kw):
        pytest.fail('run lama harus berhenti sebelum dependency jalan')
    deps = Deps(fetch_transcript=forbidden, tts=forbidden, http=httpx.Client, render=forbidden,
                plan=forbidden, fetch=forbidden)
    with pytest.raises(PipelineError, match='format lama'):
        run_pipeline('abcdefghijk', settings=Settings(), from_step='plan', no_render=True, deps=deps,
                     runs_dir=tmp_path)
    assert before == {p.name: p.read_bytes() for p in paths.root.iterdir()}
    assert json.loads(paths.script_json.read_text()) == raw
