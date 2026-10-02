import shutil

import httpx

from mayzfact.ffmpeg import probe
from mayzfact.steps.clips import run_clips
from mayzfact.store import RunPaths
from tests.factories import cand, fake_alignment

SCRIPT = {
    "beats": [
        {"text": "Look at this.", "media": "video", "queries": ["crab"]},
        {"text": "It is old.", "media": "photo", "queries": ["fossil"]},
    ],
    "fallback_query": "animals",
}
TTS = {"duration_s": 3.0, "alignment": fake_alignment("Look at this. It is old.", 2.4)}


class FakeSearch:
    def candidates(self, kind, query):
        if (kind, query) == ("video", "crab"):
            return [cand("pexels", "v1", "video", 1080, 1920, duration_s=10.0, url="https://cdn.test/v1.mp4")]
        if (kind, query) == ("photo", "fossil"):
            return [cand("pixabay", "p1", "photo", 1600, 1000, url="https://cdn.test/p1.jpg")]
        return []


def hook_data(winner_file):
    return {"hook_seconds": 10.0, "skipped_platforms": [], "segments": [
        {"index": 0, "start_s": 0.0, "end_s": 1.9, "queries": {}, "candidates": [], "winner": None},
        {"index": 1, "start_s": 1.9, "end_s": 3.0, "queries": {}, "candidates": [], "winner": {
            "source": "tiktok", "provider": "tiktok", "provider_id": "w1", "kind": "video", "file": winner_file,
            "offset_s": 3.0, "score": 0.93, "label": "exact", "page_url": "https://www.tiktok.com/@a/video/w1", "author": "a",
        }},
    ]}


def run(tmp_path, make_video, make_photo, winner_seconds, logs):
    files = {"/v1.mp4": make_video(1080, 1920, 5.0).read_bytes(), "/p1.jpg": make_photo(1600, 1000).read_bytes()}
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=files[r.url.path])))
    paths = RunPaths(tmp_path / "run")
    (paths.root / "hook").mkdir(parents=True)
    shutil.copyfile(make_video(1080, 1920, winner_seconds), paths.root / "hook" / "winner_02.mp4")
    data = run_clips(
        paths, SCRIPT, TTS, FakeSearch(), client, max_shot_s=2.5, fg_min_ratio=0.5,
        media_cache=tmp_path / "media", log=logs.append, hook=hook_data("hook/winner_02.mp4"), hook_seconds=10.0,
    )
    return paths, data


def test_hook_winner_fills_first_shot(tmp_path, make_video, make_photo):
    paths, data = run(tmp_path, make_video, make_photo, 5.0, [])
    first, second = data["shots"]
    assert (first["provider"], first["provider_id"], first["hook_segment"], first["match"]) == ("tiktok", "w1", 1, "exact")
    assert first["query"] == "hook:1"
    assert first["file"] == "clips/shot_01.mp4"
    assert abs(probe(paths.root / first["file"], "clips")["duration_s"] - 1.6) < 0.1
    assert second["provider"] == "pixabay"


def test_short_hook_video_falls_back_to_stock(tmp_path, make_video, make_photo):
    logs = []
    _, data = run(tmp_path, make_video, make_photo, 1.0, logs)
    assert data["shots"][0]["provider"] == "pexels"
    assert "hook_segment" not in data["shots"][0]
    assert any("gagal dipakai" in line for line in logs)
