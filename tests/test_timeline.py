import pytest

from mayzfact.errors import PipelineError
from mayzfact.steps.timeline import build_timeline, run_timeline, to_frame
from mayzfact.store import RunPaths, read_json
from tests.factories import fake_alignment


def shot(file, kind, start_s, width, height):
    return {"file": file, "kind": kind, "start_s": start_s, "width": width, "height": height}


CLIPS = {
    "shots": [
        shot("clips/shot_01.mp4", "video", 0.0, 1080, 1920),
        shot("clips/shot_02.jpg", "photo", 2.4, 1600, 1000),
        shot("clips/shot_03.mp4", "video", 4.4, 1920, 1080),
    ]
}


def test_to_frame_rounds_half_up():
    assert to_frame(0.0) == 0
    assert to_frame(2.4) == 72
    assert to_frame(0.0167) == 1
    assert to_frame(0.0166) == 0


def test_build_timeline_frames_layouts_and_total():
    timeline = build_timeline(CLIPS, audio_duration_s=6.5, fg_min_ratio=0.5)
    assert (timeline["fps"], timeline["width"], timeline["height"], timeline["durationInFrames"]) == (30, 1080, 1920, 195)
    assert (timeline["audio"], timeline["photoZoom"]) == ("voice.mp3", 1.08)
    assert timeline["shots"] == [
        {"src": "clips/shot_01.mp4", "kind": "video", "layout": "full", "from": 0, "durationInFrames": 72},
        {"src": "clips/shot_02.jpg", "kind": "photo", "layout": "blur", "from": 72, "durationInFrames": 60, "fgHeight": 960},
        {"src": "clips/shot_03.mp4", "kind": "video", "layout": "blur", "from": 132, "durationInFrames": 63, "fgHeight": 960},
    ]
    assert sum(s["durationInFrames"] for s in timeline["shots"]) == timeline["durationInFrames"]


def test_backslash_paths_become_forward_slashes():
    timeline = build_timeline({"shots": [shot("clips\\shot_01.mp4", "video", 0.0, 1080, 1920)]}, 2.0, 0.5)
    assert timeline["shots"][0]["src"] == "clips/shot_01.mp4"


def test_zero_frame_shot_is_an_error():
    clips = {"shots": [shot("clips/a.mp4", "video", 0.0, 1080, 1920), shot("clips/b.mp4", "video", 0.01, 1080, 1920)]}
    with pytest.raises(PipelineError, match="0 frame"):
        build_timeline(clips, 2.0, 0.5)


def test_run_timeline_writes_json(tmp_path):
    paths = RunPaths(tmp_path)
    data = run_timeline(paths, CLIPS, {"duration_s": 6.5}, fg_min_ratio=0.5)
    assert read_json(paths.timeline_json) == data


SCRIPT = {"beats": [{"text": "Look at this creature."}, {"text": "Number five, horseshoe crab."}, {"text": "It is old."}]}
ALIGN = fake_alignment("Look at this creature. Number five, horseshoe crab. It is old.", 6.2)
CD_CLIPS = {"shots": [shot("clips/shot_01.mp4", "video", 0.0, 1080, 1920), shot("clips/shot_02.mp4", "video", 2.3, 1080, 1920),
                      shot("clips/shot_03.jpg", "photo", 5.2, 1080, 1920)]}


def test_countdown_card_covers_countdown_beat():
    timeline = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN)
    assert timeline["countdown"] == [{
        "number": 5, "label": "HORSESHOE CRAB", "numberFrom": 69, "numberAt": 0, "numberDuration": 39,
        "cardFrom": 108, "cardDuration": 48, "src": "clips/shot_02.mp4", "kind": "video", "clipOffset": 39,
    }]
    assert len(timeline["shots"]) == 3


