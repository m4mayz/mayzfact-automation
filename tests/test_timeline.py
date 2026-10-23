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


def test_card_ends_where_next_clip_starts_when_plan_shortened_the_box():
    early = {"shots": [{**CD_CLIPS["shots"][0], "beat": 0}, {**CD_CLIPS["shots"][1], "beat": 1},
                       {**shot("clips/shot_03.jpg", "photo", 4.5, 1080, 1920), "beat": 2}]}
    card = build_timeline(early, 6.5, 0.5, script=SCRIPT, alignment=ALIGN)["countdown"][0]
    assert card["cardFrom"] + card["cardDuration"] == 135  # 4,5 detik, bukan ujung beat (156)


def test_card_runs_until_next_beat_clip_when_plan_lengthened_the_box():
    late = {"shots": [{**CD_CLIPS["shots"][0], "beat": 0}, {**CD_CLIPS["shots"][1], "beat": 1},
                      {**shot("clips/shot_03.jpg", "photo", 5.6, 1080, 1920), "beat": 2}]}
    card = build_timeline(late, 6.5, 0.5, script=SCRIPT, alignment=ALIGN)["countdown"][0]
    assert card["cardFrom"] + card["cardDuration"] == 168  # 5,6 detik, lewat ujung beat countdown (156)


def test_text_blurs_follow_layout_on_shots_and_cards():
    from mayzfact.overlay import screen_box

    blurs = {"clips/shot_01.mp4": [(0.4, 0.9, 0.6, 0.95)], "clips/shot_02.mp4": [(0.1, 0.1, 0.3, 0.2)]}
    timeline = build_timeline(CD_CLIPS, 6.5, 0.5, script=SCRIPT, alignment=ALIGN, blurs=blurs)
    x, y, w, h = screen_box((0.4, 0.9, 0.6, 0.95), 1080, 1920, fg_min_ratio=0.5)
    assert timeline["shots"][0]["blurs"] == [{"x": x, "y": y, "w": w, "h": h}]
    assert "blurs" not in timeline["shots"][2]
    # card nampilin klip shot_02 di box 820x820 (object-fit cover): kotaknya ikut skala box
    assert timeline["countdown"][0]["blurs"] == [{"x": 82, "y": round(820 * (1920 / 1080) * 0.1 - (820 * 1920 / 1080 - 820) / 2),
                                                  "w": 164, "h": round(820 * 1920 / 1080 * 0.1)}]


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
    assert timeline["bgm"] == [{"src": "audio/bgm/mystery.mp3", "from": 0, "durationInFrames": 195, "volume": 0.12,
                               "fadeOutFrames": 30}]
    # shot ke-2 ketutup card → nggak dapat "cut"; card dapat "number" + "subject"; shot ke-3 dapat "cut" 3 frame sebelum ganti.
    assert timeline["sfx"] == [
        {"src": "audio/sfx/h.mp3", "from": 0, "volume": 0.8},
        {"src": "audio/sfx/n.mp3", "from": 60, "volume": 0.9},
        {"src": "audio/sfx/s.mp3", "from": 105, "volume": 0.7},
        {"src": "audio/sfx/c.mp3", "from": 153, "volume": 0.4},  # klik 0,4 (Akmal: jangan terlalu keras)
    ]


def test_cut_sfx_on_plain_shots_and_missing_audio():
    timeline = build_timeline(CLIPS, 6.5, 0.5, audio={"bgm": None, "sfx": {"cut": "audio/sfx/c.mp3"}})
    assert timeline["bgm"] == []
    assert [s["from"] for s in timeline["sfx"]] == [69, 129]
    plain = build_timeline(CLIPS, 6.5, 0.5)
    assert plain["bgm"] == [] and plain["sfx"] == []


