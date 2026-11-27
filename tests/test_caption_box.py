import pytest
from pydantic import ValidationError

from mayzfact.cta import _EDGE_PUNCT
from mayzfact.models import Script
from mayzfact.steps.timeline import (
    CAPTION_KEYWORD,
    _beat_of,
    _box_chunks,
    build_timeline,
)
from mayzfact.timing import word_timings
from tests.faktacuil_fixtures import faktacuil_script, faktacuil_timeline_fixture
from tests.top3_fixtures import top3_script


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
    assert [c["group"] for c in caps] == sorted(c["group"] for c in caps)
    assert sorted(by_group) == list(range(len(by_group)))
    split = 0
    for beat in sorted(set(beat_of)):
        idx = [i for i, b in enumerate(beat_of) if b == beat]
        sizes = [sum(1 for i in idx if caps[i]["group"] == g) for g in sorted({caps[i]["group"] for i in idx})]
        assert sizes == [len(c) for c in _box_chunks([caps[i]["text"] for i in idx])]
        split += len(sizes) > 1
    assert split >= 1  # fixture punya beat 7 kata / 40 huruf yang harus kebagi

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
    _, _, box = box_timeline()
    script, alignment, clips = faktacuil_timeline_fixture(25, faktacuil_script(cta="none").model_dump())
    word = build_timeline(clips, 25, 0.5, script=script, alignment=alignment, audio=None, log=lambda m: None)
    key = lambda c: (c["from"], c["durationInFrames"], c["color"])  # noqa: E731
    assert [key(c) for c in box["captions"]] == [key(c) for c in word["captions"]]
    assert [c["text"].upper() for c in box["captions"]] == [c["text"] for c in word["captions"]]
