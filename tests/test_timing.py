import pytest

from mayzfact.errors import PipelineError
from mayzfact.timing import beat_offsets, beat_timings
from tests.factories import fake_alignment


def test_beat_offsets():
    assert beat_offsets(["ab", "cde", "f"]) == [0, 3, 7]


def test_beat_timings_are_contiguous_and_end_at_audio():
    texts = ["Look at this.", "It is old.", "Wow."]
    alignment = fake_alignment(" ".join(texts), 1.45)
    assert beat_timings(texts, alignment, 2.0) == [
        {"start_s": 0.0, "end_s": 0.7},
        {"start_s": 0.7, "end_s": 1.25},
        {"start_s": 1.25, "end_s": 2.0},
    ]


def test_beat_timings_with_punctuation_and_apostrophes():
    texts = ["It's huge, right?", 'He said "wait" - then ran...']
    timings = beat_timings(texts, fake_alignment(" ".join(texts), 4.0), 4.5)
    assert timings[0]["start_s"] == 0.0
    assert timings[0]["end_s"] == timings[1]["start_s"]
    assert timings[1]["end_s"] == 4.5


def test_alignment_mismatch_is_an_error_that_keeps_voice():
    alignment = fake_alignment("Look at this! It is old.", 2.4)
    with pytest.raises(PipelineError, match="jangan generate ulang"):
        beat_timings(["Look at this.", "It is old."], alignment, 3.0)


def test_audio_shorter_than_last_beat_is_an_error():
    texts = ["Look at this.", "It is old."]
    with pytest.raises(PipelineError, match="Timing beat 2"):
        beat_timings(texts, fake_alignment(" ".join(texts), 2.4), 1.0)


def test_word_timings_group_characters_per_word():
    from mayzfact.timing import word_timings

    words = word_timings(fake_alignment("Hi there,  it's ok.", 1.9))
    assert [(w["text"], w["char_start"], w["char_end"]) for w in words] == [
        ("Hi", 0, 1), ("there,", 3, 8), ("it's", 11, 14), ("ok.", 16, 18)]
    assert (words[1]["start_s"], words[1]["end_s"]) == (0.3, 0.9)
    assert word_timings({"characters": [], "character_start_times_seconds": [], "character_end_times_seconds": []}) == []