def test_captions_one_word_each_outside_countdown():
    captions = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN)["captions"]
    assert [(c["text"], c["from"], c["durationInFrames"]) for c in captions] == [
        ("LOOK", 0, 15), ("AT", 15, 9), ("THIS", 24, 15), ("CREATURE", 39, 30),
        ("IT", 156, 9), ("IS", 165, 9), ("OLD", 174, 21),
    ]
    colors = {c["text"]: c["color"] for c in captions}
    assert colors["LOOK"] == colors["IT"] == "#ffffff" and colors["CREATURE"] == "#22d3ee"


def test_caption_colors_cycle_and_subject_words_are_colored():
    script = {"beats": [{"text": "Number two, eel."}, {"text": "The eel is enormous and ancient."}]}
    align = fake_alignment("Number two, eel. The eel is enormous and ancient.", 4.9)
    captions = build_timeline({"shots": [shot("clips/a.mp4", "video", 0.0, 1080, 1920)]}, 5.0, 0.5, script=script, alignment=align)["captions"]
    assert [(c["text"], c["color"]) for c in captions] == [
        ("THE", "#ffffff"), ("EEL", "#22d3ee"), ("IS", "#ffffff"), ("ENORMOUS", "#4ade80"), ("AND", "#ffffff"), ("ANCIENT", "#facc15")]


def test_unknown_number_has_no_card_and_keeps_captions():
    script = {"beats": [{"text": "Number eleven, x."}]}
    timeline = build_timeline({"shots": [shot("clips/a.mp4", "video", 0.0, 1080, 1920)]}, 2.0, 0.5,
                              script=script, alignment=fake_alignment("Number eleven, x.", 1.7))
    assert timeline["countdown"] == []
    assert [c["text"] for c in timeline["captions"]] == ["NUMBER", "ELEVEN", "X"]


def test_without_script_or_with_bad_alignment_timeline_still_builds():
    plain = build_timeline(CLIPS, 6.5, 0.5)
    assert plain["captions"] == [] and plain["countdown"] == []
    logs = []
    bad = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=fake_alignment("beda total", 1.0), log=logs.append)
    assert bad["captions"] == [] and bad["countdown"] == [] and logs


def test_warns_when_card_runs_past_its_clip():
    split = {"shots": [shot("clips/shot_01.mp4", "video", 0.0, 1080, 1920), shot("clips/shot_02.mp4", "video", 2.3, 1080, 1920),
                       shot("clips/shot_02b.mp4", "video", 4.0, 1080, 1920), shot("clips/shot_03.jpg", "photo", 5.2, 1080, 1920)]}
    logs = []
    timeline = build_timeline(split, 6.5, 0.5, script=SCRIPT, alignment=ALIGN, log=logs.append)
    assert timeline["countdown"][0]["src"] == "clips/shot_02.mp4"
    assert any("--from" in line for line in logs)
    logs.clear()
    build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN, log=logs.append)
    assert logs == []


def test_short_end_times_fall_back_without_crash():
    bad = {**ALIGN, "character_end_times_seconds": ALIGN["character_end_times_seconds"][:5]}
    timeline = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=bad, log=lambda m: None)
    assert timeline["captions"] == [] and timeline["countdown"] == []


AUDIO = {"bgm": "audio/bgm/mystery.mp3", "sfx": {"hook": "audio/sfx/h.mp3", "number": "audio/sfx/n.mp3",
                                                 "subject": "audio/sfx/s.mp3", "cut": "audio/sfx/c.mp3"}}


def test_sfx_and_bgm_placement():
    timeline = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN, audio=AUDIO)
    assert timeline["bgm"] == {"src": "audio/bgm/mystery.mp3", "volume": 0.12, "fadeOutFrames": 30}
    # shot ke-2 ketutup card → nggak dapat "cut"; card dapat "number" + "subject"; shot ke-3 dapat "cut" 3 frame sebelum ganti.
    assert timeline["sfx"] == [
        {"src": "audio/sfx/h.mp3", "from": 0, "volume": 0.8},
        {"src": "audio/sfx/n.mp3", "from": 66, "volume": 0.9},
        {"src": "audio/sfx/s.mp3", "from": 105, "volume": 0.7},
        {"src": "audio/sfx/c.mp3", "from": 153, "volume": 0.35},
    ]


