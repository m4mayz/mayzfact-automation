"""Kontrak CTA hiburan; alignment di test bukan audio/TTS produksi."""
import pytest

from mayzfact.models import Beat
from mayzfact.narration import cta_beat_indices, top3_problems
from tests.top3_fixtures import SOURCE_TEXT, playful_script, top3_script


@pytest.mark.parametrize('as_dict', [False, True])
def test_shared_detector_includes_triggerless_question_in_approved_block(as_dict):
    script = playful_script()
    beats = script.model_dump()['beats'] if as_dict else script.beats
    assert cta_beat_indices(beats) == [7, 8, 9, 10]


def test_shared_detector_includes_separate_transition_before_first_invitation():
    script = playful_script()
    script.beats[7:9] = [
        Beat(media='video', text='But before number one,', queries=['phone']),
        Beat(media='video', text='try tapping like.', queries=['phone']),
    ]
    assert cta_beat_indices(script.beats) == [7, 8, 9, 10]


def test_shared_detector_never_bridges_countdown_to_detached_invitation():
    script = playful_script()
    script.beats[-1].text = 'And comment your choice.'
    assert cta_beat_indices(script.beats) == [7, 8, 9, 10, 13]


def test_approved_four_beat_cta_satisfies_top3_structure():
    assert top3_problems(playful_script(), SOURCE_TEXT) == []


@pytest.mark.parametrize('index', [7, 8, 9, 10])
@pytest.mark.parametrize('mark', ['subject', 'point'])
def test_every_cta_beat_including_question_requires_empty_subject_and_no_point(index, mark):
    script = playful_script()
    setattr(script.beats[index], mark, 'volcano' if mark == 'subject' else True)
    problems = top3_problems(script, SOURCE_TEXT)
    assert any('CTA' in p and mark in p for p in problems)


@pytest.mark.parametrize('change', ['early', 'late', 'trailing_gap', 'body_intrusion', 'five_beats', 'detached'])
def test_playful_cta_rejects_wrong_placement_and_body_intrusion(change):
    script = playful_script()
    if change == 'early':
        script.beats = script.beats[7:11] + script.beats[:7] + script.beats[11:]
    elif change == 'late':
        script.beats = script.beats[:7] + script.beats[11:] + script.beats[7:11]
    elif change == 'trailing_gap':
        script.beats.insert(10, script.beats.pop(6))
    elif change == 'body_intrusion':
        script.beats[8] = script.beats[6].model_copy()
    elif change == 'five_beats':
        script.beats.insert(8, script.beats[8].model_copy())
    else:
        script.beats[0].text = 'Hit like for these three animals.'
    assert any('CTA' in p for p in top3_problems(script, SOURCE_TEXT))


def test_cta_extra_words_shift_only_top3_shared_total_budget():
    from mayzfact.steps.script import narration_word_range
    from mayzfact.text import words

    script = playful_script()
    assert sum(len(words(script.beats[i].text)) for i in cta_beat_indices(script.beats)) == 21
    assert narration_word_range(script, 120, 1.1) == (91, 87, 95)
    assert narration_word_range(script, 120, 1.0) == (84, 81, 87)
    assert narration_word_range(top3_script(), 120, 1.1) == (80, 76, 84)


@pytest.mark.parametrize('base_words,valid', [(75, False), (76, True), (80, True), (84, True), (85, False)])
def test_approved_cta_keeps_body_budget_bounded(base_words, valid):
    from mayzfact.steps.script import check_script
    from mayzfact.text import words

    script = playful_script(base_words)
    original = top3_script(base_words)
    assert [b.model_dump() for i, b in enumerate(script.beats) if i not in cta_beat_indices(script.beats)] == [
        b.model_dump() for i, b in enumerate(original.beats) if i not in cta_beat_indices(original.beats)]
    assert sum(len(words(b.text)) for b in script.beats) == base_words + 11
    problems, _ = check_script(script, SOURCE_TEXT, 120)
    assert (problems == []) is valid
    if not valid:
        assert any('between 87 and 95' in p for p in problems)


def test_old_two_beat_cta_wording_stays_supported_with_shared_delta():
    from mayzfact.steps.script import check_script, narration_word_range

    script = top3_script()
    script.beats[7].text = "Subscribe, it turns into a volcano, like if you'd watch,"
    script.beats[8].text = "or comment 'nope' if you'd run."
    assert cta_beat_indices(script.beats) == [7, 8]
    assert narration_word_range(script, 120) == (86, 82, 90)
    assert check_script(script, SOURCE_TEXT, 120)[0] == []


def test_triggerless_question_does_not_replace_item_two_explanation():
    from mayzfact.steps.script import check_script

    script = playful_script()
    del script.beats[6]
    problems, _ = check_script(script, SOURCE_TEXT, 120)
    assert any('Number two' in p and 'only 1 explanation' in p for p in problems)


def test_cta_with_eleven_words_is_rejected_despite_total_allowance():
    from mayzfact.steps.script import check_script

    script = playful_script()
    script.beats[8].text = 'Did the little button really turn into a giant erupting volcano?'
    problems, _ = check_script(script, SOURCE_TEXT, 120)
    assert any('Beat 9 has 11 words' in p and 'at most 10' in p for p in problems)


def test_maximum_four_ten_word_cta_beats_still_have_a_finite_budget():
    from mayzfact.steps.script import check_script, narration_word_range
    from mayzfact.text import words

    script = playful_script()
    for i in range(7, 11):
        n = len(words(script.beats[i].text))
        script.beats[i].text += ' extra' * (10 - n)
    assert narration_word_range(script, 120) == (110, 106, 114)
    assert check_script(script, SOURCE_TEXT, 120)[0] == []


def test_short_legacy_cta_does_not_reduce_base_word_budget():
    from mayzfact.steps.script import narration_word_range

    script = top3_script()
    script.beats[7:9] = [script.beats[7].model_copy(update={'text': 'Subscribe, hit like, and comment.'})]
    assert top3_problems(script, SOURCE_TEXT) == []
    assert narration_word_range(script, 120) == (80, 76, 84)


def test_cli_reports_same_cta_adjusted_budget(tmp_path, monkeypatch, capsys):
    from mayzfact import cli
    from mayzfact.config import Settings
    from mayzfact.store import RunPaths, write_json_atomic

    paths = RunPaths(tmp_path / 'abcdefghijk')
    write_json_atomic(paths.script_json, playful_script().model_dump())
    write_json_atomic(paths.source_json, dict(duration_s=90, transcript=[dict(text=SOURCE_TEXT)]))
    monkeypatch.setattr(cli, 'RUNS_DIR', tmp_path)
    monkeypatch.setattr(cli, 'load_settings', lambda: Settings())
    assert cli.main(['check-script', 'abcdefghijk']) == 0
    assert '91 kata, target 91' in capsys.readouterr().out
