import pytest


def test_top3_word_budget_ignores_source_length_and_honors_speed():
    from mayzfact.steps.script import check_script
    from tests.top3_fixtures import SOURCE_TEXT, top3_script

    assert check_script(top3_script(), SOURCE_TEXT, 120)[0] == []
    for count in [75, 85]:
        problems, _ = check_script(top3_script(count), SOURCE_TEXT, 120)
        assert any('words' in p for p in problems)
    from mayzfact.steps.script import narration_word_range
    assert narration_word_range(top3_script(), 120, 1.1) == (80, 76, 84)
    assert narration_word_range(top3_script(), 120, 1.0) == (73, 70, 76)
    for speed in [0, -1, float('nan'), float('inf')]:
        with pytest.raises(ValueError, match='speed'):
            narration_word_range(top3_script(), 120, speed)


@pytest.mark.parametrize('change', ['extra', 'missing', 'duplicate', 'swapped_subject', 'source_missing', 'source_duplicate'])
def test_top3_requires_exact_original_source_ranks(change):
    from mayzfact.steps.script import check_script
    from tests.top3_fixtures import SOURCE_TEXT, top3_script

    script, source = top3_script(), SOURCE_TEXT
    if change == 'extra':
        script.beats[1].text = 'Number five, basilisk lizards.'
    elif change == 'missing':
        script.beats[4].text = 'Here comes another creature.'
    elif change == 'duplicate':
        script.beats[4].text = 'Number three, immortal jellyfish.'
    elif change == 'swapped_subject':
        script.beats[1].text = 'Number three, immortal jellyfish.'
    elif change == 'source_missing':
        source = source.replace('Number three,', 'Third place is')
    else:
        source += ' Number three, basilisk lizards.'
    problems, _ = check_script(script, source, 45)
    assert any('Top 3' in p for p in problems)


def test_top3_source_headings_accept_normalized_case_spaces_and_chunks():
    import tempfile
    from pathlib import Path

    from mayzfact.steps.script import check_script_file
    from mayzfact.store import RunPaths, write_json_atomic
    from tests.top3_fixtures import SOURCE_TEXT, top3_script

    with tempfile.TemporaryDirectory() as folder:
        paths = RunPaths(Path(folder))
        write_json_atomic(paths.script_json, top3_script().model_dump())
        text = SOURCE_TEXT.replace('Number three, basilisk lizards.', 'NUMBER 3:  BASILISK   LIZARDS.')
        source = dict(duration_s=90, transcript=[dict(text=p) for p in text.split(' ', 7)])
        assert check_script_file(paths, source, ratio=.8, minimum_s=32, bgm_choices=None) == []


@pytest.mark.parametrize('change', ['early', 'late', 'gap', 'too_many', 'missing_like', 'no_cta', 'one_explanation', 'five_hook', 'bad_announcement'])
def test_top3_enforces_cta_block_and_editorial_structure(change):
    from mayzfact.steps.script import check_script
    from tests.top3_fixtures import SOURCE_TEXT, top3_script

    s = top3_script()
    if change == 'early':
        s.beats = s.beats[7:9] + s.beats[:7] + s.beats[9:]
    elif change == 'late':
        s.beats = s.beats[:7] + s.beats[9:] + s.beats[7:9]
    elif change == 'gap':
        s.beats.insert(9, s.beats.pop(6))
    elif change == 'too_many':
        s.beats[8:8] = [s.beats[8].model_copy() for _ in range(3)]
    elif change == 'missing_like':
        s.beats[7].text = "Subscribe if you'd touch it or watch,"
    elif change == 'no_cta':
        s.beats = s.beats[:7] + s.beats[9:]
    elif change == 'one_explanation':
        del s.beats[6]
    elif change == 'five_hook':
        s.beats[0].text = s.beats[0].text.replace('three', 'five')
    else:
        s.beats[1].text = 'number 3: basilisk lizards!'
    problems, _ = check_script(s, SOURCE_TEXT, 45)
    assert any('Top 3' in p or 'explanation' in p for p in problems)


def test_cli_uses_top3_budget_and_nondefault_speed(tmp_path, monkeypatch, capsys):
    from mayzfact import cli
    from mayzfact.config import Settings
    from mayzfact.store import RunPaths, write_json_atomic
    from tests.top3_fixtures import SOURCE_TEXT, top3_script

    paths = RunPaths(tmp_path / 'abcdefghijk')
    write_json_atomic(paths.source_json, dict(duration_s=90, transcript=[dict(text=SOURCE_TEXT)]))
    write_json_atomic(paths.script_json, top3_script().model_dump())
    monkeypatch.setattr(cli, 'RUNS_DIR', tmp_path)
    monkeypatch.setattr(cli, 'load_settings', lambda: Settings())
    assert cli.main(['check-script', 'abcdefghijk']) == 0
    assert '80 kata, target 80' in capsys.readouterr().out
    monkeypatch.setattr(cli, 'load_settings', lambda: Settings(video_speed=1.0))
    assert cli.main(['check-script', 'abcdefghijk']) == 1
    assert 'between 70 and 76' in capsys.readouterr().out