def test_cut_sfx_on_plain_shots_and_missing_audio():
    timeline = build_timeline(CLIPS, 6.5, 0.5, audio={"bgm": None, "sfx": {"cut": "audio/sfx/c.mp3"}})
    assert timeline["bgm"] is None
    assert [s["from"] for s in timeline["sfx"]] == [69, 129]
    plain = build_timeline(CLIPS, 6.5, 0.5)
    assert plain["bgm"] is None and plain["sfx"] == []


def test_intro_transition_goes_with_hook_sfx():
    # Kayak transisi antar scene di source: scene masuk putih + blur vertikal, cepat tajam, terangnya pudar ±7 frame.
    with_hook = build_timeline(CLIPS, 6.5, 0.5, audio={"bgm": None, "sfx": {"hook": "audio/sfx/h.mp3"}})
    assert with_hook["intro"] == {"durationInFrames": 7}
    assert build_timeline(CLIPS, 6.5, 0.5, audio={"bgm": None, "sfx": {}})["intro"] is None
    assert build_timeline(CLIPS, 6.5, 0.5)["intro"] is None

def point(t, x=100):
    return {"t": t, "x": x, "y": 200, "w": 300, "h": 400}


def test_overlays_from_detections():
    overlays = {"clips/shot_01.mp4": {"points": [point(0.5), point(1.5, x=150)]},
                "clips/shot_02.jpg": {"points": None},
                "clips/shot_03.mp4": {"points": [point(0.5)]}}
    timeline = build_timeline(CLIPS, 6.5, 0.5, overlays=overlays)
    assert timeline["overlays"] == [
        {"type": "arrow", "color": "#ff2a2a", "from": 6, "durationInFrames": 51,
         "keyframes": [{"frame": 9, "x": 100, "y": 200, "w": 300, "h": 400}, {"frame": 39, "x": 150, "y": 200, "w": 300, "h": 400}]},
        {"type": "arrow", "color": "#ffd400", "from": 138, "durationInFrames": 42,
         "keyframes": [{"frame": 9, "x": 100, "y": 200, "w": 300, "h": 400}]},
    ]
    assert build_timeline(CLIPS, 6.5, 0.5)["overlays"] == []


def test_every_fifth_overlay_is_a_circle_and_cards_are_skipped():
    shots = {"shots": [shot(f"clips/s{i}.mp4", "video", float(i), 1080, 1920) for i in range(0, 12, 2)]}
    overlays = {f"clips/s{i}.mp4": {"points": [point(0.5)]} for i in range(0, 12, 2)}
    types = [o["type"] for o in build_timeline(shots, 12.5, 0.5, overlays=overlays)["overlays"]]
    assert types == ["arrow", "arrow", "arrow", "arrow", "circle", "arrow"]
    covered = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN,
                             overlays={"clips/shot_02.mp4": {"points": [point(0.5)]}})
    assert covered["overlays"] == []



def test_voice_onset_moves_number_and_captions():
    import numpy as np

    from mayzfact.voice_onset import STEP_S

    env = np.zeros(int(6.5 / STEP_S))
    for start, end in [(0.0, 2.2), (2.8, 3.0), (3.1, 3.4), (3.7, 5.1), (5.4, 6.2)]:  # "Number" baru kedengeran di 2.8s
        env[int(start / STEP_S):int(end / STEP_S)] = 1000.0
    timeline = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN, voice_envelope=env,
                              audio={"bgm": None, "sfx": {"number": "audio/sfx/w.mp3"}})
    card = timeline["countdown"][0]
    assert (card["numberFrom"], card["numberAt"], card["cardFrom"]) == (69, 15, 111)
    assert timeline["sfx"] == [{"src": "audio/sfx/w.mp3", "from": 81, "volume": 0.9}]
    assert [c["from"] for c in timeline["captions"] if c["text"] == "IT"] == [162]


