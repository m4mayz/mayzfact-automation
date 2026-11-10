import shutil

import pytest

from mayzfact.steps.plan import run_plan
from mayzfact.store import RunPaths
from mayzfact.text import script_text
from tests.factories import fake_alignment
from tests.top3_fixtures import playful_script, top3_script


@pytest.mark.parametrize('make_script,ctas', [(top3_script, [7, 8]), (playful_script, [7, 8, 9, 10])])
def test_top3_short_hook_never_steals_countdown_or_body_keywords(tmp_path, cut_video, make_script, ctas):
    script = make_script().model_dump()
    script['hook_queries'] = {'0': dict(en=['opening only'], zh=['开场'])}
    # Mawar fixture source video cuma 2 detik; semua referensi tetap frame lokal nyata.
    source = dict(video_id='abcdefghijk',duration_s=2,transcript=[dict(text='intro',start=0,duration=.2),
                  dict(text='Number three, basilisk lizards.',start=.2,duration=.4),
                  dict(text='Number two, immortal jellyfish.',start=.7,duration=.4),
                  dict(text='Number one, tardigrades.',start=1.3,duration=.4)])
    tts = dict(duration_s=20,alignment=fake_alignment(script_text(script['beats']),20))
    data = run_plan(RunPaths(tmp_path/'run'),script,tts,source,max_shot_s=4,hook_seconds=10,
                    download_source=lambda vid,dest: shutil.copyfile(cut_video,dest),log=lambda m:None)
    assert any(s['hook_segment'] is not None for s in data['shots'] if s['beat']==0)
    for shot in data['shots']:
        if shot['beat'] >= 1:
            assert shot['hook_segment'] is None
        if shot['beat'] in ctas:
            assert shot['auto_cta'] is True
            assert shot['subject'] == ''
            assert shot['source_rank'] is None
            assert shot['group'] == 'auto-cta'
            assert shot['keywords'] == {'en': [], 'zh': []}
            assert shot['ref_frames'] == []
        else:
            if shot['beat'] >= 1:
                assert shot['keywords']['en'] == script['beats'][shot['beat']]['queries']
            assert len(shot['ref_frames']) == 3
