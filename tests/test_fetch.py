from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from mayzfact.embed import unit
from mayzfact.errors import AwaitingInput
from mayzfact.manual.links import save_links
from mayzfact.steps.fetch import run_fetch
from mayzfact.store import RunPaths, read_json

E = np.eye(3, dtype=np.float32)


class FakeEncoder:
    """Gambar: vektor dari nama file. Frame video f_0003 = E0, lainnya E2. Teks 'crab' = E1."""

    def images(self, paths):
        out = []
        for p in map(Path, paths):
            if p.name.startswith("seg_") or p.stem in {"good", "f_0003"}:
                out.append(E[0])
            elif p.stem == "crab":
                out.append(E[1])
            else:
                out.append(E[2])
        return unit(np.stack(out))

    def texts(self, texts):
        return unit(np.stack([E[1] if "crab" in t else E[2] for t in texts]))


def make_plan(paths):
    (paths.root / "plan").mkdir(parents=True)
    for k in range(3):
        Image.new("RGB", (8, 8)).save(paths.root / "plan" / f"seg_01_{k}.jpg")
    return {"shots": [
        {"index": 0, "beat": 0, "start_s": 0.0, "end_s": 1.5, "media": "video", "text": "Look.", "subject": None,
         "hook_segment": 0, "ref_frames": [f"plan/seg_01_{k}.jpg" for k in range(3)], "keywords": {"en": [], "zh": []}},
        {"index": 1, "beat": 1, "start_s": 1.5, "end_s": 3.0, "media": "photo", "text": "Number five, horseshoe crab.",
         "subject": "horseshoe crab", "hook_segment": None, "ref_frames": [], "keywords": {"en": ["crab"], "zh": []}},
    ]}


def photos(tmp_path, *names):
    out = []
    for name in names:
        path = tmp_path / "media" / f"{name}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1200, 800), "white").save(path)
        out.append(path)
    return out


def test_missing_links_stop_with_awaiting_input(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"shots": {"1": {"url": "https://a.b/v.mp4"}}})
    with pytest.raises(AwaitingInput, match="2"):
        run_fetch(paths, plan, obtain=lambda e, r: [], encoder=FakeEncoder(), fg_min_ratio=0.5, log=lambda m: None)
    status = read_json(paths.links_status_json)["shots"]
    assert status["2"]["state"] == "missing"
    assert not paths.clips_json.exists()


def test_fetch_picks_best_video_offset_and_best_photo(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"shots": {"1": {"url": "https://www.douyin.com/video/1"}, "2": {"url": "https://x.com/post"}}})
    files = {"https://www.douyin.com/video/1": [cut_video], "https://x.com/post": photos(tmp_path, "other", "crab")}
    data = run_fetch(paths, plan, obtain=lambda e, r: files[e["url"]], encoder=FakeEncoder(), fg_min_ratio=0.5, log=lambda m: None)
    first, second = data["shots"]
    assert (first["kind"], first["provider"], first["hook_segment"], first["match"]) == ("video", "douyin", 0, 1.0)
    assert (second["kind"], second["provider"], second["query"]) == ("photo", "other", "manual")
    assert second["match"] == 1.0
    assert read_json(paths.clips_json) == data
    assert read_json(paths.links_status_json)["shots"]["2"]["state"] == "ok"


def test_pick_number_and_errors_are_reported(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"shots": {"1": {"url": "https://a.b/p", "pick": 5}, "2": {"url": "https://a.b/q", "pick": 1}}})
    two = photos(tmp_path, "other", "crab")
    with pytest.raises(AwaitingInput, match="1"):
        run_fetch(paths, plan, obtain=lambda e, r: two, encoder=FakeEncoder(), fg_min_ratio=0.5, log=lambda m: None)
    status = read_json(paths.links_status_json)["shots"]
    assert status["1"]["state"] == "error" and "#5" in status["1"]["message"]
    assert status["2"]["state"] == "ok" and "skor rendah" in status["2"]["message"]


def test_same_link_in_two_shots_gets_two_clips(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"shots": {"1": {"url": "https://a.b/p"}, "2": {"url": "https://a.b/p"}}})
    shared = photos(tmp_path, "good", "crab")
    data = run_fetch(paths, plan, obtain=lambda e, r: shared, encoder=FakeEncoder(), fg_min_ratio=0.5, log=lambda m: None)
    assert [s["file"] for s in data["shots"]] == ["clips/shot_01.jpg", "clips/shot_02.jpg"]
