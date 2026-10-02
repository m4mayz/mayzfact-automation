"""Info platform login, deteksi ke-blok, konversi cookie, dan jeda antar search (spec Fase 2 bagian 5)."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable

from mayzfact.errors import PipelineError


class PlatformBlocked(Exception):
    def __init__(self, platform: str, reason: str) -> None:
        super().__init__(f"{platform}: {reason}")
        self.platform = platform
        self.reason = reason


@dataclass(frozen=True)
class PlatformInfo:
    name: str
    language: str  # "en" | "zh": bahasa query yang dipakai
    home_url: str
    cookie_domain: str
    login_cookie: str
    login_cookie_value: str | None  # None = asal nggak kosong
    blocked_url_markers: tuple[str, ...]
    blocked_html_markers: tuple[str, ...]


PLATFORMS: dict[str, PlatformInfo] = {
    "tiktok": PlatformInfo(
        "tiktok", "en", "https://www.tiktok.com/", "tiktok.com", "sessionid", None,
        ("/login", "/signup"), ("captcha-verify-container", "captcha_container"),
    ),
    "douyin": PlatformInfo(
        "douyin", "zh", "https://www.douyin.com/", "douyin.com", "sessionid", None,
        ("/login", "verify.zijieapi.com"), ("captcha_container", "verify-bar-close"),
    ),
    "rednote": PlatformInfo(
        "rednote", "zh", "https://www.xiaohongshu.com/explore", "xiaohongshu.com", "web_session", None,
        ("/website-login", "/login"), ("red-captcha", "captcha-container"),
    ),
    "pinterest": PlatformInfo(
        "pinterest", "en", "https://www.pinterest.com/", "pinterest.com", "_auth", "1",
        ("/login", "/signup"), (),
    ),
}


def platform_info(name: str) -> PlatformInfo:
    if name not in PLATFORMS:
        raise PipelineError("config", f"Platform {name!r} nggak dikenal. Pilihan: {', '.join(PLATFORMS)}")
    return PLATFORMS[name]


def url_blocked(info: PlatformInfo, url: str) -> bool:
    return any(marker in url for marker in info.blocked_url_markers)


def looks_blocked(info: PlatformInfo, url: str, html: str) -> bool:
    return url_blocked(info, url) or any(marker in html for marker in info.blocked_html_markers)


def is_logged_in(info: PlatformInfo, cookies: list[dict]) -> bool:
    for cookie in cookies:
        if cookie.get("name") != info.login_cookie or info.cookie_domain not in cookie.get("domain", ""):
            continue
        value = cookie.get("value") or ""
        if value and (info.login_cookie_value is None or value == info.login_cookie_value):
            return True
    return False


def cookies_to_netscape(cookies: list[dict]) -> str:
    """Cookie Playwright → format Netscape yang dibaca yt-dlp (--cookies)."""
    lines = ["# Netscape HTTP Cookie File"]
    for cookie in cookies:
        domain = cookie.get("domain", "")
        expires = cookie.get("expires", -1) or -1
        lines.append("\t".join([
            domain,
            "TRUE" if domain.startswith(".") else "FALSE",
            cookie.get("path") or "/",
            "TRUE" if cookie.get("secure") else "FALSE",
            str(int(expires)) if expires > 0 else "0",
            cookie.get("name", ""),
            cookie.get("value", ""),
        ]))
    return "\n".join(lines) + "\n"


class Throttle:
    """Jeda acak antar search biar pola request nggak kelihatan kayak bot."""

    def __init__(
        self,
        min_s: float = 2.0,
        max_s: float = 5.0,
        *,
        sleep: Callable[[float], None] = time.sleep,
        rand: Callable[[float, float], float] = random.uniform,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._min, self._max = min_s, max_s
        self._sleep, self._rand, self._clock = sleep, rand, clock
        self._last: float | None = None

    def wait(self) -> None:
        if self._last is not None:
            gap = self._rand(self._min, self._max)
            elapsed = self._clock() - self._last
            if elapsed < gap:
                self._sleep(gap - elapsed)
        self._last = self._clock()
