import pytest

from mayzfact.steps.timeline import _beat_of, _top3_cta, build_timeline
from mayzfact.text import script_text
from mayzfact.timing import beat_timings, word_timings
from tests.factories import fake_alignment
from tests.top3_fixtures import playful_script, top3_script


@pytest.mark.parametrize('duration', [38.5, 3.85])
def test_approved_top3_cta_events_follow_spoken_order_before_number_one(duration):
    script = top3_script().model_dump()
    script['beats'][7]['text'] = "Subscribe if you'd touch it, like if you'd watch,"
    alignment = fake_alignment(script_text(script['beats']), duration)
    times = beat_timings([b['text'] for b in script['beats']], alignment, duration)
    clips = {'shots': [dict(file=f'clips/shot_{i}.mp4', kind='video', start_s=t['start_s'],
                           width=1080, height=1920, beat=i) for i,t in enumerate(times)]}
    timeline = build_timeline(clips, duration, .5, script=script, alignment=alignment)
    assert [c['number'] for c in timeline['countdown']] == [3,2,1]
    words = word_timings(alignment)
    beat_of = _beat_of(words, script['beats'])
    cta = _top3_cta(words, beat_of, script['beats'], timeline['countdown'], timeline['durationInFrames'])
    assert [c['kind'] for c in cta] == ['subscribe','like']
    one = timeline['countdown'][-1]['numberFrom']
    cta_begin = round(times[7]['start_s'] * 30)
    for c in cta:
        assert cta_begin <= c['from'] < one
        assert c['from'] + c['durationInFrames'] <= one
        assert 0 <= c['clickAt'] < c['durationInFrames']
    sub,like = cta
    assert sub['from'] + sub['durationInFrames'] <= like['from']


@pytest.mark.parametrize('duration', [38.5, 3.85])
def test_playful_cta_animations_start_on_actual_invitation_words(duration):
    from mayzfact.steps.timeline import to_frame

    script = playful_script().model_dump()
    alignment = fake_alignment(script_text(script['beats']), duration)
    times = beat_timings([b['text'] for b in script['beats']], alignment, duration)
    clips = {'shots': [dict(file=f'clips/shot_{i}.mp4', kind='video', start_s=t['start_s'],
                           width=1080, height=1920, beat=i) for i, t in enumerate(times)]}
    timeline = build_timeline(clips, duration, .5, script=script, alignment=alignment)
    words = word_timings(alignment)
    beat_of = _beat_of(words, script['beats'])
    cta = _top3_cta(words, beat_of, script['beats'], timeline['countdown'], timeline['durationInFrames'])
    assert [c['kind'] for c in cta] == ['like', 'subscribe']
    expected = [to_frame(w['start_s']) for w in words if w['text'].lower().strip('.,') in ['like', 'subscribe']]
    assert [c['from'] for c in cta] == expected
    one = timeline['countdown'][-1]['numberFrom']
    for c in cta:
        assert 0 <= c['clickAt'] < c['durationInFrames']
        assert c['from'] + c['durationInFrames'] <= one
    question_from = to_frame(times[8]['start_s'])
    question_end = to_frame(times[8]['end_s'])
    assert not any(question_from <= c['from'] < question_end for c in cta)
    assert any(c['text'] == 'VOLCANO' for c in timeline['captions'])


def test_scene_cta_keeps_click_sfx_without_legacy_overlay():
    duration = 38.5
    script = top3_script().model_dump()
    alignment = fake_alignment(script_text(script['beats']), duration)
    times = beat_timings([b['text'] for b in script['beats']], alignment, duration)
    clips = {'shots': [dict(file=f'clips/shot_{i}.mp4', kind='video', start_s=t['start_s'],
                           width=1080, height=1920, beat=i) for i, t in enumerate(times)]}
    audio = {'bgm': None, 'sfx': {'click': 'audio/sfx/click.mp3'}}
    timeline = build_timeline(clips, duration, .5, script=script, alignment=alignment, audio=audio)
    words = word_timings(alignment)
    beat_of = _beat_of(words, script['beats'])
    actions = _top3_cta(words, beat_of, script['beats'], timeline['countdown'], timeline['durationInFrames'])
    assert 'cta' not in timeline
    clicks = [item for item in timeline['sfx'] if item['src'] == 'audio/sfx/click.mp3']
    assert len(actions) == 2
    assert len(clicks) == len(actions)


def test_timeline_without_mode_uses_top3_click_order():
    duration = 38.5
    script = top3_script().model_dump()
    script.pop('narration_mode')
    alignment = fake_alignment(script_text(script['beats']), duration)
    times = beat_timings([b['text'] for b in script['beats']], alignment, duration)
    clips = {'shots': [dict(file=f'clips/shot_{i}.mp4', kind='video', start_s=t['start_s'],
                           width=1080, height=1920, beat=i) for i, t in enumerate(times)]}
    audio = {'bgm': None, 'sfx': {'click': 'audio/sfx/click.mp3'}}
    timeline = build_timeline(clips, duration, .5, script=script, alignment=alignment, audio=audio)
    words = word_timings(alignment)
    beat_of = _beat_of(words, script['beats'])
    actions = _top3_cta(words, beat_of, script['beats'], timeline['countdown'], timeline['durationInFrames'])
    expected = [max(0, action['from'] + action['clickAt'] - 3) for action in actions]
    clicks = [item['from'] for item in timeline['sfx'] if item['src'] == 'audio/sfx/click.mp3']
    assert len(actions) == 2
    assert clicks == expected


def test_cta_scene_has_no_legacy_label():
    duration = 38.5
    script = playful_script().model_dump()
    alignment = fake_alignment(script_text(script['beats']), duration)
    times = beat_timings([b['text'] for b in script['beats']], alignment, duration)
    clips = {'shots': [dict(file=f'clips/shot_{i}.mp4', kind='video', start_s=t['start_s'],
                           width=1080, height=1920, beat=i) for i, t in enumerate(times)]}
    timeline = build_timeline(clips, duration, .5, script=script, alignment=alignment)
    assert 'label' not in timeline['ctaScene']