def test_hook_clip_changes_get_camera_flash_and_white_flash():
    clips = {"shots": [{**shot("clips/h1.mp4", "video", 0.0, 1080, 1920), "hook_segment": 0},
                       {**shot("clips/h2.mp4", "video", 1.0, 1080, 1920), "hook_segment": 1},
                       {**shot("clips/h3.mp4", "video", 2.0, 1080, 1920), "hook_segment": 2},
                       shot("clips/a.mp4", "video", 3.0, 1080, 1920)]}
    audio = {"bgm": None, "sfx": {"cut": "audio/sfx/click.mp3", "hook_cut": "audio/sfx/flash.mp3"}}
    t = build_timeline(clips, 4.0, 0.5, audio=audio)
    # di dalam hook (frame 30, 60): camera flash + flash putih; masuk isi (90): klik kayak biasa
    assert [(x["from"], x["src"]) for x in t["sfx"]] == [(27, "audio/sfx/flash.mp3"), (57, "audio/sfx/flash.mp3"),
                                                          (87, "audio/sfx/click.mp3")]
    assert t["flashes"] == [{"from": 30, "durationInFrames": 3}, {"from": 60, "durationInFrames": 3}]


def test_hook_cut_adds_one_random_hook_extra_at_low_volume():
    clips = {"shots": [{**shot("clips/h1.mp4", "video", 0.0, 1080, 1920), "hook_segment": 0},
                       {**shot("clips/h2.mp4", "video", 1.0, 1080, 1920), "hook_segment": 1},
                       {**shot("clips/h3.mp4", "video", 2.0, 1080, 1920), "hook_segment": 2},
                       shot("clips/a.mp4", "video", 3.0, 1080, 1920)]}
    audio = {"bgm": None, "sfx": {"cut": "audio/sfx/click.mp3", "hook_cut": "audio/sfx/flash.mp3",
                                  "hook_extra_uy": "audio/sfx/uy.mp3", "hook_extra_gasp": "audio/sfx/gasp.mp3"}}
    t = build_timeline(clips, 4.0, 0.5, audio=audio)
    extra = {"audio/sfx/uy.mp3", "audio/sfx/gasp.mp3"}
    # tiap ganti klip di hook: camera flash + persis 1 SFX tambahan hook (volume 0,3); habis hook nggak ada
    for frame in (27, 57):
        at = [x for x in t["sfx"] if x["from"] == frame]
        assert [x["src"] for x in at if x["src"] == "audio/sfx/flash.mp3"] == ["audio/sfx/flash.mp3"]
        picked = [x for x in at if x["src"] in extra]
        assert len(picked) == 1 and picked[0]["volume"] == 0.3
    assert not [x for x in t["sfx"] if x["from"] >= 87 and x["src"] in extra]


def test_no_transition_between_shots_from_the_same_clip():
    def from_link(name, start, link, hook=None):
        return {**shot(f"clips/{name}.mp4", "video", start, 1080, 1920), "page_url": link, "hook_segment": hook}

    clips = {"shots": [from_link("h1", 0.0, "https://t/1", 0), from_link("h2", 1.0, "https://t/1", 1),
                       from_link("h3", 2.0, "https://t/2", 2), from_link("a", 3.0, "https://t/3"),
                       from_link("b", 4.0, "https://t/3"), from_link("c", 5.0, "https://t/4")]}
    audio = {"bgm": None, "sfx": {"cut": "audio/sfx/click.mp3", "hook_cut": "audio/sfx/flash.mp3"}}
    t = build_timeline(clips, 6.0, 0.5, audio=audio)
    # h1→h2 dan a→b klip yang sama: sepi. h2→h3 flash, h3→a klik, b→c klik.
    assert [(x["from"], x["src"]) for x in t["sfx"]] == [(57, "audio/sfx/flash.mp3"), (87, "audio/sfx/click.mp3"),
                                                          (147, "audio/sfx/click.mp3")]
    assert t["flashes"] == [{"from": 60, "durationInFrames": 3}]


