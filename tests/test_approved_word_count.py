"""Pengecualian panjang naskah yang disetujui untuk satu run Top 3."""
from mayzfact.models import CtaScene, Script
from mayzfact.steps.script import narration_word_range


def test_approved_word_count_survives_json_and_sets_exact_budget():
    script = Script.model_validate({
        'narration_mode': 'top3', 'beats': [], 'approved_word_count': 131,
        'cta_scene': CtaScene(theme='volcano', transform_word='turns', comment_text='NOPE'),
    })
    restored = Script.model_validate_json(script.model_dump_json())
    assert narration_word_range(restored, 77.345, 1.0) == (131, 131, 131)


def test_default_budget_stays_unchanged():
    script = Script(narration_mode='top3', beats=[],
                    cta_scene=CtaScene(theme='volcano', transform_word='turns', comment_text='NOPE'))
    assert narration_word_range(script, 77.345, 1.0) == (73, 70, 76)


def test_invalid_approved_counts_are_rejected():
    import pytest
    from pydantic import ValidationError
    for count in [0, -1, 501, True, 131.5, '131']:
        with pytest.raises(ValidationError):
            Script(narration_mode='top3', beats=[], approved_word_count=count,
                   cta_scene=CtaScene(theme='volcano', transform_word='turns', comment_text='NOPE'))


def test_approval_does_not_disable_other_script_checks():
    from mayzfact.steps.script import check_script
    script = Script(narration_mode='top3', approved_word_count=1, beats=[{
        'text': 'Wrong.', 'media': 'video', 'queries': [],
    }], cta_scene=CtaScene(theme='volcano', transform_word='turns', comment_text='NOPE'))
    issues, _ = check_script(script, '', 77.345, video_speed=1.0)
    assert not any('The narration has' in issue for issue in issues)
    assert any('Top 3 requires exactly' in issue for issue in issues)
    assert any('no search queries' in issue for issue in issues)
