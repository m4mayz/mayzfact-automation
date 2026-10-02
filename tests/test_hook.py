import shutil
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from mayzfact.embed import unit
from mayzfact.platforms.base import PlatformBlocked
from mayzfact.steps.hook import HookDeps, run_hook
from mayzfact.store import RunPaths, read_json
from tests.factories import cand

E = np.eye(4, dtype=np.float32)
SEGMENT_VECTORS = {1: E[0], 2: E[1]}
TABLE = {
    "tiktok_t1": E[0],
    "tiktok_t2": unit(0.6 * E[0] + 0.8 * E[2]),
    "pexels_p1": unit(0.8 * E[0] + 0.6 * E[3]),
    "pexels_photo_p1": unit(0.8 * E[0] + 0.6 * E[3]),
    "tiktok_n1": unit(0.9 * E[1] + 0.43589 * E[2]),
}
SOURCE = {"video_id": "abc", "duration_s": 2.0, "transcript": [{"text": "five ancient creatures", "start": 0.0, "duration": 2.0}]}


class FakeEncoder:
    """Vektor ditentuin dari nama file: frame segmen, frame verifikasi, thumbnail, atau foto."""

    def images(self, paths):
        return unit(np.stack([self._vector(Path(p)) for p in paths]))

    def texts(self, texts):
        raise AssertionError("hook nggak pakai teks")

    def _vector(self, path):
        if path.name.startswith("seg_"):
            return SEGMENT_VECTORS[int(path.name[4:6])]
        if path.parent.parent.name == "verify":
            return TABLE[path.parent.name] if path.stem == "f_0003" else E[3]
        return TABLE[path.stem]


class FakeSearcher:
    def __init__(self, name, language, results, *, video, photo, blocked=False):
        self.name, self.language = name, language
        self.results, self.video, self.photo, self.blocked = results, video, photo, blocked
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        if self.blocked:
            raise PlatformBlocked(self.name, "captcha/login")
        return list(self.results.get(query, []))

    def download(self, candidate, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.video if candidate.kind == "video" else self.photo, dest)
        return dest


def make_deps(tmp_path, cut_video, make_photo, searchers, queries):
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()
    downloads = []

    def fetch_thumb(candidate):
        path = thumbs / f"{candidate.provider}_{candidate.id}.jpg"
        if candidate.id == "bad":
            path.write_bytes(b"<html>403</html>")
        else:
            Image.new("RGB", (8, 8)).save(path)
        return path

    def download_source(video_id, dest):
        downloads.append(video_id)
        shutil.copyfile(cut_video, dest)
        return dest

    deps = HookDeps(
        download_source=download_source,
        encoder=FakeEncoder(),
        describe=lambda infos, frames: queries,
        searchers=searchers,
        fetch_thumb=fetch_thumb,
        log=lambda message: None,
    )
    return deps, downloads


def test_run_hook_picks_best_verified_clip_per_segment(tmp_path, cut_video, make_photo):
    photo = make_photo(640, 480)
    tiktok = FakeSearcher("tiktok", "en", {
        "crab": [cand("tiktok", "t1"), cand("tiktok", "t2"), cand("tiktok", "bad")],
        "nautilus": [cand("tiktok", "t1"), cand("tiktok", "n1")],
    }, video=cut_video, photo=photo)
    douyin = FakeSearcher("douyin", "zh", {}, video=cut_video, photo=photo, blocked=True)
    stock = FakeSearcher("stock", "en", {"crab": [cand("pexels", "p1", kind="photo")]}, video=cut_video, photo=photo)
    queries = {0: {"en": ["crab"], "zh": ["鲎"]}, 1: {"en": ["nautilus"], "zh": ["鹦鹉螺"]}}
    deps, downloads = make_deps(tmp_path, cut_video, make_photo, [tiktok, douyin, stock], queries)
    paths = RunPaths(tmp_path / "run")

    data = run_hook(paths, SOURCE, deps, hook_seconds=10.0, exact_threshold=0.95, media_cache=tmp_path / "media")

    assert downloads == ["abc"]
    assert read_json(paths.hook_json) == data
    assert data["skipped_platforms"] == [{"platform": "douyin", "reason": "captcha/login"}]
    assert douyin.queries == ["鲎"]
    first, second = data["segments"]
    assert [c["provider_id"] for c in first["candidates"]] == ["t1", "p1", "t2"]
    assert first["winner"] == {
        "source": "tiktok", "provider": "tiktok", "provider_id": "t1", "kind": "video", "file": "hook/winner_01.mp4",
        "offset_s": 1.0, "score": 1.0, "label": "exact", "page_url": "https://tiktok.test/t1", "author": "tester",
    }
    assert (paths.root / "hook" / "winner_01.mp4").exists()
    assert second["winner"]["provider_id"] == "n1"
    assert second["winner"]["label"] == "similar"
    assert second["winner"]["score"] == pytest.approx(0.9, abs=1e-3)
    assert all(c["provider_id"] != "t1" for c in second["candidates"])


def test_run_hook_without_candidates_keeps_winner_empty(tmp_path, cut_video, make_photo):
    deps, downloads = make_deps(tmp_path, cut_video, make_photo, [], {0: {"en": [], "zh": []}, 1: {"en": [], "zh": []}})
    paths = RunPaths(tmp_path / "run")
    paths.root.mkdir(parents=True)
    shutil.copyfile(cut_video, paths.source_mp4)
    data = run_hook(paths, SOURCE, deps, hook_seconds=10.0, exact_threshold=0.85, media_cache=tmp_path / "media")
    assert downloads == []
    assert len(data["segments"]) == 2
    assert all(segment["winner"] is None for segment in data["segments"])


def test_source_download_error_tells_how_to_retry(tmp_path, cut_video, make_photo):
    from mayzfact.errors import PipelineError

    deps, _ = make_deps(tmp_path, cut_video, make_photo, [], {})

    def broken_download(video_id, dest):
        raise PipelineError("hook", "yt-dlp gagal download")

    deps.download_source = broken_download
    with pytest.raises(PipelineError, match="--from hook"):
        run_hook(RunPaths(tmp_path / "run"), SOURCE, deps, hook_seconds=10.0, exact_threshold=0.85, media_cache=tmp_path / "media")
