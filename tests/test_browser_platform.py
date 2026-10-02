from pathlib import Path

import pytest

from mayzfact.errors import PipelineError
from mayzfact.platforms.base import PlatformBlocked, Throttle
from mayzfact.platforms.browser import BrowserPlatform


def tiktok_item(vid):
    return {"id": vid, "author": {"uniqueId": "u"}, "video": {"cover": f"https://c/{vid}.jpg", "duration": 9}}


def make_platform(capture, **kwargs):
    return BrowserPlatform(
        "tiktok", client=None, root=Path("unused"), capture=capture,
        throttle=Throttle(0, 0, sleep=lambda s: None), **kwargs,
    )


def test_search_parses_captured_payloads_with_running_rank():
    seen = []

    def capture(url, patterns):
        seen.append((url, patterns))
        return [{"item_list": [tiktok_item("1"), tiktok_item("2")]}, {"item_list": [tiktok_item("3")]}]

    platform = make_platform(capture)
    cands = platform.search("horseshoe crab")
    assert [c.id for c in cands] == ["1", "2", "3"]
    assert [c.rank for c in cands] == [0, 1, 2]
    assert seen[0][0] == "https://www.tiktok.com/search/video?q=horseshoe%20crab"
    assert platform.language == "en"


def test_blocked_platform_stays_blocked():
    calls = []

    def capture(url, patterns):
        calls.append(url)
        raise PlatformBlocked("tiktok", "captcha/login")

    platform = make_platform(capture)
    with pytest.raises(PlatformBlocked):
        platform.search("a")
    with pytest.raises(PlatformBlocked, match="captcha"):
        platform.search("b")
    assert len(calls) == 1
    assert platform.blocked_reason == "captcha/login"


def test_browser_launch_error_marks_platform_blocked():
    def capture(url, patterns):
        raise PipelineError("browser", "Chrome gagal dibuka")

    platform = make_platform(capture)
    with pytest.raises(PlatformBlocked, match="Chrome gagal dibuka"):
        platform.search("a")


def test_search_limit_per_run():
    platform = make_platform(lambda url, patterns: [{"item_list": []}], max_searches=2)
    platform.search("a")
    platform.search("b")
    with pytest.raises(PlatformBlocked, match="batas 2 search"):
        platform.search("c")


def test_photo_without_url_cannot_be_downloaded(tmp_path):
    from tests.factories import cand

    photo = cand("rednote", "x", kind="photo")
    photo = type(photo)(**{**photo.__dict__, "renditions": ()})
    with pytest.raises(PipelineError, match="URL gambar"):
        make_platform(lambda u, p: []).download(photo, tmp_path / "x.jpg")
