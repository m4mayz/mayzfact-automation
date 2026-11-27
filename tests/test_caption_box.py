import pytest
from pydantic import ValidationError

from mayzfact.models import Script
from mayzfact.steps.timeline import (
    BOX_MAX_CHARS,
    BOX_MAX_WORDS,
    CAPTION_KEYWORD,
    _beat_of,
    _box_chunks,
    build_timeline,
)
from mayzfact.cta import _EDGE_PUNCT
from mayzfact.timing import word_timings
from tests.faktacuil_fixtures import faktacuil_script, faktacuil_timeline_fixture
from tests.top3_fixtures import top3_script


def spoken(alignment):
    return [w for w in word_timings(alignment) if _EDGE_PUNCT.sub("", w["text"])]


def box_timeline():
    script = faktacuil_script(cta="none").model_dump()
    script["caption_style"] = "box"
    script, alignment, clips = faktacuil_timeline_fixture(25, script)
    tl = build_timeline(clips, 25, 0.5, script=script, alignment=alignment, audio=None, log=lambda m: None)
    return script, alignment, tl


def test_caption_style_defaults_to_word_and_rejects_unknown():
    assert faktacuil_script().caption_style == "word"
    with pytest.raises(ValidationError):
        Script(**{**faktacuil_script().model_dump(), "caption_style": "neon"})


def test_box_caption_style_is_faktacuil_only():
    with pytest.raises(ValidationError, match="caption_style"):
        Script(**{**top3_script().model_dump(), "caption_style": "box"})


def test_default_faktacuil_captions_have_no_group():
    script, alignment, clips = faktacuil_timeline_fixture(25)
    tl = build_timeline(clips, 25, 0.5, script=script, alignment=alignment, audio=None, log=lambda m: None)
    assert tl["captionStyle"] == "faktacuil"
    assert all("group" not in c for c in tl["captions"])


def test_box_timeline_groups_words_per_beat_in_original_case():
    script, alignment, tl = box_timeline()
    assert tl["captionStyle"] == "faktacuil-box"
    caps = tl["captions"]
    assert caps and all("group" in c for c in caps)
    assert any(c["text"] != c["text"].upper() for c in caps)  # huruf asli, bukan kapital semua
    words = word_timings(alignment)
    beat_of = [b for w, b in zip(words, _beat_of(words, script["beats"])) if _EDGE_PUNCT.sub("", w["text"])]
    by_group: dict[int, set[int]] = {}
    for cap, beat in zip(caps, beat_of, strict=True):
        by_group.setdefault(cap["group"], set()).add(beat)
    assert all(len(beats) == 1 for beats in by_group.values())  # 1 tampilan nggak nyebrang beat
    groups = sorted(by_group)
    assert groups == list(range(len(groups)))
    for g in groups:
        texts = [c["text"] for c in caps if c["group"] == g]
        assert len(texts) <= BOX_MAX_WORDS and sum(len(t) for t in texts) <= BOX_MAX_CHARS or len(texts) == 1


def test_box_keeps_keyword_color():
    _, _, tl = box_timeline()
    assert any(c["color"] == CAPTION_KEYWORD for c in tl["captions"])


def test_box_chunks_split_long_beat_evenly():
    words = "Kenapa orang Jepang nggak mau pakai paku waktu bikin rumah?".split()
    chunks = _box_chunks(words)
    assert [len(c) for c in chunks] == [5, 5]
    assert [w for c in chunks for w in c] == words
    assert _box_chunks(["Halo", "semua"]) == [["Halo", "semua"]]
    assert _box_chunks(["Pneumonoultramicroscopicsilicovolcanoconiosis", "ya"]) == [["Pneumonoultramicroscopicsilicovolcanoconiosis"], ["ya"]]


def test_box_words_keep_timing_of_word_style():
    script, alignment, tl = box_timeline()
    starts = [c["from"] for c in tl["captions"]]
    assert starts == sorted(starts) and len(starts) == len(spoken(alignment))