def test_overlay_sfx_plays_when_overlay_appears():
    overlays = {"clips/shot_01.mp4": {"points": [point(0.5)]}}
    timeline = build_timeline(CLIPS, 6.5, 0.5, overlays=overlays, audio={"bgm": None, "sfx": {"overlay": "audio/sfx/t.mp3"}})
    assert timeline["sfx"] == [{"src": "audio/sfx/t.mp3", "from": 6, "volume": 0.35}]


def test_overlay_skipped_when_shot_too_short():
    short = {"shots": [shot("clips/a.mp4", "video", 0.0, 1080, 1920), shot("clips/b.mp4", "video", 0.8, 1080, 1920)]}
    overlays = {"clips/a.mp4": {"points": [point(0.2)]}}
    assert build_timeline(short, 3.0, 0.5, overlays=overlays)["overlays"] == []



NO_MARK = {"point": False, "emoji": "", "emoji_word": ""}


def test_emoji_pops_on_its_word_until_beat_end():
    marks = {"beats": [{"point": False, "emoji": "🧐", "emoji_word": "creature"}, NO_MARK,
                       {"point": False, "emoji": "😮", "emoji_word": ""}],
             "emoji": {"🧐": "emoji/1f9d0.json", "😮": "emoji/1f62e.json"}}
    timeline = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN, marks=marks,
                              audio={"bgm": None, "sfx": {"emoji": "audio/sfx/pop.mp3"}})
    assert timeline["emojis"] == [{"src": "emoji/1f9d0.json", "from": 39, "durationInFrames": 30},
                                  {"src": "emoji/1f62e.json", "from": 156, "durationInFrames": 39}]
    assert timeline["sfx"] == [{"src": "audio/sfx/pop.mp3", "from": 39, "volume": 0.6},
                               {"src": "audio/sfx/pop.mp3", "from": 156, "volume": 0.6}]
    assert build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN)["emojis"] == []


def test_emoji_runs_past_its_beat_but_stops_before_next_emoji_or_video_end():
    script = {"beats": [{"text": "Look at this creature."}, {"text": "It is so old."}, {"text": "Wow."}]}
    text = "Look at this creature. It is so old. Wow."
    marks = {"beats": [{"point": False, "emoji": "🧐", "emoji_word": "creature"}, NO_MARK,
                       {"point": False, "emoji": "😮", "emoji_word": "wow"}],
             "emoji": {"🧐": "emoji/1f9d0.json", "😮": "emoji/1f62e.json"}}
    one = {"shots": [shot("clips/a.mp4", "video", 0.0, 1080, 1920)]}
    timeline = build_timeline(one, 4.4, 0.5, script=script, alignment=fake_alignment(text, 4.1), marks=marks)
    # 🧐 mulai di "creature" (frame 39), nyebrang ke beat ke-2 sampai 😮 mulai di "Wow" (frame 111)
    assert timeline["emojis"] == [{"src": "emoji/1f9d0.json", "from": 39, "durationInFrames": 72},
                                  {"src": "emoji/1f62e.json", "from": 111, "durationInFrames": 21}]


def test_emoji_word_right_before_a_card_starts_on_an_earlier_word():
    script = {"beats": [{"text": "Look at this old crab."}, {"text": "Number five, horseshoe crab."}, {"text": "It is old."}]}
    align = fake_alignment("Look at this old crab. Number five, horseshoe crab. It is old.", 6.2)
    marks = {"beats": [{"point": False, "emoji": "🧐", "emoji_word": "crab"}, NO_MARK, NO_MARK],
             "emoji": {"🧐": "emoji/1f9d0.json"}}
    timeline = build_timeline(CD_CLIPS, 6.5, 0.5, script=script, alignment=align, marks=marks)
    # "crab" (51) cuma 18 frame sebelum card #5 (69), jadi mulainya dimajuin ke "old" (39) biar tampil 1 detik
    assert timeline["emojis"] == [{"src": "emoji/1f9d0.json", "from": 39, "durationInFrames": 30}]


