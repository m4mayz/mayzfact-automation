"""Kontrak CTA dekoratif opt-in; seluruh alignment di sini fixture, bukan audio produksi."""
import pytest
from pydantic import ValidationError

from mayzfact.models import Script
from mayzfact.text import script_text, text_hash
from tests.top3_fixtures import playful_script

CONFIG = dict(theme='volcano', transform_word='volcano', comment_text='ERUPTED')


def scene_script():
    return {**playful_script().model_dump(), 'cta_scene': CONFIG.copy()}


def test_plan_marks_shared_cta_block_automatic_without_manual_references(tmp_path, cut_video):
    import shutil

    from mayzfact.narration import cta_beat_indices
    from mayzfact.steps.plan import run_plan
    from mayzfact.store import RunPaths
    from tests.factories import fake_alignment

    script = scene_script()
    source = dict(video_id='abcdefghijk', duration_s=2, transcript=[
        dict(text='Number three, basilisk lizards.', start=0, duration=.4),
        dict(text='Number two, immortal jellyfish.', start=.5, duration=.4),
        dict(text='Number one, tardigrades.', start=1.2, duration=.6)])
    plan = run_plan(RunPaths(tmp_path/'run'), script,
                    dict(duration_s=20, alignment=fake_alignment(script_text(script['beats']), 20)),
                    source, max_shot_s=2, hook_seconds=0,
                    download_source=lambda vid, dest: shutil.copyfile(cut_video, dest), log=lambda m: None)
    ctas = set(cta_beat_indices(script['beats']))
    auto = [s for s in plan['shots'] if s.get('auto_cta')]
    assert {s['beat'] for s in auto} == ctas
    assert all(s['group'] == 'auto-cta' and s['ref_frames'] == [] and not s['subject'] for s in auto)
    group = next(g for g in plan['groups'] if g['id'] == 'auto-cta')
    assert group['auto_cta'] is True
    assert plan['cta_scene'] == CONFIG
    assert all(len(s['ref_frames']) == 3 for s in plan['shots'] if not s.get('auto_cta'))


def auto_plan():
    from tests.test_fetch import shot
    return dict(cta_scene=CONFIG, groups=[dict(id='body', label='body', shots=[0]),
                dict(id='auto-cta', label='AUTO CTA', shots=[1, 2], auto_cta=True),
                dict(id='one', label='one', shots=[3])],
                shots=[shot(0, 0, .6, 'body'),
                       {**shot(1, .6, 1.1, 'auto-cta'), 'auto_cta': True},
                       {**shot(2, 1.1, 3.5, 'auto-cta'), 'auto_cta': True},
                       shot(3, 3.5, 4.1, 'one')])


def test_auto_cta_never_requires_links_or_reference_frames(tmp_path):
    from mayzfact.brief.server import missing_frames
    from mayzfact.manual.links import missing_groups, missing_shots
    from mayzfact.store import RunPaths
    plan = auto_plan()
    assert missing_shots(plan, {'shots': {'0': {'url': 'https://x/a'}}}) == [3]
    assert missing_shots(plan, {'shots': {'0': {}, '3': {}}}) == [0, 3]
    assert missing_groups(plan, {'groups': {'body': [{'url': 'https://x/a'}]}}) == ['one']
    assert missing_frames(RunPaths(tmp_path), plan) == [0, 3]


def test_brief_auto_row_has_no_input_or_upload_controls():
    from mayzfact.brief.page import render_page
    html = render_page('fixture', auto_plan(), {'shots': {}}, {})
    assert 'AUTO CTA' in html
    assert 'data-auto-cta="true"' in html
    for i in [1, 2]:
        assert f'data-shot="{i}"' not in html
        assert f'data-time-start="{i}"' not in html
        assert f'uploadShot({i},' not in html
    assert 'data-shot="0"' in html and 'data-shot="3"' in html
    assert '2/4 shot' in html


