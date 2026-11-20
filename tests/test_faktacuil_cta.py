import pytest

from mayzfact.faktacuil import (
    count_word,
    faktacuil_cta_indices,
    id_like_begin,
    id_like_positions,
    quiz_count,
    quiz_index,
)
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


def beats_of(*texts):
    return [{"text": t} for t in texts]


def test_lucky_object_beat_joins_block_via_muncul():
    b = beats_of("Hook,", "Padahal salah,", "Tapi sebelum lanjut, coba tekan like,", "jika beruntung bisa muncul madu.",
                 "Ternyata a,", "jadi b.")
    assert faktacuil_cta_indices(b) == [2, 3]


def test_emoji_lead_in_joins_block_backwards():
    b = beats_of("Hook,", "Ternyata a,", "Tapi mengapa ada emoji madu", "saat tekan like?")
    assert faktacuil_cta_indices(b) == [2, 3]


def test_answer_with_muncul_is_not_absorbed_when_block_has_muncul():
    b = beats_of("Hook,", "Padahal salah,", "Tapi coba tekan like, nanti muncul madu,", "Ternyata bulunya muncul lagi.",
                 "jadi b.")
    assert faktacuil_cta_indices(b) == [2]


def test_quiz_beat_is_never_a_cta_anchor():
    b = beats_of("Hook kardus,", "kardus lagi,", "Nah coba tebak berapa kali aku bilang kardus di video like ini?")
    assert faktacuil_cta_indices(b) == []
    assert quiz_index(b) == 2


def test_count_word_is_whole_word_case_insensitive():
    assert count_word("Kardus, kardusnya, kardus-kardus, KARDUS.", "kardus") == 2


def test_quiz_count_excludes_quiz_beat():
    b = beats_of("Kenapa kucing suka kardus?", "Padahal Kardus itu keras,", "Nah coba tebak berapa kali aku bilang kardus")
    assert quiz_count(b, "kardus") == 2
    assert quiz_count(beats_of("tanpa kuis kardus"), "kardus") == 0


def test_answer_muncul_does_not_pull_emoji_cta_backwards():
    b = beats_of("Ternyata jerawat muncul karena hormon.", "Tapi mengapa ada emoji jerawat saat tekan like?")
    assert faktacuil_cta_indices(b) == [1]


def test_misconception_with_emoji_stays_out_of_lucky_block():
    b = beats_of("Hook,", "Padahal emoji itu cuma hiasan,", "Tapi sebelum lanjut, coba tekan like,",
                 "jika beruntung bisa muncul madu.", "Ternyata a,", "jadi b.")
    assert faktacuil_cta_indices(b) == [2, 3]


def test_quiz_phrase_matches_cleaned_tokens():
    b = beats_of("Hook,", "Nah, berapa kali,  aku bilang kardus, like?")
    assert quiz_index(b) == 1
    assert faktacuil_cta_indices(b) == []