CTA_TEXT = "Tap like and subscribe now. It looks like a tank."
CTA_SCRIPT = {"beats": [{"text": "Tap like and subscribe now."}, {"text": "It looks like a tank."}]}
CTA_CLIPS = {"shots": [shot("clips/a.mp4", "video", 0.0, 1080, 1920)]}


def test_cta_like_then_subscribe_with_clicks():
    timeline = build_timeline(CTA_CLIPS, 5.0, 0.5, script=CTA_SCRIPT, alignment=fake_alignment(CTA_TEXT, 4.9),
                              audio={"bgm": None, "sfx": {"click": "audio/sfx/click.mp3"}})
    # "like" di beat ke-2 artinya "mirip", bukan CTA.
    assert timeline["cta"] == [{"kind": "like", "from": 12, "durationInFrames": 16, "clickAt": 4},
                               {"kind": "subscribe", "from": 39, "durationInFrames": 27, "clickAt": 14}]
    assert timeline["sfx"] == [{"src": "audio/sfx/click.mp3", "from": 13, "volume": 0.8},
                               {"src": "audio/sfx/click.mp3", "from": 50, "volume": 0.8}]


def test_subscribe_waits_until_like_finishes():
    text = "Like, subscribe."
    timeline = build_timeline(CTA_CLIPS, 1.5, 0.5, script={"beats": [{"text": text}]}, alignment=fake_alignment(text, 1.0))
    # "subscribe" cuma 11 frame setelah "like": animasi subscribe nunggu like selesai, kayak di source
    assert timeline["cta"] == [{"kind": "like", "from": 0, "durationInFrames": 16, "clickAt": 4},
                               {"kind": "subscribe", "from": 16, "durationInFrames": 27, "clickAt": 14}]


def test_emoji_that_collides_with_cta_starts_after_it():
    marks = {"beats": [{"point": False, "emoji": "🍀", "emoji_word": "subscribe"}, NO_MARK], "emoji": {"🍀": "emoji/1f340.json"}}
    timeline = build_timeline(CTA_CLIPS, 5.0, 0.5, script=CTA_SCRIPT, alignment=fake_alignment(CTA_TEXT, 4.9), marks=marks)
    # subscribe 39-66 → 🍀 mulai di 66, maksimal 75 frame tapi berhenti di akhir video (150)
    assert timeline["emojis"] == [{"src": "emoji/1f340.json", "from": 66, "durationInFrames": 75}]


def test_overlays_only_inside_point_beats():
    overlays = {"clips/shot_01.mp4": {"points": [point(0.5)]}, "clips/shot_03.jpg": {"points": [point(0.2)]}}
    marks = {"beats": [NO_MARK, NO_MARK, dict(NO_MARK, point=True)], "emoji": {}}
    timeline = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN, overlays=overlays, marks=marks)
    assert [(o["from"], o["durationInFrames"]) for o in timeline["overlays"]] == [(162, 18)]
    # Klip panjang yang nutup beberapa beat (kayak hook nyambung): panah cuma di rentang beat point.
    one = {"shots": [shot("clips/long.mp4", "video", 0.0, 1080, 1920)]}
    timeline = build_timeline(one, 6.5, 0.5, script=SCRIPT, alignment=ALIGN, marks=marks,
                              overlays={"clips/long.mp4": {"points": [point(0.5), point(6.0, x=300)]}})
    long = timeline["overlays"][0]
    assert (long["from"], long["durationInFrames"]) == (162, 18)
    assert long["keyframes"][0]["frame"] == 15 - 162 and long["keyframes"][1]["frame"] == 180 - 162
