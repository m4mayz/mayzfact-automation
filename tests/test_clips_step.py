import httpx

from mayzfact.ffmpeg import probe
from mayzfact.steps.clips import run_clips
from mayzfact.store import RunPaths, read_json
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


def test_run_clips_downloads_normalizes_and_writes_credits(tmp_path, make_video, make_photo):
    files = {"/v1.mp4": make_video(1080, 1920, 5.0).read_bytes(), "/p1.jpg": make_photo(1600, 1000).read_bytes()}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=files[request.url.path])))
    paths = RunPaths(tmp_path / "run")
    paths.clips_dir.mkdir(parents=True)
    (paths.clips_dir / "shot_09.mp4").write_bytes(b"sisa run lama")

    data = run_clips(
        paths, SCRIPT, TTS, FakeSearch(), client,
        max_shot_s=2.5, fg_min_ratio=0.5, media_cache=tmp_path / "media", log=lambda message: None,
    )

    assert read_json(paths.clips_json) == data
    first, second = data["shots"]
    assert first == {
        "index": 0, "beat": 0, "start_s": 0.0, "end_s": 1.4, "kind": "video", "file": "clips/shot_01.mp4",
        "width": 1080, "height": 1920, "provider": "pexels", "provider_id": "v1",
        "page_url": "https://pexels.test/v1", "author": "tester", "query": "crab",
    }
    assert (second["file"], second["kind"], second["width"], second["height"]) == ("clips/shot_02.jpg", "photo", 1600, 1000)
    assert (second["start_s"], second["end_s"], second["provider"]) == (1.4, 3.0, "pixabay")
    assert abs(probe(paths.clips_dir / "shot_01.mp4", "clips")["duration_s"] - 1.6) < 0.1
    assert sorted(p.name for p in paths.clips_dir.iterdir()) == ["shot_01.mp4", "shot_02.jpg"]
    assert len(list((tmp_path / "media").iterdir())) == 2