def test_transition_sfx_only_after_hook():
    clips = {"shots": [{**shot("clips/h1.mp4", "video", 0.0, 1080, 1920), "hook_segment": 0},
                       {**shot("clips/h2.mp4", "video", 1.0, 1080, 1920), "hook_segment": 1},
                       shot("clips/a.mp4", "video", 2.0, 1080, 1920), shot("clips/b.mp4", "video", 3.0, 1080, 1920)]}
    timeline = build_timeline(clips, 4.0, 0.5, audio={"bgm": None, "sfx": {"cut": "audio/sfx/click.mp3"}})
    # pergantian di dalam hook (frame 30) sepi; masuk isi (60) dan sesudahnya (90) dapat klik, 3 frame lebih awal
    assert [(s["from"], s["src"]) for s in timeline["sfx"]] == [(57, "audio/sfx/click.mp3"), (87, "audio/sfx/click.mp3")]


ITEM_SCRIPT = {"beats": [{"text": "Look at this creature."}, {"text": "Number five, horseshoe crab."},
                         {"text": "It is old."}, {"text": "It is very old."}, {"text": "It is so old."}]}
ITEM_ALIGN = fake_alignment("Look at this creature. Number five, horseshoe crab. It is old. It is very old. It is so old.", 10.0)
ITEM_AUDIO = {"bgm": "audio/bgm/mystery.mp3", "bgm_main": "audio/bgm/main.mp3", "riser_s": 2.0,
              "sfx": {"cut": "audio/sfx/click.mp3", "subject": "audio/sfx/check.mp3", "item_reveal": "audio/sfx/reveal.mp3",
                      "riser": "audio/sfx/riser.mp3", "number": "audio/sfx/number.mp3", "extra_oof": "audio/sfx/oof.mp3",
                      "extra_punch": "audio/sfx/punch.mp3"}}


def item_timeline(audio=ITEM_AUDIO):
    """Hook 1 shot, CTA 1 shot, card #5, terus 3 klip penjelasan."""
    card = build_timeline({"shots": [shot("clips/x.mp4", "video", 0.0, 1080, 1920)]}, 10.0, 0.5,
                          script=ITEM_SCRIPT, alignment=ITEM_ALIGN)["countdown"][0]
    number_s, end_s = card["numberFrom"] / 30, (card["cardFrom"] + card["cardDuration"]) / 30
    clips = {"shots": [{**shot("clips/hook.mp4", "video", 0.0, 1080, 1920), "hook_segment": 0},
                       shot("clips/cta.mp4", "video", 1.0, 1080, 1920), shot("clips/card.mp4", "video", number_s, 1080, 1920),
                       shot("clips/p1.jpg", "photo", end_s, 1080, 1920), shot("clips/v2.mp4", "video", end_s + 1.0, 1080, 1920),
                       shot("clips/v3.mp4", "video", end_s + 2.0, 1080, 1920)]}
    return build_timeline(clips, 10.0, 0.5, script=ITEM_SCRIPT, alignment=ITEM_ALIGN, audio=audio)


def test_item_box_checks_then_first_clip_reveals_then_clicks():
    t = item_timeline()
    starts = {s["src"]: s["from"] for s in t["shots"]}
    at = lambda frame: sorted(x["src"].split("/")[-1] for x in t["sfx"] if x["from"] == frame - 3)  # noqa: E731
    card = t["countdown"][0]
    assert at(starts["clips/cta.mp4"])[0] == "click.mp3"  # setelah hook, sebelum card: klik (+acak)
    assert at(card["cardFrom"]) == ["check.mp3"]  # box foto subjek muncul pas "Number five, ..."
    assert at(starts["clips/p1.jpg"]) == ["reveal.mp3"]  # klip pertama habis card: magic reveal aja
    assert at(starts["clips/v2.mp4"])[0] == "click.mp3" and at(starts["clips/v3.mp4"])[0] == "click.mp3"
    assert t["transitions"] == [{"from": starts["clips/p1.jpg"], "durationInFrames": 7}]  # efek kayak awal video
    assert not any(x["src"].endswith(("check.mp3", "reveal.mp3", "click.mp3")) and x["from"] == starts["clips/card.mp4"] - 3
                   for x in t["sfx"])  # masuk card number nggak dapat bunyi transisi


