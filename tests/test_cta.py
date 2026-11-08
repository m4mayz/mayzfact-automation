import pytest

from mayzfact.cta import cta_kinds


def test_tapping_like_is_detected_in_approved_transition():
    assert cta_kinds('But before number one, try tapping like.') == {'like'}


def test_conditional_like_is_detected_in_approved_cta():
    assert cta_kinds("Subscribe if you'd touch it, like if you'd watch, or comment 'nope' if you'd run.") == {
        'like', 'subscribe', 'comment'}


@pytest.mark.parametrize('text', ['Like if you agree.', 'Then like if you agree.', 'And like if you agree.',
                                 'Watch it. Like if you agree.', 'Subscribe, then like if you agree.'])
def test_like_if_requires_an_inviting_clause(text):
    assert 'like' in cta_kinds(text)


@pytest.mark.parametrize('text', ['If you like these animals, subscribe.', 'Animals like this are rare.',
                                 'I like if they stay calm.', 'It moves like a tapping dancer.',
                                 'The button looks like a volcano.', 'Tapping the screen feels like rain.'])
def test_conditional_like_does_not_match_opinion_or_comparison(text):
    assert 'like' not in cta_kinds(text)