def test_brief_api_ignores_stale_auto_links_and_rejects_auto_upload(tmp_path):
    import threading

    import httpx

    from mayzfact.brief.server import make_server
    from mayzfact.store import RunPaths, read_json, write_json_atomic
    paths = RunPaths(tmp_path/'brief')
    write_json_atomic(paths.shots_plan_json, auto_plan())
    srv = make_server(paths, 0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{srv.server_address[1]}'
    try:
        response = httpx.post(base+'/api/links', json={'shots': {
            '0': 'https://x/a', '1': 'https://stale/cta', '3': 'https://x/b'}})
        assert response.json()['missing'] == []
        assert set(read_json(paths.links_json)['shots']) == {'0', '3'}
        assert httpx.post(base+'/api/upload?shot=1', content=b'no',
                          headers={'X-Filename': 'no.mp4'}).status_code == 400
        assert httpx.post(base+'/api/upload?group=auto-cta', content=b'no',
                          headers={'X-Filename': 'no.mp4'}).status_code == 400
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join()


def test_operator_review_uses_plan_completeness_for_auto_cta(tmp_path):
    import importlib.util
    from pathlib import Path

    from mayzfact.store import RunPaths, write_json_atomic
    file = Path('D:/akmal/_notes/tools/short_ops.py')
    if not file.exists():
        pytest.skip('helper lokal PC operator')
    spec = importlib.util.spec_from_file_location('short_ops', file)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    paths = RunPaths(tmp_path/'operator')
    write_json_atomic(paths.shots_plan_json, auto_plan())
    write_json_atomic(paths.links_json, {'shots': {'0': {'url': 'https://x/a'}, '1': {}, '2': {}}})
    assert mod.review_inputs(paths.root) == ([3], {'https://x/a'})


@pytest.mark.parametrize('mode', ['shots', 'groups'])
def test_fetch_reuses_only_pre_cta_video_with_deterministic_continuing_loop(tmp_path, cut_video, mode):
    from mayzfact.steps.fetch import run_fetch
    from mayzfact.store import RunPaths, read_json, write_json_atomic
    from tests.test_fetch import FakeEncoder
    paths = RunPaths(tmp_path/'fetch')
    plan = auto_plan()
    links = ({'shots': {'0': {'url': 'https://x/earlier', 'start_s': .4},
                        '3': {'url': 'https://x/future'}}} if mode == 'shots' else
             {'groups': {'body': [{'url': 'https://x/earlier', 'start_s': .4}],
                         'one': [{'url': 'https://x/future'}]}})
    write_json_atomic(paths.links_json, links)
    calls = []
    def obtain(e, root):
        calls.append(e['url'])
        return [cut_video]
    data = run_fetch(paths, plan, obtain=obtain, encoder=FakeEncoder(), fg_min_ratio=.5, log=lambda m: None)
    auto = [s for s in data['shots'] if s.get('auto_cta')]
    assert len(auto) == 2
    assert [s['index'] for s in data['shots']] == [0, 1, 2, 3]
    assert all(s['reused'] and s['reused_from'] == 0 and s['page_url'] == 'https://x/earlier' for s in auto)
    assert auto[1]['clipOffset'] == auto[0]['clipOffset'] + 15
    assert auto[1]['loopFrames'] > 0
    assert all(s['match'] is None for s in auto)
    assert len(calls) == 2
    assert data['shots'][0]['source_s'] == .4
    assert read_json(paths.links_status_json)['shots']['1']['state'] == 'auto'
    again = run_fetch(paths, plan, obtain=obtain, encoder=FakeEncoder(), fg_min_ratio=.5, log=lambda m: None)
    assert again == data


def test_fetch_auto_falls_back_without_video_and_never_requests_cta_links(tmp_path):
    from mayzfact.steps.fetch import run_fetch
    from mayzfact.store import RunPaths, write_json_atomic
    from tests.test_fetch import FakeEncoder, photos
    paths = RunPaths(tmp_path/'fallback')
    plan = auto_plan()
    write_json_atomic(paths.links_json, {'shots': {'0': {'url': 'https://x/photo'}, '3': {'url': 'https://x/one'}}})
    files = photos(tmp_path, 'a', 'b')
    data = run_fetch(paths, plan, obtain=lambda e, root: [files[0 if e['url'].endswith('photo') else 1]],
                     encoder=FakeEncoder(), fg_min_ratio=.5, log=lambda m: None)
    assert all(s.get('generated') for s in data['shots'][1:3])
    assert all(not s.get('page_url') for s in data['shots'][1:3])


def timeline_fixture(duration=20):
    from mayzfact.timing import beat_timings
    from tests.factories import fake_alignment
    script = scene_script()
    alignment = fake_alignment(script_text(script['beats']), duration)
    times = beat_timings([b['text'] for b in script['beats']], alignment, duration)
    clips = {'shots': [dict(file=f'clips/shot_{i}.mp4', kind='video', start_s=t['start_s'], end_s=t['end_s'],
                           width=1080, height=1920, beat=i) for i, t in enumerate(times)]}
    return script, alignment, clips


def test_scene_stages_cover_cta_follow_actual_words_and_end_before_one():
    from mayzfact.narration import cta_beat_indices
    from mayzfact.steps.timeline import build_timeline, to_frame
    from mayzfact.timing import word_timings
    script, alignment, clips = timeline_fixture()
    # Metadata salah dari klien lama nggak boleh bikin panah/emoji menutupi scene.
    marks = {'beats': [dict(point=True, emoji='x', emoji_word='') for b in script['beats']], 'emoji': {'x': 'x.json'}}
    detections = {s['file']: {'points': [dict(t=0, x=300, y=600, w=200, h=200)]} for s in clips['shots']}
    timeline = build_timeline(clips, 20, .5, script=script, alignment=alignment, marks=marks, overlays=detections)
    scene = timeline['ctaScene']
    words = word_timings(alignment)
    expected = {kind: to_frame(next(w for w in words if w['text'].lower().strip('.,?') == token)['start_s'])
                for kind, token in [('like', 'like'), ('transform', 'volcano'), ('subscribe', 'subscribe'), ('comment', 'comment')]}
    assert {c['kind']: c['from'] for c in scene['cues']} == expected
    assert [s['kind'] for s in scene['stages']] == ['like', 'transform', 'subscribe', 'comment']
    assert [s['from'] for s in scene['stages']][1:] == [expected[k] for k in ['transform', 'subscribe', 'comment']]
    assert scene['from'] == to_frame(clips['shots'][min(cta_beat_indices(script['beats']))]['start_s'])
    stop = scene['from'] + scene['durationInFrames']
    assert stop == timeline['countdown'][-1]['numberFrom']
    assert sum(s['durationInFrames'] for s in scene['stages']) == stop - scene['stages'][0]['from']
    assert timeline['cta'] == []
    for key in ['emojis', 'overlays']:
        assert all(x['from'] + x['durationInFrames'] <= scene['from'] or x['from'] >= stop for x in timeline[key])
    assert any(c['text'] == 'VOLCANO' for c in timeline['captions'])
    assert any(c['text'] == 'COMMENT' for c in timeline['captions'])


def test_like_appears_only_when_try_tapping_is_spoken_not_during_leadin():
    from mayzfact.steps.timeline import build_timeline, to_frame
    from mayzfact.timing import word_timings
    script, alignment, clips = timeline_fixture()
    timeline = build_timeline(clips, 20, .5, script=script, alignment=alignment)
    scene = timeline['ctaScene']
    words = word_timings(alignment)
    invitation = to_frame(next(w for w in words if w['text'].lower().strip('.,?') == 'try')['start_s'])
    click = to_frame(next(w for w in words if w['text'].lower().strip('.,?') == 'like')['start_s'])
    stage = next(s for s in scene['stages'] if s['kind'] == 'like')
    assert stage['from'] == invitation
    assert stage['from'] > scene['from']
    assert stage['triggerAt'] == click - invitation
    assert all(s['from'] >= invitation for s in scene['stages'])


def test_scene_without_word_events_uses_structural_bounds_not_fake_spoken_cues():
    from mayzfact.steps.timeline import build_timeline
    script, _, clips = timeline_fixture()
    timeline = build_timeline(clips, 20, .5, script=script)
    scene = timeline['ctaScene']
    assert scene['cues'] == []
    assert [s['kind'] for s in scene['stages']] == ['like', 'transform', 'subscribe', 'comment']
    assert all(s['timing'] == 'structure' for s in scene['stages'])
    assert scene['from'] + scene['durationInFrames'] <= round(clips['shots'][11]['start_s'] * 30)


def test_scene_absence_keeps_legacy_top3_and_source_timeline_unchanged():
    from mayzfact.steps.timeline import build_timeline
    script, alignment, clips = timeline_fixture()
    script.pop('cta_scene')
    top3 = build_timeline(clips, 20, .5, script=script, alignment=alignment)
    assert 'ctaScene' not in top3 and len(top3['cta']) == 2
    script.pop('narration_mode')
    source = build_timeline(clips, 20, .5, script=script, alignment=alignment)
    assert 'ctaScene' not in source


def test_scene_reuse_entries_retain_loop_and_offset_metadata():
    from mayzfact.steps.timeline import build_timeline
    script, alignment, clips = timeline_fixture()
    clips['shots'][7].update(auto_cta=True, reused=True, clipOffset=19, loopFrames=27)
    clips['shots'][8].update(auto_cta=True, generated=True, clipOffset=23)
    data = build_timeline(clips, 20, .5, script=script, alignment=alignment)
    assert data['shots'][7]['clipOffset'] == 19
    assert data['shots'][7]['loopFrames'] == 27
    assert data['shots'][7]['decorative'] is True
    assert data['shots'][8]['generated'] is True


def test_decorative_auto_background_skips_subject_and_text_detection(tmp_path, cut_video):
    from mayzfact.overlay import prepare_overlays
    from mayzfact.store import RunPaths
    from mayzfact.textblur import prepare_text_blurs
    paths = RunPaths(tmp_path/'detectors')
    paths.root.mkdir(parents=True)
    clip = dict(auto_cta=True, index=1, beat=7, kind='video', file=str(cut_video),
                start_s=1, end_s=4, width=320, height=240)
    class NoDetector:
        def boxes(self, image):
            pytest.fail('CTA dekoratif tidak butuh OCR baru')
        def best_box(self, image, query):
            pytest.fail('CTA dekoratif tidak butuh subject detection')
    assert prepare_text_blurs(paths, {'shots': [clip]}, NoDetector(), log=lambda m: None) == {}
    assert prepare_overlays(paths, {'shots': [clip]}, scene_script(), None, NoDetector(),
                            fg_min_ratio=.5, log=lambda m: None) == {}


def test_prefetch_initial_urls_exclude_stale_auto_cta_inputs():
    from mayzfact.brief.server import link_urls
    assert link_urls({'shots': {'0': {'url': 'https://x/a'}, '1': {'url': 'https://stale/cta'}}}, auto_plan()) == ['https://x/a']
    assert link_urls({'groups': {'body': [{'url': 'https://x/a'}],
                                 'auto-cta': [{'url': 'https://stale/cta'}]}}, auto_plan()) == ['https://x/a']


def test_cta_visual_markup_cases_run_in_node():
    import shutil
    import subprocess
    from pathlib import Path
    node = shutil.which('node')
    if not node:
        pytest.skip('Node dibutuhkan untuk tes komponen Remotion')
        return
    root = Path(__file__).resolve().parents[1]/'remotion'
    result = subprocess.run([node, 'tests/cta-scene.cjs'], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '11 CTA visual cases passed' in result.stdout


def test_operator_summary_exempts_explicit_reuse_from_overlap_warnings(tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path

    from mayzfact.store import write_json_atomic
    file = Path('D:/akmal/_notes/tools/short_ops.py')
    if not file.exists():
        pytest.skip('helper lokal PC operator')
    spec = importlib.util.spec_from_file_location('short_ops_summary', file)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, 'REPO', tmp_path)
    run = tmp_path/'runs'/'fixture'
    write_json_atomic(run/'timeline.json', dict(durationInFrames=120, shots=[], cta=[],
        ctaScene=dict(stages=[dict(kind='transform', **{'from': 45})])))
    write_json_atomic(run/'clips.json', {'shots': [
        dict(index=0, kind='video', page_url='same', source_s=0, start_s=0, end_s=1, match=.5),
        dict(index=1, kind='video', page_url='same', source_s=0, start_s=1, end_s=2, match=None, reused=True)]})
    (tmp_path/'mayzfact'/'steps').mkdir(parents=True)
    (tmp_path/'mayzfact'/'steps'/'fetch.py').write_text('TAIL_S = 0.2')
    lines = mod.summary('fixture')
    assert any('klip numpuk' in line and 'tidak ada' in line for line in lines)
    assert any('scene CTA' in line and 'transform' in line for line in lines)


def test_missing_transform_word_event_uses_beat_start_without_invented_cue():
    from mayzfact.cta_scene import build_scene
    from mayzfact.steps.timeline import _beat_of, _shot_entries
    from mayzfact.timing import word_timings
    script, alignment, clips = timeline_fixture()
    words = word_timings(alignment)
    beat_of = _beat_of(words, script['beats'])
    pairs = [(w, b) for w, b in zip(words, beat_of) if 'volcano' not in w['text'].lower()]
    scene = build_scene(script, clips['shots'], _shot_entries(clips['shots'], 600, .5),
                        [w for w, _ in pairs], [b for _, b in pairs], [], 600)
    assert scene is not None
    stage = next(s for s in scene['stages'] if s['kind'] == 'transform')
    assert stage['timing'] == 'structure'
    assert 'triggerAt' not in stage
    assert 'transform' not in {c['kind'] for c in scene['cues']}


def test_unicorn_theme_schema_needs_no_label_and_preserves_voice_hash():
    raw = scene_script()
    raw['cta_scene'] = dict(theme='unicorn', transform_word='turn', comment_text='MAGIC')
    parsed = Script.model_validate(raw)
    assert parsed.cta_scene is not None
    assert parsed.cta_scene.theme == 'unicorn'
    assert parsed.cta_scene.transform_word == 'turn'
    assert text_hash(script_text(parsed.model_dump()['beats'])) == text_hash(script_text(raw['beats']))
    with pytest.raises(ValidationError):
        Script.model_validate({**raw, 'cta_scene': {**raw['cta_scene'], 'sparkle_speed': 2}})


def test_scene_metadata_survives_schema_without_changing_voice_hash():
    raw = scene_script()
    parsed = Script.model_validate(raw).model_dump()
    assert parsed['cta_scene']['transform_word'] == 'volcano'
    assert text_hash(script_text(parsed['beats'])) == text_hash(script_text(raw['beats']))
    for bad in [{**CONFIG, 'typo': True}, {**CONFIG, 'theme': 'unknown'},
                {**CONFIG, 'transform_word': ''}, {**CONFIG, 'theme': 'word'}]:
        with pytest.raises(ValidationError):
            Script.model_validate({**raw, 'cta_scene': bad})
    with pytest.raises(ValidationError):
        Script.model_validate({**raw, 'narration_mode': 'source'})