def test_click_transitions_add_random_extra_or_nothing_the_same_way_each_time():
    clips = {"shots": [shot(f"clips/s{i}.mp4", "video", float(i), 1080, 1920) for i in range(16)]}
    audio = {"bgm": None, "sfx": {"cut": "audio/sfx/click.mp3", "extra_oof": "audio/sfx/oof.mp3",
                                  "extra_punch": "audio/sfx/punch.mp3"}}
    sfx = build_timeline(clips, 16.0, 0.5, audio=audio)["sfx"]
    clicks = {x["from"] for x in sfx if x["src"] == "audio/sfx/click.mp3"}
    extras = [x for x in sfx if x["src"] != "audio/sfx/click.mp3"]
    assert len(clicks) == 15 and {x["from"] for x in extras} <= clicks
    assert 0 < len(extras) < 15  # kadang nggak ada SFX tambahan
    assert len({x["from"] for x in extras}) == len(extras)  # maksimal 1 SFX tambahan per transisi
    assert build_timeline(clips, 16.0, 0.5, audio=audio)["sfx"] == sfx  # render ulang nggak ganti bunyi


def test_extra_sfx_lines_up_with_click_and_stays_quiet():
    clips = {"shots": [shot(f"clips/s{i}.mp4", "video", float(i), 1080, 1920) for i in range(16)]}
    audio = {"bgm": None, "sfx": {"cut": "audio/sfx/click.mp3", "extra_oof": "audio/sfx/oof.mp3",
                                  "extra_punch": "audio/sfx/punch.mp3"},
             # detik sampai bunyinya mulai kedengeran (hening di depan file)
             "sfx_onset": {"cut": 0.02, "extra_oof": 0.2, "extra_punch": 0.38}}
    sfx = build_timeline(clips, 16.0, 0.5, audio=audio)["sfx"]
    clicks = sorted(x["from"] for x in sfx if x["src"] == "audio/sfx/click.mp3")
    assert {x["volume"] for x in sfx if x["src"] == "audio/sfx/click.mp3"} == {0.4}
    oof = [x for x in sfx if x["src"] == "audio/sfx/oof.mp3"]
    punch = [x for x in sfx if x["src"] == "audio/sfx/punch.mp3"]
    assert oof and punch
    # bunyi tambahan mulai kedengeran barengan klik: digeser lebih awal sebesar selisih heningnya
    assert all(x["from"] + 5 in clicks and x["volume"] == 0.45 for x in oof)  # (0,2 - 0,02) * 30 = 5,4 -> 5 frame
    assert all(x["from"] + 11 in clicks and x["volume"] == 0.22 for x in punch)  # file punch jauh lebih keras


def test_hook_extra_lines_up_with_camera_flash():
    clips = {"shots": [{**shot("clips/h1.mp4", "video", 0.0, 1080, 1920), "hook_segment": 0},
                       {**shot("clips/h2.mp4", "video", 1.0, 1080, 1920), "hook_segment": 1},
                       shot("clips/a.mp4", "video", 2.0, 1080, 1920)]}
    audio = {"bgm": None, "sfx": {"hook_cut": "audio/sfx/flash.mp3", "hook_extra_uy": "audio/sfx/uy.mp3"},
             "sfx_onset": {"hook_cut": 0.12, "hook_extra_uy": 0.18}}
    sfx = build_timeline(clips, 3.0, 0.5, audio=audio)["sfx"]
    # flash 3 frame sebelum cut; "uy" hening 0,06 dtk lebih lama di depan -> mulai 2 frame lebih awal (urut per frame)
    assert [(x["src"], x["from"], x["volume"]) for x in sfx] == [("audio/sfx/uy.mp3", 25, 0.3),
                                                                 ("audio/sfx/flash.mp3", 27, 0.4)]


