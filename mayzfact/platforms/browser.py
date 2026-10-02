"""Platform login lewat Chrome (Playwright): search dengan nangkep JSON, download pakai yt-dlp + cookies."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from mayzfact.config import BROWSER_PROFILES_DIR
from mayzfact.errors import PipelineError
from mayzfact.net import download
from mayzfact.platforms.base import (
    PlatformBlocked, Throttle, cookies_to_netscape, looks_blocked, platform_info, url_blocked,
)
from mayzfact.platforms.parsers import PARSERS, SEARCH_PAGES, search_url
from mayzfact.providers.types import Candidate
from mayzfact.ytdlp import run_ytdlp

MAX_SEARCHES = 12
WAIT_S = 20.0

Capture = Callable[[str, tuple[str, ...]], list[dict]]


def _launch(name: str, root: Path, headless: bool) -> tuple[Any, Any]:
    try:
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
    except Exception as exc:
        raise PipelineError("browser", f"Playwright gagal jalan: {exc}") from exc
    try:
        context = playwright.chromium.launch_persistent_context(
            str(root / name), channel="chrome", headless=headless, viewport={"width": 1280, "height": 900},
        )
    except Exception as exc:
        playwright.stop()
        raise PipelineError(
            "browser", f"Chrome gagal dibuka buat {name}: {str(exc)[:200]}. Tutup jendela Chrome profil ini kalau masih kebuka."
        ) from exc
    return playwright, context


class BrowserPlatform:
    def __init__(
        self,
        name: str,
        *,
        client: Any,
        root: Path = BROWSER_PROFILES_DIR,
        headless: bool = False,
        capture: Capture | None = None,
        throttle: Throttle | None = None,
        max_searches: int = MAX_SEARCHES,
        log: Callable[[str], None] = print,
    ) -> None:
        self.info = platform_info(name)
        self.name = name
        self.language = self.info.language
        self.blocked_reason: str | None = None
        self._client = client
        self._root = root
        self._headless = headless
        self._capture_fn = capture
        self._throttle = throttle or Throttle()
        self._max = max_searches
        self._count = 0
        self._log = log
        self._playwright: Any = None
        self._context: Any = None

    def _ctx(self) -> Any:
        if self._context is None:
            self._playwright, self._context = _launch(self.name, self._root, self._headless)
        return self._context

    def search(self, query: str) -> list[Candidate]:
        if self.blocked_reason:
            raise PlatformBlocked(self.name, self.blocked_reason)
        if self._count >= self._max:
            self.blocked_reason = f"batas {self._max} search per run"
            raise PlatformBlocked(self.name, self.blocked_reason)
        self._count += 1
        self._throttle.wait()
        _, patterns = SEARCH_PAGES[self.name]
        capture = self._capture_fn or self._capture
        try:
            payloads = capture(search_url(self.name, query), patterns)
        except PlatformBlocked as exc:
            self.blocked_reason = exc.reason
            raise
        except PipelineError as exc:
            self.blocked_reason = exc.message
            raise PlatformBlocked(self.name, exc.message) from exc
        parse = PARSERS[self.name]
        candidates: list[Candidate] = []
        for payload in payloads:
            candidates += parse(payload, len(candidates))
        return candidates

    def _capture(self, url: str, patterns: tuple[str, ...]) -> list[dict]:
        from playwright.sync_api import Error as PlaywrightError

        page = self._ctx().new_page()
        responses: list[Any] = []
        page.on("response", lambda r: responses.append(r) if any(p in r.url for p in patterns) else None)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=WAIT_S * 1000)
            deadline = time.monotonic() + WAIT_S
            while not responses and time.monotonic() < deadline:
                if url_blocked(self.info, page.url):
                    raise PlatformBlocked(self.name, "diarahin ke halaman login/captcha")
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(700)
            page.wait_for_timeout(800)
            payloads = []
            for response in responses:
                try:
                    payloads.append(response.json())
                except Exception:
                    continue
            if not payloads:
                reason = "captcha/login" if looks_blocked(self.info, page.url, page.content()) else "hasil search nggak kebaca"
                raise PlatformBlocked(self.name, reason)
            return payloads
        except PlaywrightError as exc:
            raise PlatformBlocked(self.name, f"browser error: {str(exc)[:120]}") from exc
        finally:
            page.close()

    def _cookies_file(self) -> Path:
        path = self._root / f"{self.name}.cookies.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(cookies_to_netscape(self._ctx().cookies()), encoding="utf-8")
        return path

    def download(self, candidate: Candidate, dest: Path) -> Path:
        if candidate.kind == "photo":
            if not candidate.renditions:
                raise PipelineError("hook", f"{self.name} {candidate.id} nggak punya URL gambar.")
            return download(self._client, candidate.renditions[0].url, dest, step="hook")
        return run_ytdlp(candidate.page_url, dest, cookies=self._cookies_file())

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._context = self._playwright = None


def read_profile_cookies(name: str, root: Path = BROWSER_PROFILES_DIR) -> list[dict]:
    playwright, context = _launch(name, root, headless=True)
    try:
        return context.cookies()
    finally:
        context.close()
        playwright.stop()


def open_login_browser(name: str, root: Path = BROWSER_PROFILES_DIR, prompt: Callable[[str], str] = input) -> None:
    info = platform_info(name)
    playwright, context = _launch(name, root, headless=False)
    try:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(info.home_url)
        prompt(f"Login ke {name} di jendela Chrome, terus tekan Enter di sini...")
    finally:
        context.close()
        playwright.stop()
