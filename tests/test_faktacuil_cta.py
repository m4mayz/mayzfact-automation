import pytest

from mayzfact.faktacuil import faktacuil_cta_indices, id_like_begin, id_like_positions
from mayzfact.narration import cta_beat_indices, cta_indices
from tests.faktacuil_fixtures import faktacuil_script
from tests.top3_fixtures import top3_script


@pytest.mark.parametrize("text,expected", [
    ("Tapi coba tekan like dulu,", [3]),
    ("tekan tombol like sekarang", [2]),
    ("pencet like ya", [1]),
    ("apakah like-mu berubah jadi madu?", []),
    ("aku like video ini", []),
    ("like video ini", []),
])
def test_id_like_positions(text, expected):
    assert id_like_positions(text.split()) == expected


def test_like_begin_walks_back_to_coba():
    tokens = "Tapi coba tekan like dulu,".split()
    assert id_like_begin(tokens, 3) == 1


def test_cta_block_includes_gimmick_question():
    assert faktacuil_cta_indices(faktacuil_script().model_dump()["beats"]) == [4, 5]


def test_like_word_outside_cta_makes_block_non_contiguous():
    beats = faktacuil_script().model_dump()["beats"]
    beats[7]["text"] = "rasanya like permen buat kucing."
    assert faktacuil_cta_indices(beats) == [4, 5, 6, 7]  # anchor terakhir narik blok; check_script nolak (test_faktacuil_review_fixes)


def test_cta_indices_dispatch_keeps_top3():
    top = top3_script()
    assert cta_indices(top) == cta_beat_indices(top.beats)
    assert cta_indices(faktacuil_script()) == [4, 5]


@pytest.mark.parametrize("word", ["subscribe", "komen", "komentar", "comment"])
def test_subscribe_and_comment_words_are_cta_anchors(word):
    beats = faktacuil_script().model_dump()["beats"]
    beats[7]["text"] = f"jangan lupa {word} ya,"
    assert faktacuil_cta_indices(beats) == [4, 5, 6, 7]
