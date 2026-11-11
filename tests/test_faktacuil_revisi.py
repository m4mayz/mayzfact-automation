"""Revisi FaktaCuil dari preview gu2M14rfRlU: caption ngilang pas jeda, tanda tanya, intro kayak MayzFact."""

from mayzfact.steps.timeline import _captions, build_timeline, to_frame
from mayzfact.timing import word_timings
from tests.faktacuil_fixtures import faktacuil_timeline_fixture


def alignment_of(spec):
    """[(teks, mulai, selesai)] per karakter; spasi diselipin otomatis di antara kata."""
    chars, starts, ends = [], [], []
    for word in spec:
        if chars:
            chars.append(" ")
            starts.append(ends[-1])
            ends.append(word[0][1])
        for char, start, end in word:
            chars.append(char)
            starts.append(start)
            ends.append(end)
    return {"characters": chars, "character_start_times_seconds": starts, "character_end_times_seconds": ends}


# Pola ElevenLabs di gu2M14rfRlU: jeda habis "rumah?" ikut ke karakter "?" (2.80-3.52).
RUMAH = [("r", 2.46, 2.52), ("u", 2.52, 2.58), ("m", 2.58, 2.64), ("a", 2.64, 2.72), ("h", 2.72, 2.80),
         ("?", 2.80, 3.52)]
MUNGKIN = [("M", 3.56, 3.60), ("u", 3.60, 3.70), ("n", 3.70, 3.92)]
BIKIN = [("b", 2.20, 2.26), ("i", 2.26, 2.32), ("k", 2.32, 2.36), ("i", 2.36, 2.40), ("n", 2.40, 2.44)]


def test_word_timings_voice_end_skips_trailing_punctuation():
    words = word_timings(alignment_of([RUMAH, MUNGKIN]))
    assert words[0]["end_s"] == 3.52 and words[0]["voice_end_s"] == 2.80
    assert words[1]["voice_end_s"] == words[1]["end_s"] == 3.92


def test_faktacuil_caption_hides_during_long_pause():
    words = word_timings(alignment_of([BIKIN, RUMAH, MUNGKIN]))
    caps = _captions(words, 4.0, [], set(), 120, keywords={}, beat_of=[0, 0, 1])
    rumah = caps[1]
    assert rumah["from"] + rumah["durationInFrames"] == to_frame(2.80 + 0.15)  # 0.15 detik setelah suaranya habis
    bikin = caps[0]
    assert bikin["from"] + bikin["durationInFrames"] == rumah["from"]  # jeda pendek: tetap nyambung


def test_faktacuil_caption_keeps_question_mark():
    words = word_timings(alignment_of([BIKIN, RUMAH, MUNGKIN]))
    caps = _captions(words, 4.0, [], set(), 120, keywords={0: "rumah"}, beat_of=[0, 0, 1])
    assert [c["text"] for c in caps] == ["BIKIN", "RUMAH?", "MUN"]
    assert caps[1]["color"] == "#FFC53D"  # keyword tetap kena walau ada "?"


def test_top3_caption_unchanged():
    words = word_timings(alignment_of([BIKIN, RUMAH, MUNGKIN]))
    caps = _captions(words, 4.0, [], set(), 120)
    assert caps[1]["text"] == "RUMAH"
    assert caps[1]["from"] + caps[1]["durationInFrames"] == to_frame(3.56)  # tetap nyambung ke kata berikutnya


AUDIO = {"bgm": None, "bgm_main": "audio/bgm/main.mp3", "riser_s": 2.0,
         "sfx": {"hook": "audio/sfx/hook.mp3", "riser": "audio/sfx/riser.mp3", "cut": "audio/sfx/cut.mp3"}}


def test_faktacuil_intro_matches_mayzfact_without_riser():
    script, alignment, clips = faktacuil_timeline_fixture(25)
    tl = build_timeline(clips, 25, 0.5, script=script, alignment=alignment, audio=AUDIO, log=lambda m: None)
    assert tl["intro"] == {"durationInFrames": 7}
    srcs = [s["src"] for s in tl["sfx"]]
    assert {"src": "audio/sfx/hook.mp3", "from": 0, "volume": 0.8} in tl["sfx"]
    assert "audio/sfx/riser.mp3" not in srcs


def test_faktacuil_cta_uses_faktabor_style_over_normal_clips():
    script, alignment, clips = faktacuil_timeline_fixture(25)
    tl = build_timeline(clips, 25, 0.5, script=script, alignment=alignment, audio=AUDIO, log=lambda m: None)
    scene = tl["ctaScene"]
    assert scene["style"] == "faktacuil"
    begin, end = scene["from"], scene["from"] + scene["durationInFrames"]
    inside = [s for s in tl["shots"] if begin <= s["from"] < end]
    assert inside and not any(s.get("decorative") for s in inside)  # klip CTA dari brief, tampil normal kayak FaktaBor


def test_top3_cta_scene_keeps_mayzfact_style():
    from tests.test_cta_scene import timeline_fixture

    script, alignment, clips = timeline_fixture()
    tl = build_timeline(clips, 20, 0.5, script=script, alignment=alignment)
    assert "style" not in tl["ctaScene"]
