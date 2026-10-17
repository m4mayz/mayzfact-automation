from mayzfact.countdown import Countdown, parse_countdown
from mayzfact.shots import beat_subjects, split_shots


def test_parse_countdown_words_digits_and_the():
    assert parse_countdown("Number five, horseshoe crab.") == Countdown(5, "horseshoe crab", 10)
    assert parse_countdown("number 3: the platypus!") == Countdown(3, "platypus", 7)
    assert parse_countdown("  NUMBER ONE - Tardigrade") == Countdown(1, "Tardigrade", 9)  # index di teks yang udah di-clean


def test_parse_countdown_unknown_number_keeps_subject():
    assert parse_countdown("Number eleven, x.") == Countdown(None, "x", 12)
    assert parse_countdown("It is old.") is None
    assert parse_countdown("Number five is cool") is None


def test_beat_subjects_still_carry_countdown_subject():
    beats = [{"text": "Intro."}, {"text": "Number five, Horseshoe Crab."}, {"text": "It is old."},
             {"text": "Next one.", "subject": "nautilus"}]
    assert beat_subjects(beats) == [None, "horseshoe crab", "horseshoe crab", "nautilus"]


def test_split_shots_keeps_countdown_beat_whole():
    beats = [{"text": "Number five, horseshoe crab.", "media": "photo"}, {"text": "It is a very old animal.", "media": "video"}]
    timings = [{"start_s": 0.0, "end_s": 6.0}, {"start_s": 6.0, "end_s": 12.0}]
    slots = split_shots(timings, beats, 4.0)
    assert [(s.beat, s.start_s, s.end_s) for s in slots] == [(0, 0.0, 6.0), (1, 6.0, 9.0), (1, 9.0, 12.0)]


def test_parse_countdown_same_on_raw_and_cleaned_text():
    assert parse_countdown("Number five — the horseshoe crab.") == Countdown(5, "horseshoe crab", 10)
    beats = [{"text": "Number five — the horseshoe crab.", "media": "photo"}]
    assert len(split_shots([{"start_s": 0.0, "end_s": 9.0}], beats, 4.0)) == 1
    assert beat_subjects(beats) == ["horseshoe crab"]


def test_parse_countdown_ignores_decimal_numbers():
    assert parse_countdown("Number 1.5 million crabs live here.") is None
