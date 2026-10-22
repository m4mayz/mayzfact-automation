import shutil

import pytest

from mayzfact.store import RunPaths, read_json
from mayzfact.textblur import PAD, merge_boxes, prepare_text_blurs, text_boxes_from_ocr


def test_ocr_result_keeps_confident_text_only():
    result = [
        ([[229, 971], [347, 971], [347, 994], [229, 994]], "fb:AzerHezye", 0.97),
        ([[10, 10], [60, 10], [60, 30], [10, 30]], "x", 0.99),  # 1 huruf: tekstur, bukan teks
        ([[100, 500], [300, 500], [300, 540], [100, 540]], "blur", 0.70),  # nggak cukup yakin
        ([[171, 553], [356, 553], [356, 729], [171, 729]], "ni", 0.95),  # kotak persegi: pola api, bukan baris teks
    ]
    boxes = text_boxes_from_ocr(result, width=576, height=1024)
    assert boxes == [pytest.approx((229 / 576, 971 / 1024, 347 / 576, 994 / 1024))]
    assert text_boxes_from_ocr(None, width=576, height=1024, min_score=0.6) == []


def test_merge_boxes_pads_and_joins_overlapping():
    merged = merge_boxes([(0.10, 0.10, 0.20, 0.12), (0.19, 0.10, 0.30, 0.12), (0.60, 0.80, 0.70, 0.85),
                          (0.99, 0.99, 1.0, 1.0)], pad=0.01)
    assert merged == [pytest.approx((0.09, 0.09, 0.31, 0.13)), pytest.approx((0.59, 0.79, 0.71, 0.86)),
                      pytest.approx((0.98, 0.98, 1.0, 1.0))]


class FakeDetector:
    def __init__(self):
        self.calls = []

    def boxes(self, image):
        self.calls.append(image)
        return [(0.4, 0.95, 0.6, 0.97)]


def test_prepare_text_blurs_samples_each_clip_and_caches(tmp_path, make_video, make_photo):
    paths = RunPaths(tmp_path / "run")
    (paths.root / "clips").mkdir(parents=True)
    shutil.copyfile(make_video(1080, 1920, 3.0), paths.root / "clips" / "shot_01.mp4")
    shutil.copyfile(make_photo(1600, 1000), paths.root / "clips" / "shot_02.jpg")
    clips = {"shots": [{"file": "clips/shot_01.mp4", "kind": "video", "start_s": 0.0, "end_s": 3.0},
                       {"file": "clips/shot_02.jpg", "kind": "photo", "start_s": 3.0, "end_s": 4.0},
                       {"file": "clips/missing.mp4", "kind": "video", "start_s": 4.0, "end_s": 5.0}]}
    detector = FakeDetector()
    out = prepare_text_blurs(paths, clips, detector, log=lambda m: None)
    assert set(out) == {"clips/shot_01.mp4", "clips/shot_02.jpg"}
    assert out["clips/shot_01.mp4"] == [pytest.approx((0.4 - PAD, 0.95 - PAD, 0.6 + PAD, 0.97 + PAD))]
    assert len(detector.calls) == 4  # video: 3 frame sampel, foto: 1
    again = FakeDetector()
    assert prepare_text_blurs(paths, clips, again, log=lambda m: None) == out and again.calls == []  # dari cache
    assert set(read_json(paths.root / "textblur.json")) == {"clips/shot_01.mp4", "clips/shot_02.jpg"}


def test_one_bad_clip_does_not_stop_the_rest(tmp_path, make_photo):
    paths = RunPaths(tmp_path / "run")
    (paths.root / "clips").mkdir(parents=True)
    shutil.copyfile(make_photo(1600, 1000), paths.root / "clips" / "a.jpg")
    shutil.copyfile(make_photo(1600, 1000), paths.root / "clips" / "b.jpg")

    class Flaky(FakeDetector):
        def boxes(self, image):
            if image.name == "a.jpg":
                raise RuntimeError("onnx rusak")
            return super().boxes(image)

    clips = {"shots": [{"file": "clips/a.jpg", "kind": "photo", "start_s": 0, "end_s": 1},
                       {"file": "clips/b.jpg", "kind": "photo", "start_s": 1, "end_s": 2}]}
    logs = []
    out = prepare_text_blurs(paths, clips, Flaky(), log=logs.append)
    assert list(out) == ["clips/b.jpg"] and any("a.jpg" in line for line in logs)
