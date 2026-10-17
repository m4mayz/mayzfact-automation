from mayzfact.shots import beat_subjects, split_shots


def test_split_shots_respects_max_duration_and_media():
    timings = [{"start_s": 0.0, "end_s": 2.4}, {"start_s": 2.4, "end_s": 6.4}, {"start_s": 6.4, "end_s": 7.0}]
    beats = [{"media": "video"}, {"media": "photo"}, {"media": "video"}]
    slots = split_shots(timings, beats, 2.5)
    assert [(s.index, s.beat, s.part, s.start_s, s.end_s, s.media) for s in slots] == [
        (0, 0, 0, 0.0, 2.4, "video"),
        (1, 1, 0, 2.4, 4.4, "photo"),
        (2, 1, 1, 4.4, 6.4, "photo"),
        (3, 2, 0, 6.4, 7.0, "video"),
    ]


def test_split_shots_exact_multiple_is_not_split_further():
    slots = split_shots([{"start_s": 0.0, "end_s": 5.0}], [{"media": "video"}], 2.5)
    assert [(s.start_s, s.end_s) for s in slots] == [(0.0, 2.5), (2.5, 5.0)]


def test_beat_subjects_from_field_or_countdown():
    beats = [
        {"text": "Check out five ancient beasts!"},
        {"text": "Number five, horseshoe crab."},
        {"text": "It resembles an armored tank!"},
        {"text": "Number four: Nautilus!"},
        {"text": "It swims.", "subject": "chambered nautilus"},
        {"text": "Number 3, the platypus."},
    ]
    assert beat_subjects(beats) == [None, "horseshoe crab", "horseshoe crab", "nautilus", "chambered nautilus", "platypus"]
