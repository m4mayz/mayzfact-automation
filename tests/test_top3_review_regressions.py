"""Regresi temuan final review; semua input/alignments adalah fixture lokal."""
import pytest

from mayzfact.steps.script import check_script
from tests.top3_fixtures import SOURCE_TEXT, top3_script


@pytest.mark.parametrize('delimiter', ['. ', ' - ', ' – ', ' — '])
def test_source_heading_delimiters_match_shared_countdown_grammar(delimiter):
    source = SOURCE_TEXT.replace(', ', delimiter)
    assert check_script(top3_script(), source, 90)[0] == []


@pytest.mark.parametrize('layout', ['same_beat', 'split_beats'])
def test_cta_token_boundaries_match_validation_and_timeline(layout):
    from mayzfact.steps.timeline import _beat_of, _top3_cta, build_timeline
    from mayzfact.text import script_text
    from mayzfact.timing import beat_timings, word_timings
    from tests.factories import fake_alignment

    s = top3_script()
    s.beats[6].text = s.beats[6].text.rstrip(',.')
    if layout == 'same_beat':
        s.beats[7].text = "Like if you'd watch, turns into a volcano, subscribe,"
        expected = ['like', 'subscribe']
    else:
        s.beats[7].text = "Subscribe, it turns into a volcano, see for yourself"
        s.beats[8].text = "Like if you'd watch, or comment 'nope' if you'd run."
        expected = ['subscribe', 'like']
    assert check_script(s, SOURCE_TEXT, 90)[0] == []
    script = s.model_dump()
    alignment = fake_alignment(script_text(script['beats']),38.5)
    times = beat_timings([b['text'] for b in script['beats']],alignment,38.5)
    clips = {'shots':[dict(file=f'clips/{i}.mp4',kind='video',start_s=t['start_s'],width=1080,height=1920,beat=i)
                      for i,t in enumerate(times)]}
    t = build_timeline(clips,38.5,.5,script=script,alignment=alignment)
    words = word_timings(alignment)
    beat_of = _beat_of(words, script['beats'])
    cta = _top3_cta(words, beat_of, script['beats'], t['countdown'], t['durationInFrames'])
    assert [c['kind'] for c in cta] == expected


def test_top3_body_frames_are_pinned_to_original_rank_not_visual_subject(tmp_path, monkeypatch):
    import mayzfact.steps.plan as plan
    from mayzfact.store import RunPaths
    from mayzfact.text import script_text
    from tests.factories import fake_alignment

    script = top3_script().model_dump()
    source = dict(video_id='abcdefghijk',duration_s=110,transcript=[
        dict(text='Number five, wood frogs.',start=0,duration=10),
        dict(text='Number four, archerfish.',start=20,duration=10),
        dict(text='Number three, basilisk lizards.',start=40,duration=10),
        dict(text='Number two, immortal jellyfish.',start=60,duration=10),
        dict(text='Number one, tardigrades.',start=80,duration=10)])
    paths = RunPaths(tmp_path/'run')
    paths.root.mkdir()
    paths.source_mp4.write_bytes(b'test-placeholder-probe-is-stubbed')
    sampled={}
    def extract(src, time, dest):
        sampled.setdefault(dest.name,[]).append(time)
        return dest
    monkeypatch.setattr(plan,'extract_frame',extract)
    monkeypatch.setattr(plan,'probe',lambda *a:dict(duration_s=110))
    tts=dict(duration_s=38.5,alignment=fake_alignment(script_text(script['beats']),38.5))
    data=plan.run_plan(paths,script,tts,source,max_shot_s=4,hook_seconds=0,
                       download_source=lambda *a:pytest.fail('unexpected download'),log=lambda m:None)
    bounds={1:(40,60),2:(40,60),3:(40,60),4:(60,80),5:(60,80),6:(60,80),
            9:(80,110),10:(80,110),11:(80,110)}
    for shot in data['shots']:
        if shot['beat'] in bounds:
            low,high=bounds[shot['beat']]
            for ref in shot['ref_frames']:
                assert all(low <= t < high for t in sampled[ref.split('/')[-1]])


@pytest.mark.parametrize('mode', ['Top3', '', None])
def test_paid_voice_resume_rejects_unknown_mode_without_applying_word_budget(tmp_path, mode):
    from mayzfact.errors import PipelineError
    from mayzfact.pipeline import check_voice
    from mayzfact.store import RunPaths, write_json_atomic
    from tests.test_pipeline import write_voice_state

    paths=RunPaths(tmp_path)
    write_voice_state(paths,['Short text.'],38.5)
    import json
    script=json.loads(paths.script_json.read_text())
    script['narration_mode']=mode
    write_json_atomic(paths.script_json,script)
    with pytest.raises(PipelineError,match='narration_mode'):
        check_voice(paths,log=lambda m:None)
    script['narration_mode']='top3'
    write_json_atomic(paths.script_json,script)
    # Resume yang valid tidak membayar ulang atau menerapkan rentang kata pada audio terkunci.
    assert check_voice(paths,log=lambda m:None)['duration_s']==38.5


def test_invalid_mode_is_checked_before_deleting_resume_outputs(tmp_path):
    import httpx

    from mayzfact.config import Settings
    from mayzfact.errors import PipelineError
    from mayzfact.pipeline import Deps, run_pipeline
    from mayzfact.store import RunPaths, write_json_atomic
    from mayzfact.text import script_text, text_hash
    from tests.factories import fake_alignment

    paths=RunPaths(tmp_path/'abcdefghijk')
    script=top3_script().model_dump()
    script['narration_mode']='Top3'
    write_json_atomic(paths.script_json,script)
    write_json_atomic(paths.source_json,dict(duration_s=90,transcript=[dict(text=SOURCE_TEXT)]))
    write_json_atomic(paths.tts_json,dict(duration_s=38.5,text_sha256=text_hash(script_text(script['beats'])),
                                        alignment=fake_alignment(script_text(script['beats']),38.5)))
    paths.voice_mp3.write_bytes(b'paid-audio')
    paths.final_mp4.write_bytes(b'existing-video')
    write_json_atomic(paths.shots_plan_json,dict(shots=[]))
    before={p.name:p.read_bytes() for p in paths.root.iterdir()}
    def forbidden(*a,**kw):
        pytest.fail('resume should stop before dependencies run')
    deps=Deps(fetch_transcript=forbidden,tts=forbidden,http=httpx.Client,render=forbidden,plan=forbidden,fetch=forbidden)
    with pytest.raises(PipelineError,match='narration_mode'):
        run_pipeline('abcdefghijk',settings=Settings(),from_step='plan',no_render=True,deps=deps,runs_dir=tmp_path)
    assert before=={p.name:p.read_bytes() for p in paths.root.iterdir()}
