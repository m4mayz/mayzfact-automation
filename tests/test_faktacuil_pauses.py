"""Tes aturan jeda FaktaCuil: hening maksimal 0,2 detik."""
from mayzfact.pauses import (
    keep_segments,
    parse_silences,
    plan_cuts,
    shift_alignment,
    shift_time,
)

STDERR = """[silencedetect @ 0x1] silence_start: 3.236054
[silencedetect @ 0x1] silence_end: 4.511837 | silence_duration: 1.275782
[silencedetect @ 0x1] silence_start: 6.764694
[silencedetect @ 0x1] silence_end: 7.252766 | silence_duration: 0.488073
[silencedetect @ 0x1] silence_start: 29.101429
[silencedetect @ 0x1] silence_end: 29.293243 | silence_duration: 0.191814
"""


def test_parse_silences_ambil_start_end():
    assert parse_silences(STDERR) == [(3.236054, 4.511837), (6.764694, 7.252766), (29.101429, 29.293243)]


def test_plan_cuts_sisain_02_detik_di_awal_hening():
    cuts = plan_cuts(parse_silences(STDERR), 0.2)
    assert len(cuts) == 2
    assert cuts[0][0] == 3.236054 + 0.2
    assert cuts[0][1] == 4.511837


def test_plan_cuts_hening_pendek_nggak_dipotong():
    cuts = plan_cuts([(29.101429, 29.293243)], 0.2)
    assert cuts == []


def test_keep_segments_urut_dan_mentok_durasi():
    segments = keep_segments(31.76, [(3.436054, 4.511837), (6.964694, 7.252766)])
    assert segments == [(0.0, 3.436054), (4.511837, 6.964694), (7.252766, 31.76)]


def test_shift_time_buang_durasi_potongan_sebelumnya():
    cuts = [(3.436054, 4.511837)]
    assert shift_time(3.0, cuts) == 3.0
    assert round(shift_time(5.511837, cuts), 6) == 4.436054
    assert round(shift_time(10.0, cuts), 6) == 8.924217


def test_shift_alignment_geser_semua_timestamp():
    alignment = {
        "characters": ["a", "b", "c"],
        "character_start_times_seconds": [0.0, 3.5, 5.0],
        "character_end_times_seconds": [0.4, 4.0, 5.5],
    }
    out = shift_alignment(alignment, [(3.436054, 4.511837)])
    assert out["characters"] == ["a", "b", "c"]
    assert out["character_start_times_seconds"][0] == 0.0
    assert round(out["character_start_times_seconds"][1], 6) == 3.436054
    assert round(out["character_start_times_seconds"][2], 6) == 3.924217


def test_shift_alignment_tanpa_potongan_balikin_apa_adanya():
    alignment = {"characters": ["a"], "character_start_times_seconds": [0.0]}
    assert shift_alignment(alignment, []) is alignment
