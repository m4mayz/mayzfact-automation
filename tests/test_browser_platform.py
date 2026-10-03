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


class FakeContext:
    def __init__(self, page_error=None, cookie_error=None):
        self.page_error, self.cookie_error, self.closed = page_error, cookie_error, False

    def new_page(self):
        if self.page_error:
            raise self.page_error
        raise AssertionError("test ini nggak butuh page")

    def cookies(self):
        if self.cookie_error:
            raise self.cookie_error
        return []

    def close(self):
        self.closed = True


class FakePlaywright:
    def __init__(self, context=None):
        self.launched, self.stopped = [], 0
        self.chromium = self
        self.context = context

    def launch_persistent_context(self, user_data_dir, **kwargs):
        self.launched.append(Path(user_data_dir).name)
        return self.context or FakeContext()

    def stop(self):
        self.stopped += 1


def test_platforms_share_one_playwright_instance(tmp_path):
    from mayzfact.platforms.browser import SharedPlaywright

    fake = FakePlaywright()
    starts = []
    shared = SharedPlaywright(start=lambda: starts.append(1) or fake)
    tiktok = BrowserPlatform("tiktok", client=None, root=tmp_path, playwright=shared)
    douyin = BrowserPlatform("douyin", client=None, root=tmp_path, playwright=shared)
    tiktok._ctx()
    douyin._ctx()
    tiktok.close()
    douyin.close()
    assert (starts, fake.launched, fake.stopped) == ([1], ["tiktok", "douyin"], 0)
    shared.stop()
    shared.stop()
    assert fake.stopped == 1


def test_browser_error_on_new_page_marks_platform_blocked(tmp_path):
    from mayzfact.platforms.browser import SharedPlaywright

    fake = FakePlaywright(FakeContext(page_error=RuntimeError("Target page, context or browser has been closed")))
    platform = BrowserPlatform(
        "tiktok", client=None, root=tmp_path, playwright=SharedPlaywright(start=lambda: fake),
        throttle=Throttle(0, 0, sleep=lambda s: None),
    )
    with pytest.raises(PlatformBlocked, match="closed"):
        platform.search("crab")


def test_cookie_read_error_becomes_pipeline_error(tmp_path):
    from mayzfact.platforms.browser import SharedPlaywright
    from tests.factories import cand

    fake = FakePlaywright(FakeContext(cookie_error=RuntimeError("Target closed")))
    platform = BrowserPlatform("tiktok", client=None, root=tmp_path, playwright=SharedPlaywright(start=lambda: fake))
    with pytest.raises(PipelineError, match="cookies"):
        platform.download(cand("tiktok", "1"), tmp_path / "x.mp4")


def test_broken_payloads_do_not_crash_search():
    payloads = [["not", "a", "dict"], {"item_list": "rusak"}, {"item_list": [tiktok_item("ok")]}]
    platform = make_platform(lambda url, patterns: payloads)
    assert [c.id for c in platform.search("crab")] == ["ok"]


def test_login_browser_warms_up_search_page_for_captcha(tmp_path, monkeypatch):
    from mayzfact.platforms import browser

    visited, prompts = [], []

    class Page:
        def goto(self, url, **kwargs):
            visited.append(url)

    class Context(FakeContext):
        pages = [Page()]

    fake = FakePlaywright(Context())
    real_shared = browser.SharedPlaywright
    monkeypatch.setattr(browser, "SharedPlaywright", lambda: real_shared(start=lambda: fake))
    browser.open_login_browser("douyin", root=tmp_path, prompt=prompts.append)
    assert visited == ["https://www.douyin.com/", "https://www.douyin.com/search/%E7%8C%AB?type=video"]
    assert len(prompts) == 2 and "captcha" in prompts[1]
    assert fake.stopped == 1
