from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from mayzfact.embed import unit
from mayzfact.errors import AwaitingInput
from mayzfact.ffmpeg import probe
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


def test_single_hook_video_plays_continuously(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"groups": {"hook": [{"url": "https://www.douyin.com/video/1"}],
                                             "horseshoe-crab": [{"url": "https://x.com/post"}]}})
    files = {"https://www.douyin.com/video/1": [cut_video], "https://x.com/post": photos(tmp_path, "other", "crab")}
    data = run_fetch(paths, plan, obtain=lambda e, r: files[e["url"]], encoder=FakeEncoder(), **QUIET)
    hook, third, fourth = data["shots"]
    # 1 klip nyambung buat shot 1-2. Mulai di detik 0.5: frame detik 1.0 (= ref) jatuh di tengah shot 2.
    assert (hook["start_s"], hook["end_s"], hook["file"], hook["source_s"]) == (0.0, 0.6, "clips/shot_01.mp4", 0.5)
    assert (hook["kind"], hook["provider"], hook["match"], hook["hook_segment"]) == ("video", "douyin", 0.5, 0)
    assert abs(probe(paths.root / hook["file"], "t")["duration_s"] - 0.8) < 0.1
    assert (third["page_url"], third["match"]) == ("https://x.com/post", 1.0)
    assert fourth["match"] == 0.0 and fourth["query"] == "manual"
    status = read_json(paths.links_status_json)["groups"]
    assert status["hook"]["state"] == "ok" and status["horseshoe-crab"]["state"] == "ok"
    assert read_json(paths.clips_json) == data

    save_links(paths.links_json, {"groups": {"hook": [{"url": "https://www.douyin.com/video/1"}, {"url": "https://a.b/2"}],
                                             "horseshoe-crab": [{"url": "https://x.com/post"}]}})
    files["https://a.b/2"] = [cut_video]
    data = run_fetch(paths, plan, obtain=lambda e, r: files[e["url"]], encoder=FakeEncoder(), **QUIET)
    assert [s["file"] for s in data["shots"]][:2] == ["clips/shot_01.mp4", "clips/shot_02.mp4"]


def test_content_video_shots_do_not_overlap(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    plan["groups"] = plan["groups"][1:]
    plan["shots"] = [{**plan["shots"][2], "start_s": 0.6, "end_s": 0.9}, {**plan["shots"][3], "start_s": 0.9, "end_s": 1.2}]
    save_links(paths.links_json, {"groups": {"horseshoe-crab": [{"url": "https://www.douyin.com/video/1"}]}})
    data = run_fetch(paths, plan, obtain=lambda e, r: [cut_video], encoder=FakeEncoder(), **QUIET)
    first, second = data["shots"]
    assert first["kind"] == second["kind"] == "video"
    assert second["source_s"] + 0.5 <= first["source_s"] or second["source_s"] >= first["source_s"] + 0.5
    assert "tambah link" not in read_json(paths.links_status_json)["groups"]["horseshoe-crab"]["message"]


def test_used_clip_is_never_shown_again(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    plan["groups"] = plan["groups"][1:]
    plan["shots"] = plan["shots"][2:]
    save_links(paths.links_json, {"groups": {"horseshoe-crab": [{"url": "https://a.b/one"}]}})
    one = photos(tmp_path, "crab")
    with pytest.raises(AwaitingInput, match="horseshoe crab"):
        run_fetch(paths, plan, obtain=lambda e, r: one, encoder=FakeEncoder(), **QUIET)
    status = read_json(paths.links_status_json)["groups"]["horseshoe-crab"]
    assert status["state"] == "error" and "tambah link" in status["message"]

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
    plan["groups"][0]["shots"] = [2]
    plan["shots"] = plan["shots"][:1]
    save_links(paths.links_json, {"groups": {"horseshoe-crab": [{"url": "https://a.b/p", "pick": 1}]}})
    data = run_fetch(paths, plan, obtain=lambda e, r: photos(tmp_path, "other", "crab"), encoder=FakeEncoder(), **QUIET)
    assert [s["match"] for s in data["shots"]] == [0.0]


def test_each_shot_prefers_a_video_not_used_yet(tmp_path, cut_video):
    import shutil

    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    plan["groups"] = plan["groups"][1:]
    plan["shots"] = [{**plan["shots"][2], "start_s": 0.6, "end_s": 0.9}, {**plan["shots"][3], "start_s": 0.9, "end_s": 1.2}]
    other = shutil.copyfile(cut_video, tmp_path / "other.mp4")
    files = {"https://a.b/one": [cut_video], "https://a.b/two": [other]}
    save_links(paths.links_json, {"groups": {"horseshoe-crab": [{"url": "https://a.b/one"}, {"url": "https://a.b/two"}]}})
    data = run_fetch(paths, plan, obtain=lambda e, r: files[e["url"]], encoder=FakeEncoder(), **QUIET)
    assert [s["page_url"] for s in data["shots"]] == ["https://a.b/one", "https://a.b/two"]


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


def test_clip_used_in_earlier_group_is_not_shown_again(tmp_path):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    plan["groups"] = [{"id": "a", "label": "A", "shots": [2]}, {"id": "b", "label": "B", "shots": [3]}]
    plan["shots"] = plan["shots"][2:]
    same = photos(tmp_path, "crab")
    save_links(paths.links_json, {"groups": {"a": [{"url": "https://a.b/p"}], "b": [{"url": "https://a.b/p"}]}})
    with pytest.raises(AwaitingInput, match="B"):
        run_fetch(paths, plan, obtain=lambda e, r: same, encoder=FakeEncoder(), **QUIET)
    status = read_json(paths.links_status_json)["groups"]
    assert status["a"]["state"] == "ok" and status["b"]["state"] == "error"


def test_progress_write_failure_never_breaks_fetch(tmp_path, cut_video, monkeypatch):
    import mayzfact.steps.fetch as fetch_mod

    real = fetch_mod.write_json_atomic

    def locked(path, data):
        if path.name == "fetch_progress.json":
            raise PermissionError(13, "dibaca brief server")
        real(path, data)

    monkeypatch.setattr(fetch_mod, "write_json_atomic", locked)
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"groups": {"hook": [{"url": "https://www.douyin.com/video/1"}],
                                             "horseshoe-crab": [{"url": "https://x.com/post"}]}})
    files = {"https://www.douyin.com/video/1": [cut_video], "https://x.com/post": photos(tmp_path, "other", "crab")}
    data = run_fetch(paths, plan, obtain=lambda e, r: files[e["url"]], encoder=FakeEncoder(), **QUIET)
    assert len(data["shots"]) == 3
    assert all(s["state"] == "ok" for s in read_json(paths.links_status_json)["groups"].values())


