from mayzfact.text import clean_text, ngram_overlap, script_text, text_hash, words


def test_clean_text_turns_fancy_punctuation_into_ascii():
    assert clean_text("It’s  “huge” — really… wow now") == 'It\'s "huge", really... wow now'
    assert clean_text("1–2 eggs") == "1-2 eggs"


def test_words_lowercases_and_keeps_apostrophes():
    assert words("They’re HERE, 100 times!") == ["they're", "here", "100", "times"]


def test_ngram_overlap():
    source = "these animals have been around for millions of years"
    assert ngram_overlap(source, source) == 1.0
    assert ngram_overlap("a totally different sentence about crabs", source) == 0.0
    assert ngram_overlap("too short", source) == 0.0
    # 4-gram baru: (have been around for) ada di source, (been around for ages) nggak
    assert ngram_overlap("have been around for ages", source) == 0.5


def test_script_text_joins_cleaned_beats_with_single_space():
    beats = [{"text": " Look  at this. "}, {"text": "It’s old."}]
    assert script_text(beats) == "Look at this. It's old."


def test_text_hash_is_sha256():
    assert text_hash("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
