import pytest

from mayzfact.overlay import (
    fill_points,
    prepare_overlays,
    sample_times,
    screen_box,
    shot_query,
)
from mayzfact.store import RunPaths, read_json

BEATS = [{"text": "Look at this.", "queries": ["giant bird tower"]},
         {"text": "Number five, horseshoe crab.", "queries": ["crab"]},
         {"text": "It is old.", "queries": ["fossil crab"]}]
SCRIPT = {"beats": BEATS}


def clip(index, beat, file, kind="video", w=1080, h=1920, start=0.0, end=2.0):
    return {"index": index, "beat": beat, "file": file, "kind": kind, "width": w, "height": h, "start_s": start, "end_s": end}


class FakeDetector:
    """Kotak tengah; skor dari tabel per query, biar bisa ngatur titik yang 'hilang'."""

    def __init__(self, scores=None):
        self.scores = scores or {}
        self.calls = []

    def best_box(self, image, query):
        self.calls.append((image.name, query))
        score = self.scores.get(query, [0.5])
        value = score[(len(self.calls) - 1) % len(score)]
        return value, (0.25, 0.25, 0.75, 0.75)


def test_screen_box_full_and_blur():
    # full: klip 1080x1920 langsung pas layar
    assert screen_box((0.25, 0.25, 0.75, 0.75), 1080, 1920, fg_min_ratio=0.5) == (270, 480, 540, 960)
    # blur: klip 1920x1080 → kotak foreground 1080x960 (min 0.5×1920) di tengah, cover di dalamnya
    x, y, w, h = screen_box((0.0, 0.0, 1.0, 1.0), 1920, 1080, fg_min_ratio=0.5)
    assert (y, h) == (480, 960) and x < 0 and x + w > 1080


def test_fill_points_and_half_rule():
    a, b = {"t": 0.5, "x": 1}, {"t": 2.5, "x": 3}
    filled = fill_points([None, a, None, b])
    assert [p["x"] for p in filled] == [1, 1, 1, 3]
    assert fill_points([None, None, a]) is None
    assert fill_points([]) is None


def test_sample_times():
    assert sample_times("video", 2.2) == [0.5, 1.5]
    assert sample_times("video", 0.4) == [0.2]
    assert sample_times("photo", 3.0) == [0.0]


def test_shot_query_prefers_subject_then_plan_then_queries():
    subjects = [None, "horseshoe crab", "horseshoe crab"]
    plan = {"shots": [{"index": 0, "keywords": {"en": ["giant bird on tower"], "zh": []}}]}
    # Keyword panjang bikin OWLv2 nangkep benda lain (contoh: menara, bukan burung) → cukup 2 kata pertama.
    assert shot_query(clip(0, 0, "a"), BEATS, subjects, plan) == "giant bird"
    assert shot_query(clip(0, 0, "a"), BEATS, subjects, None) == "giant bird"
    assert shot_query(clip(2, 2, "c"), BEATS, subjects, plan) == "horseshoe crab"


def test_prepare_overlays_detects_caches_and_skips_cards(tmp_path, make_video):
    paths = RunPaths(tmp_path / "run")
    (paths.root / "clips").mkdir(parents=True)
    import shutil

    shutil.copy(make_video(1080, 1920, 2.2), paths.root / "clips" / "shot_01.mp4")
    shutil.copy(make_video(1080, 1920, 2.2), paths.root / "clips" / "shot_02.mp4")
    shutil.copy(make_video(1080, 1920, 2.2), paths.root / "clips" / "shot_03.mp4")
    clips = {"shots": [clip(0, 0, "clips/shot_01.mp4"), clip(1, 1, "clips/shot_02.mp4", start=2.0, end=4.0),
                       clip(2, 2, "clips/shot_03.mp4", start=4.0, end=6.0)]}
    detector = FakeDetector({"fossil crab": [0.5, 0.05]})
    logs = []
    out = prepare_overlays(paths, clips, SCRIPT, None, detector, fg_min_ratio=0.5, log=logs.append)
    assert "clips/shot_02.mp4" not in out  # beat countdown ketutup card
    assert out["clips/shot_01.mp4"]["points"][0] == {"t": 0.5, "x": 270, "y": 480, "w": 540, "h": 960}
    assert [p["t"] for p in out["clips/shot_01.mp4"]["points"]] == [0.5, 1.5]
    assert out["clips/shot_03.mp4"]["points"] is not None  # 1 dari 2 titik valid = 50%, masih lolos
    assert read_json(paths.root / "overlays.json")["clips/shot_01.mp4"]["key"].endswith("giant bird")
    calls = len(detector.calls)
    prepare_overlays(paths, clips, SCRIPT, None, detector, fg_min_ratio=0.5, log=logs.append)
    assert len(detector.calls) == calls  # cache kepakai


def test_prepare_overlays_drops_undetected_shot(tmp_path, make_video):
    paths = RunPaths(tmp_path / "run")
    (paths.root / "clips").mkdir(parents=True)
    import shutil

    shutil.copy(make_video(1080, 1920, 2.2), paths.root / "clips" / "shot_01.mp4")
    clips = {"shots": [clip(0, 0, "clips/shot_01.mp4")]}
    out = prepare_overlays(paths, clips, SCRIPT, None, FakeDetector({"giant bird": [0.01]}),
                           fg_min_ratio=0.5, log=lambda m: None)
    assert out["clips/shot_01.mp4"]["points"] is None


@pytest.mark.clip
def test_owlv2_finds_a_red_square(tmp_path):
    from PIL import Image, ImageDraw

    from mayzfact.detect import Owlv2Detector

    image = tmp_path / "a.jpg"
    canvas = Image.new("RGB", (640, 640), "white")
    ImageDraw.Draw(canvas).rectangle([320, 320, 560, 560], fill="red")
    canvas.save(image)
    score, (x0, y0, x1, y1) = Owlv2Detector().best_box(image, "a red square")
    assert score > 0.1 and x0 > 0.4 and y0 > 0.4
