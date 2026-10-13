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
QUIET = {"fg_min_ratio": 0.5, "log": lambda m: None}


class FakeEncoder:
    """Gambar: vektor dari nama file. Ref hook, 'good', dan frame video f_0003 (detik 1.0) = E0; 'crab' = E1; lainnya E2."""

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


def shot(index, start, end, group, *, hook=None, subject=None, media="video"):
    refs = [f"plan/seg_{hook + 1:02d}_{k}.jpg" for k in range(3)] if hook is not None else []
    return {"index": index, "beat": index, "start_s": start, "end_s": end, "media": media, "text": f"shot {index}",
            "subject": subject, "hook_segment": hook, "ref_frames": refs, "keywords": {"en": [], "zh": []}, "group": group}


def make_plan(paths):
    (paths.root / "plan").mkdir(parents=True)
    for seg in (1, 2):
        for k in range(3):
            Image.new("RGB", (8, 8)).save(paths.root / "plan" / f"seg_{seg:02d}_{k}.jpg")
    return {
        "groups": [{"id": "hook", "label": "HOOK", "shots": [0, 1]},
                   {"id": "horseshoe-crab", "label": "horseshoe crab", "shots": [2, 3]}],
        "shots": [shot(0, 0.0, 0.3, "hook", hook=0), shot(1, 0.3, 0.6, "hook", hook=1),
                  shot(2, 0.6, 1.6, "horseshoe-crab", subject="horseshoe crab", media="photo"),
                  shot(3, 1.6, 2.6, "horseshoe-crab", subject="horseshoe crab", media="photo")],
    }


def photos(tmp_path, *names):
    out = []
    for name in names:
        path = tmp_path / "media" / f"{name}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1200, 800), "white").save(path)
        out.append(path)
    return out


def test_missing_group_stops_with_awaiting_input(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"groups": {"hook": [{"url": "https://a.b/v.mp4"}]}})
    with pytest.raises(AwaitingInput, match="horseshoe crab"):
        run_fetch(paths, plan, obtain=lambda e, r: [], encoder=FakeEncoder(), **QUIET)
    assert read_json(paths.links_status_json)["groups"]["horseshoe-crab"]["state"] == "missing"
    assert not paths.clips_json.exists()


def test_one_video_feeds_several_shots_without_overlap(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"groups": {"hook": [{"url": "https://www.douyin.com/video/1"}],
                                             "horseshoe-crab": [{"url": "https://x.com/post"}]}})
    files = {"https://www.douyin.com/video/1": [cut_video], "https://x.com/post": photos(tmp_path, "other", "crab")}
    data = run_fetch(paths, plan, obtain=lambda e, r: files[e["url"]], encoder=FakeEncoder(), **QUIET)
    first, second, third, fourth = data["shots"]
    assert (first["kind"], first["provider"], first["match"], first["source_s"]) == ("video", "douyin", 1.0, 0.85)
    assert second["kind"] == "video" and second["hook_segment"] == 1
    assert second["source_s"] + 0.5 <= first["source_s"] or second["source_s"] >= first["source_s"] + 0.5
    assert (third["page_url"], third["match"]) == ("https://x.com/post", 1.0)
    assert fourth["match"] == 0.0 and fourth["query"] == "manual"
    assert [s["file"] for s in data["shots"]] == ["clips/shot_01.mp4", "clips/shot_02.mp4", "clips/shot_03.jpg", "clips/shot_04.jpg"]
    status = read_json(paths.links_status_json)["groups"]
    assert status["hook"]["state"] == "ok" and status["horseshoe-crab"]["state"] == "ok"
    assert read_json(paths.clips_json) == data


def test_several_links_are_shared_and_reuse_warns(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    plan["groups"] = plan["groups"][1:]
    plan["shots"] = plan["shots"][2:]
    save_links(paths.links_json, {"groups": {"horseshoe-crab": [{"url": "https://a.b/one"}]}})
    one = photos(tmp_path, "crab")
    data = run_fetch(paths, plan, obtain=lambda e, r: one, encoder=FakeEncoder(), **QUIET)
    assert [s["match"] for s in data["shots"]] == [1.0, 1.0]
    assert "tambah link" in read_json(paths.links_status_json)["groups"]["horseshoe-crab"]["message"]

    save_links(paths.links_json, {"groups": {"horseshoe-crab": [{"url": "https://a.b/one"}, {"url": "https://a.b/two"}]}})
    files = {"https://a.b/one": photos(tmp_path, "crab"), "https://a.b/two": photos(tmp_path, "good")}
    data = run_fetch(paths, plan, obtain=lambda e, r: files[e["url"]], encoder=FakeEncoder(), **QUIET)
    assert [s["page_url"] for s in data["shots"]] == ["https://a.b/one", "https://a.b/two"]
    assert "tambah link" not in read_json(paths.links_status_json)["groups"]["horseshoe-crab"]["message"]


def test_pick_and_failing_line_mark_group_error(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"groups": {"hook": [{"url": "https://a.b/ok"}, {"url": "https://a.b/p", "pick": 5}],
                                             "horseshoe-crab": [{"url": "https://a.b/boom"}]}})

    def obtain(entry, root):
        if entry["url"].endswith("boom"):
            raise RuntimeError("boom")
        return photos(tmp_path, "other", "crab")

    with pytest.raises(AwaitingInput, match="HOOK"):
        run_fetch(paths, plan, obtain=obtain, encoder=FakeEncoder(), **QUIET)
    status = read_json(paths.links_status_json)["groups"]
    assert status["hook"]["state"] == "error" and "baris 2" in status["hook"]["message"] and "#5" in status["hook"]["message"]
    assert status["horseshoe-crab"]["state"] == "error" and "boom" in status["horseshoe-crab"]["message"]


def test_pick_limits_post_to_one_photo(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    plan["groups"] = plan["groups"][1:]
    plan["shots"] = plan["shots"][2:]
    save_links(paths.links_json, {"groups": {"horseshoe-crab": [{"url": "https://a.b/p", "pick": 1}]}})
    data = run_fetch(paths, plan, obtain=lambda e, r: photos(tmp_path, "other", "crab"), encoder=FakeEncoder(), **QUIET)
    assert [s["match"] for s in data["shots"]] == [0.0, 0.0]


def test_fetch_writes_progress_file(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"groups": {"hook": [{"url": "https://www.douyin.com/video/1"}]}})
    with pytest.raises(AwaitingInput):
        run_fetch(paths, plan, obtain=lambda e, r: [cut_video], encoder=FakeEncoder(), **QUIET)
    progress = read_json(paths.fetch_progress_json)
    assert progress["state"] == "awaiting"
    assert (progress["links_done"], progress["links_total"]) == (1, 1)
    assert (progress["shots_done"], progress["shots_total"]) == (2, 4)
    assert any("shot 1" in line for line in progress["log"])

    save_links(paths.links_json, {"groups": {"hook": [{"url": "https://www.douyin.com/video/1"}],
                                             "horseshoe-crab": [{"url": "https://x.com/post"}]}})
    files = {"https://www.douyin.com/video/1": [cut_video], "https://x.com/post": photos(tmp_path, "other", "crab")}
    run_fetch(paths, plan, obtain=lambda e, r: files[e["url"]], encoder=FakeEncoder(), **QUIET)
    progress = read_json(paths.fetch_progress_json)
    assert progress["state"] == "done" and progress["shots_done"] == 4 and progress["current"] == ""
