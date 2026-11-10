"""Cegah objek narasi diganti kartu kata pada naskah baru."""
import pytest
from pydantic import ValidationError

from mayzfact.models import Script
from mayzfact.steps.script import check_script
from tests.top3_fixtures import playful_script


def test_new_object_cta_cannot_use_word_card():
    raw = playful_script().model_dump()
    raw['cta_scene'] = dict(theme='word', label='HONEY', transform_word='turn', comment_text='HONEY')
    with pytest.raises(ValidationError):
        Script.model_validate(raw)


def test_honey_scene_is_supported_without_text_label():
    from mayzfact.models import CtaScene
    scene = CtaScene(theme='honey', transform_word='turn', comment_text='HONEY')
    assert scene.theme == 'honey'


def test_puppy_scene_is_supported_without_text_label():
    from mayzfact.models import CtaScene
    scene = CtaScene(theme='puppy', transform_word='turn', comment_text='WOOF')
    assert scene.theme == 'puppy'


def test_lion_scene_is_supported_without_text_label():
    from mayzfact.models import CtaScene
    scene = CtaScene(theme='lion', transform_word='turn', comment_text='ROAR')
    assert scene.theme == 'lion'


def test_shark_scene_is_supported_without_text_label():
    from mayzfact.models import CtaScene
    scene = CtaScene(theme='shark', transform_word='turn', comment_text='SHARK')
    assert scene.theme == 'shark'


def test_illustration_must_match_named_object_in_cta():
    raw = playful_script().model_dump()
    raw['cta_scene'] = dict(theme='unicorn', transform_word='turn', comment_text='MAGIC')
    issues, _ = check_script(Script.model_validate(raw), '')
    assert any('does not match' in issue for issue in issues)


def test_supported_illustration_matches_transform_without_changing_text_hash():
    from mayzfact.text import script_text, text_hash
    for theme, phrase in [('volcano', 'a volcano'), ('unicorn', 'a unicorn'), ('honey', 'honey'), ('puppy', 'a puppy'), ('lion', 'a lion'), ('shark', 'a shark')]:
        raw = playful_script().model_dump()
        raw['beats'][8]['text'] = f'Did the button turn into {phrase}?'
        before = text_hash(script_text(raw['beats']))
        raw['cta_scene'] = dict(theme=theme, transform_word='turn', comment_text='DONE')
        parsed = Script.model_validate(raw)
        issues, _ = check_script(parsed, '')
        assert not any('illustration' in issue.lower() for issue in issues), issues
        assert text_hash(script_text(parsed.model_dump()['beats'])) == before


def test_unsupported_and_word_themes_are_rejected():
    from mayzfact.models import CtaScene
    with pytest.raises(ValidationError):
        CtaScene.model_validate(dict(theme='crystal', transform_word='turn', comment_text='SHINY'))
    with pytest.raises(ValidationError):
        CtaScene(theme='word', label='HONEY', transform_word='turn', comment_text='HONEY')


@pytest.mark.parametrize('comment', [
    'and comment turn into a unicorn.',
    "and comment 'Did the button turn into a unicorn?'.",
    'and comment "Did the button turn into a unicorn?".',
    'and comment “Did the button turn into a unicorn?”.',
])
@pytest.mark.parametrize('theme, matches', [('unicorn', False), ('honey', True)])
def test_comment_transformation_cannot_override_actual_honey_question(comment, theme, matches):
    raw = playful_script().model_dump()
    raw['beats'][8]['text'] = 'Did the button turn into honey?'
    raw['beats'][10]['text'] = comment
    raw['cta_scene'] = dict(theme=theme, transform_word='turn', comment_text='UNICORN')
    issues, _ = check_script(Script.model_validate(raw), '')
    assert any('does not match' in issue for issue in issues) is not matches, issues


@pytest.mark.parametrize('quote', ["'", '"', '“', '‘'])
@pytest.mark.parametrize('theme, matches', [('unicorn', False), ('honey', True)])
def test_quoted_transformation_is_not_the_actual_question(quote, theme, matches):
    closing = {'“': '”', '‘': '’'}.get(quote, quote)
    raw = playful_script().model_dump()
    raw['beats'][8]['text'] = (
        f'{quote}Did the button turn into a unicorn?{closing} Did the button turn into honey?'
    )
    raw['cta_scene'] = dict(theme=theme, transform_word='turn', comment_text='DONE')
    issues, _ = check_script(Script.model_validate(raw), '')
    assert any('does not match' in issue for issue in issues) is not matches, issues


@pytest.mark.parametrize('theme, matches', [('unicorn', False), ('honey', True)])
def test_comment_in_question_beat_does_not_override_transformation(theme, matches):
    raw = playful_script().model_dump()
    raw['beats'][8]['text'] = 'Did the button turn into honey? Comment turn into a unicorn.'
    raw['cta_scene'] = dict(theme=theme, transform_word='turn', comment_text='DONE')
    issues, _ = check_script(Script.model_validate(raw), '')
    assert any('does not match' in issue for issue in issues) is not matches, issues


def test_mention_in_comment_does_not_validate_wrong_transformation():
    raw = playful_script().model_dump()
    raw['beats'][10]['text'] = "and comment 'unicorn'."
    raw['cta_scene'] = dict(theme='unicorn', transform_word='turn', comment_text='UNICORN')
    issues, _ = check_script(Script.model_validate(raw), '')
    assert any('does not match' in issue for issue in issues)