def test_bgm_switches_at_first_number_and_riser_ends_there():
    t = item_timeline()
    switch = t["countdown"][0]["numberFrom"]
    assert t["bgm"] == [
        {"src": "audio/bgm/mystery.mp3", "from": 0, "durationInFrames": switch, "volume": 0.12, "fadeOutFrames": 8},
        {"src": "audio/bgm/main.mp3", "from": switch, "durationInFrames": t["durationInFrames"] - switch,
         "volume": 0.12, "fadeOutFrames": 30},
    ]
    riser = [x for x in t["sfx"] if x["src"] == "audio/sfx/riser.mp3"]
    # riser 2 detik (bagian yang kedengeran), habis pas kartu angka pertama muncul
    assert riser == [{"src": "audio/sfx/riser.mp3", "from": switch - 60, "volume": 1.0}]


def test_single_bgm_when_main_bgm_missing():
    t = item_timeline({"bgm": "audio/bgm/mystery.mp3", "sfx": {}})
    assert t["bgm"] == [{"src": "audio/bgm/mystery.mp3", "from": 0, "durationInFrames": t["durationInFrames"],
                         "volume": 0.12, "fadeOutFrames": 30}]


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
    # Kartu + angka muncul pas "Number" kedengeran (2.8s), bukan di awal beat (2.3s) (Akmal)
    assert (card["numberFrom"], card["numberAt"], card["cardFrom"]) == (84, 0, 111)
    # whoosh api: bunyinya baru kedengeran ±9 frame, jadi dimulai 9 frame sebelum kartu
    assert timeline["sfx"] == [{"src": "audio/sfx/w.mp3", "from": 75, "volume": 0.9}]
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


def test_cta_ignores_like_meaning_similar_and_subscribers():
    for text, kinds in [("For more creatures like this, subscribe now!", ["subscribe"]),
                        ("Hit like and subscribe, subscribers get facts first!", ["like", "subscribe"])]:
        timeline = build_timeline(CTA_CLIPS, 5.0, 0.5, script={"beats": [{"text": text}]}, alignment=fake_alignment(text, 4.9))
        assert [c["kind"] for c in timeline["cta"]] == kinds, text


def test_cta_fits_before_the_video_ends():
    text = "It is old. Like and subscribe!"
    timeline = build_timeline(CTA_CLIPS, 2.5, 0.5, script={"beats": [{"text": text}]}, alignment=fake_alignment(text, 2.5))
    # subscribe di frame 50 bakal kepotong di frame 75, jadi dimajuin ke 48 biar flip terakhirnya kelihatan
    assert timeline["cta"] == [{"kind": "like", "from": 28, "durationInFrames": 16, "clickAt": 4},
                               {"kind": "subscribe", "from": 48, "durationInFrames": 27, "clickAt": 14}]


def test_emoji_word_inside_a_hyphenated_word():
    text = "Look at this prehistoric-looking fish."
    marks = {"beats": [{"point": False, "emoji": "🧐", "emoji_word": "looking"}], "emoji": {"🧐": "emoji/1f9d0.json"}}
    timeline = build_timeline(CTA_CLIPS, 5.0, 0.5, script={"beats": [{"text": text}]}, alignment=fake_alignment(text, 4.9),
                              marks=marks)
    assert timeline["emojis"][0]["from"] == 50  # di "prehistoric-looking", bukan di awal beat


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


def test_custom_sfx_from_brief_play_at_their_second():
    clips = {"shots": [shot("clips/a.mp4", "video", 0.0, 1080, 1920), shot("clips/b.mp4", "video", 2.0, 1080, 1920)]}
    audio = {"bgm": None, "sfx": {}, "custom": [{"src": "audio/sfx/uy.mp3", "at_s": 1.0, "onset": 0.1},
                                                {"src": "audio/sfx/gasp.mp3", "at_s": 0.0, "onset": 0.2}]}
    sfx = build_timeline(clips, 4.0, 0.5, audio=audio)["sfx"]
    # bunyinya kedengeran pas di detik yang dipilih: mulai lebih awal sebesar hening di depan file
    assert sfx == [{"src": "audio/sfx/gasp.mp3", "from": 0, "volume": 0.5}, {"src": "audio/sfx/uy.mp3", "from": 27, "volume": 0.5}]
