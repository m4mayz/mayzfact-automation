import pytest

from mayzfact.errors import PipelineError
from mayzfact.platforms.base import (
    PLATFORMS, Throttle, cookies_to_netscape, is_logged_in, looks_blocked, platform_info, url_blocked,
)


def test_platform_info_rejects_unknown():
    assert platform_info("douyin").language == "zh"
    with pytest.raises(PipelineError, match="instagram"):
        platform_info("instagram")


def test_url_and_html_block_detection():
    tiktok = PLATFORMS["tiktok"]
    assert url_blocked(tiktok, "https://www.tiktok.com/login?redirect_url=x")
    assert not url_blocked(tiktok, "https://www.tiktok.com/search/video?q=crab")
    assert looks_blocked(tiktok, "https://www.tiktok.com/search/video?q=crab", '<div id="captcha-verify-container">')
    assert not looks_blocked(tiktok, "https://www.tiktok.com/search/video?q=crab", "<div>hasil</div>")


def test_is_logged_in():
    rednote, pinterest = PLATFORMS["rednote"], PLATFORMS["pinterest"]
    assert is_logged_in(rednote, [{"name": "web_session", "value": "abc", "domain": ".xiaohongshu.com"}])
    assert not is_logged_in(rednote, [{"name": "web_session", "value": "abc", "domain": ".example.com"}])
    assert not is_logged_in(rednote, [{"name": "web_session", "value": "", "domain": ".xiaohongshu.com"}])
    assert is_logged_in(pinterest, [{"name": "_auth", "value": "1", "domain": ".pinterest.com"}])
    assert not is_logged_in(pinterest, [{"name": "_auth", "value": "0", "domain": ".pinterest.com"}])


def test_cookies_to_netscape():
    text = cookies_to_netscape([
        {"name": "sessionid", "value": "s3cr3t", "domain": ".tiktok.com", "path": "/", "secure": True, "expires": 1893456000.5},
        {"name": "tt", "value": "x", "domain": "www.tiktok.com", "path": "/", "secure": False, "expires": -1},
    ])
    lines = text.splitlines()
    assert lines[0] == "# Netscape HTTP Cookie File"
    assert lines[1] == ".tiktok.com\tTRUE\t/\tTRUE\t1893456000\tsessionid\ts3cr3t"
    assert lines[2] == "www.tiktok.com\tFALSE\t/\tFALSE\t0\ttt\tx"


def test_throttle_waits_random_gap():
    now = [100.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    throttle = Throttle(2.0, 5.0, sleep=sleep, rand=lambda a, b: 3.0, clock=lambda: now[0])
    throttle.wait()
    now[0] += 1.0
    throttle.wait()
    now[0] += 10.0
    throttle.wait()
    assert sleeps == [2.0]
