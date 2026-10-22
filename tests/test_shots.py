from mayzfact.shots import beat_subjects, split_shots, tighten_countdown
from mayzfact.timing import beat_timings
from tests.factories import fake_alignment


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


def test_countdown_box_ends_right_after_subject_name():
    """Kayak source i2xag: box ditutup pas nama subjek selesai diucapin (platypus ±0,5 dtk, horseshoe crab ±0,8 dtk)."""
    beats = [{"text": "Look at this.", "media": "video"}, {"text": "Number five, horseshoe crab.", "media": "photo"},
             {"text": "It is old.", "media": "video"}]
    texts = [b["text"] for b in beats]
    full = " ".join(texts)
    alignment = fake_alignment(full, 2.0)  # nama subjek ±0,6 detik
    pause_from = full.index("It is")
    for key in ("character_start_times_seconds", "character_end_times_seconds"):  # jeda 2 detik habis nama subjek
        alignment[key] = [t + 2.0 if i >= pause_from else t for i, t in enumerate(alignment[key])]
    name_end = alignment["character_end_times_seconds"][full.index("crab.") + 4]  # kata "crab." sampai titiknya
    slots = split_shots(beat_timings(texts, alignment, 4.0), beats, 10.0)
    out = tighten_countdown(slots, beats, alignment)
    assert out[0] == slots[0] and out[1].start_s == slots[1].start_s
    assert out[1].end_s == out[2].start_s == round(name_end + 0.1, 3)
    assert out[2].end_s == slots[2].end_s


def test_countdown_box_keeps_a_minimum_when_name_is_short():
    beats = [{"text": "Look.", "media": "video"}, {"text": "Number one, ox.", "media": "photo"}, {"text": "It is old and big.", "media": "video"}]
    texts = [b["text"] for b in beats]
    full = " ".join(texts)
    alignment = fake_alignment(full, 3.0)  # cepat: "ox." cuma ±0,25 detik
    pause_from = full.index("It is")
    for key in ("character_start_times_seconds", "character_end_times_seconds"):  # jeda 2 detik habis nama subjek
        alignment[key] = [t + 2.0 if i >= pause_from else t for i, t in enumerate(alignment[key])]
    name_start = alignment["character_start_times_seconds"][full.index("ox.")]
    slots = split_shots(beat_timings(texts, alignment, 5.0), beats, 10.0)
    out = tighten_countdown(slots, beats, alignment)
    assert out[1].end_s == out[2].start_s == round(name_start + 0.5, 3)  # box tetap minimal 0,5 detik


def test_countdown_box_capped_when_name_is_long():
    beats = [{"text": "Look.", "media": "video"}, {"text": "Number two, American dipper bird.", "media": "photo"},
             {"text": "It is old.", "media": "video"}]
    texts = [b["text"] for b in beats]
    full = " ".join(texts)
    alignment = fake_alignment(full, 10.0)  # nama subjek panjang & lambat (±2 detik)
    name_start = alignment["character_start_times_seconds"][full.index("American")]
    slots = split_shots(beat_timings(texts, alignment, 10.0), beats, 10.0)
    out = tighten_countdown(slots, beats, alignment)
    assert out[1].end_s == out[2].start_s == round(name_start + 0.9, 3)  # maksimal 0,9 detik (source 0,5-0,8)


def test_countdown_box_untouched_when_already_short():
    beats = [{"text": "Number five, crab.", "media": "photo"}, {"text": "It is old.", "media": "video"}]
    texts = [b["text"] for b in beats]
    alignment = fake_alignment(" ".join(texts), 2.0)
    slots = split_shots(beat_timings(texts, alignment, 2.0), beats, 10.0)
    assert tighten_countdown(slots, beats, alignment) == slots