def test_progress_marked_failed_when_fetch_crashes(tmp_path, monkeypatch):
    import mayzfact.steps.fetch as fetch_mod

    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    save_links(paths.links_json, {"groups": {"hook": [{"url": "https://a.b/v"}]}})

    def boom(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(fetch_mod, "_run_group", boom)
    with pytest.raises(KeyboardInterrupt):
        run_fetch(paths, plan, obtain=lambda e, r: [], encoder=FakeEncoder(), **QUIET)
    assert read_json(paths.fetch_progress_json)["state"] == "failed"


def test_fetch_with_shots_dict(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    # 4 shots: 0, 1, 2, 3
    save_links(paths.links_json, {"shots": {
        "0": {"url": "https://www.douyin.com/video/1"},
        "1": {"url": "https://www.douyin.com/video/1"},
        "2": {"url": "https://x.com/post"},
    }})
    files = {"https://www.douyin.com/video/1": [cut_video], "https://x.com/post": photos(tmp_path, "other", "crab")}
    with pytest.raises(AwaitingInput, match="horseshoe crab|shot 4"):
        run_fetch(paths, plan, obtain=lambda e, r: files[e["url"]], encoder=FakeEncoder(), **QUIET)
    status = read_json(paths.links_status_json)
    assert status["shots"]["3"]["state"] == "missing"

    save_links(paths.links_json, {"shots": {
        "0": {"url": "https://www.douyin.com/video/1"},
        "1": {"url": "https://www.douyin.com/video/1"},
        "2": {"url": "https://x.com/post"},
        "3": {"url": "https://x.com/post2"},
    }})
    files["https://x.com/post2"] = photos(tmp_path, "good")
    data = run_fetch(paths, plan, obtain=lambda e, r: files[e["url"]], encoder=FakeEncoder(), **QUIET)
    assert len(data["shots"]) >= 3
    status = read_json(paths.links_status_json)
    assert all(s["state"] == "ok" for s in status["shots"].values())


def test_consecutive_shots_with_same_video_play_continuously(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    plan["groups"] = [{"id": "content", "label": "content", "shots": [2, 3]}]
    plan["shots"] = [
        {**plan["shots"][2], "start_s": 0.0, "end_s": 0.4, "media": "video"},
        {**plan["shots"][3], "start_s": 0.4, "end_s": 0.8, "media": "video"},
    ]
    save_links(paths.links_json, {"shots": {
        "2": {"url": "https://a.b/video"},
        "3": {"url": "https://a.b/video"},
    }})
    data = run_fetch(paths, plan, obtain=lambda e, r: [cut_video], encoder=FakeEncoder(), **QUIET)
    s2, s3 = data["shots"]
    assert abs(s3["source_s"] - (s2["source_s"] + 0.4)) < 1e-3


def test_same_link_continues_after_shot_with_start_time(tmp_path, cut_video):
    """Shot pertama diisi @detik, shot berikutnya link sama tanpa detik: lanjut nyambung dari situ, bukan milih sendiri."""
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    plan["groups"] = [{"id": "content", "label": "content", "shots": [2, 3]}]
    plan["shots"] = [
        {**plan["shots"][2], "start_s": 0.0, "end_s": 0.4, "media": "video"},
        {**plan["shots"][3], "start_s": 0.4, "end_s": 0.8, "media": "video"},
    ]
    save_links(paths.links_json, {"shots": {
        "2": {"url": "https://a.b/video", "start_s": 0.5},
        "3": {"url": "https://a.b/video"},
    }})
    data = run_fetch(paths, plan, obtain=lambda e, r: [cut_video], encoder=FakeEncoder(), **QUIET)
    s2, s3 = data["shots"]
    assert abs(s2["source_s"] - 0.5) < 1e-3
    assert abs(s3["source_s"] - 0.9) < 1e-3


def test_same_link_continues_across_groups(tmp_path, cut_video):
    """Shot terakhir hook dan shot pertama kelompok berikutnya pakai link sama: tetap nyambung, nggak direset per kelompok."""
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    plan["groups"] = [{"id": "a", "label": "a", "shots": [2]}, {"id": "b", "label": "b", "shots": [3]}]
    plan["shots"] = [
        {**plan["shots"][2], "start_s": 0.0, "end_s": 0.4, "media": "video", "group": "a"},
        {**plan["shots"][3], "start_s": 0.4, "end_s": 0.8, "media": "video", "group": "b"},
    ]
    save_links(paths.links_json, {"shots": {
        "2": {"url": "https://a.b/video", "start_s": 0.5},
        "3": {"url": "https://a.b/video"},
    }})
    data = run_fetch(paths, plan, obtain=lambda e, r: [cut_video], encoder=FakeEncoder(), **QUIET)
    s2, s3 = data["shots"]
    assert abs(s3["source_s"] - (s2["source_s"] + 0.4)) < 1e-3


def test_fetch_with_custom_timestamp_override(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "run")
    plan = make_plan(paths)
    plan["groups"] = [{"id": "content", "label": "content", "shots": [2]}]
    plan["shots"] = [
        {**plan["shots"][2], "start_s": 0.0, "end_s": 0.4, "media": "video"},
    ]
    # Tentukan custom timestamp 0.3s
    save_links(paths.links_json, {"shots": {
        "2": {"url": "https://a.b/video", "start_s": 0.3},
    }})
    data = run_fetch(paths, plan, obtain=lambda e, r: [cut_video], encoder=FakeEncoder(), **QUIET)
    s2 = data["shots"][0]
    assert abs(s2["source_s"] - 0.3) < 1e-3


def test_target_prefers_action_keywords(tmp_path):
    from mayzfact.steps.fetch import _target

    class RecordingEncoder:
        def __init__(self):
            self.encoded_texts = []

        def texts(self, t):
            self.encoded_texts.extend(t)
            return unit(np.ones((len(t), 3), dtype=np.float32))

    encoder = RecordingEncoder()
    paths = RunPaths(tmp_path / "run")
    s = shot(0, 0.0, 1.0, "g", subject="vulture")
    s["keywords"]["en"] = ["vulture dropping bone from sky"]
    _target(s, paths, encoder)
    # Harus meng-encode keywords visual, bukan cuma subject
    assert "vulture dropping bone from sky" in encoder.encoded_texts


def test_target_uses_reference_frames_only_for_hook_shots(tmp_path):
    """Semua shot sekarang punya ref_frames (buat Akmal), tapi cuma hook yang dicocokin pakai gambar source."""
    from mayzfact.steps.fetch import LOW_IMAGE_SCORE, LOW_TEXT_SCORE, _target

    class RecordingEncoder:
        def __init__(self):
            self.encoded_texts, self.encoded_images = [], []

        def texts(self, t):
            self.encoded_texts.extend(t)
            return unit(np.ones((len(t), 3), dtype=np.float32))

        def images(self, files):
            self.encoded_images.extend(files)
            return unit(np.ones((len(files), 3), dtype=np.float32))

    paths = RunPaths(tmp_path / "run")
    make_plan(paths)
    encoder = RecordingEncoder()
    content = shot(2, 0.6, 1.6, "horseshoe-crab", subject="horseshoe crab")
    content["ref_frames"] = ["plan/seg_02_0.jpg", "plan/seg_02_1.jpg", "plan/seg_02_2.jpg"]
    content["keywords"]["en"] = ["horseshoe crab on beach"]
    _, low = _target(content, paths, encoder)
    assert encoder.encoded_images == [] and encoder.encoded_texts == ["horseshoe crab on beach"] and low == LOW_TEXT_SCORE

    hook = shot(0, 0.0, 0.3, "hook", hook=0)
    _, low = _target(hook, paths, encoder)
    assert len(encoder.encoded_images) == 3 and low == LOW_IMAGE_SCORE


def test_normalize_local_clamps_offset_and_rejects_short_video(tmp_path, make_video):
    import pytest

    from mayzfact.errors import PipelineError
    from mayzfact.steps.fetch import normalize_local

    paths = RunPaths(tmp_path / "run")
    out = normalize_local(2, 4.0, 6.0, make_video(1080, 1920, 5.0), "video", 4.9, paths, 0.5)
    assert out["file"] == "clips/shot_03.mp4" and out["kind"] == "video"
    assert abs(probe(paths.root / out["file"], "clips")["duration_s"] - 2.2) < 0.1
    with pytest.raises(PipelineError, match="cuma"):
        normalize_local(0, 0.0, 3.0, make_video(1080, 1920, 1.0), "video", 0.0, paths, 0.5)
