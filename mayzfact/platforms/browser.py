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
HOOK_CLIP_MAX_S = 31  # verifikasi hook cuma lihat 30 detik pertama

Capture = Callable[[str, tuple[str, ...]], list[dict]]


def _start_playwright() -> Any:
    try:
        from playwright.sync_api import sync_playwright

        return sync_playwright().start()
    except Exception as exc:
        raise PipelineError("browser", f"Playwright gagal jalan: {exc}") from exc


class SharedPlaywright:
    """Satu instance Playwright per run. Sync API nggak bisa start 2 instance di thread yang sama."""

    def __init__(self, start: Callable[[], Any] = _start_playwright) -> None:
        self._start = start
        self._playwright: Any = None

    def get(self) -> Any:
        if self._playwright is None:
            self._playwright = self._start()
        return self._playwright

    def stop(self) -> None:
        if self._playwright is not None:
            try:
                self._playwright.stop()
            finally:
                self._playwright = None


def _launch_context(playwright: Any, name: str, root: Path, headless: bool) -> Any:
    try:
        return playwright.chromium.launch_persistent_context(
            str(root / name), channel="chrome", headless=headless, viewport={"width": 1280, "height": 900},
        )
    except Exception as exc:
        raise PipelineError(
            "browser", f"Chrome gagal dibuka buat {name}: {str(exc)[:200]}. Tutup jendela Chrome profil ini kalau masih kebuka."
        ) from exc


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
        playwright: SharedPlaywright | None = None,
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
        self._owns_playwright = playwright is None
        self._playwright = playwright or SharedPlaywright()
        self._context: Any = None

    def _ctx(self) -> Any:
        if self._context is None:
            self._context = _launch_context(self._playwright.get(), self.name, self._root, self._headless)
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
            if not isinstance(payload, dict):
                continue
            try:
                candidates += parse(payload, len(candidates))
            except Exception as exc:  # bentuk JSON platform berubah: skip payload ini, jangan matiin step hook
                self._log(f"[hook] {self.name}: format JSON beda ({type(exc).__name__}), payload di-skip")
        return candidates

    def _capture(self, url: str, patterns: tuple[str, ...]) -> list[dict]:
        page = None
        responses: list[Any] = []
        try:
            page = self._ctx().new_page()
            page.on("response", lambda r: responses.append(r) if any(p in r.url for p in patterns) else None)
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
        except (PlatformBlocked, PipelineError):
            raise
        except Exception as exc:  # error Playwright apa pun (jendela ditutup, timeout, dll) = platform di-skip
            raise PlatformBlocked(self.name, f"browser error: {str(exc)[:120]}") from exc
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass

    def _cookies_file(self) -> Path:
        try:
            cookies = self._ctx().cookies()
        except PipelineError:
            raise
        except Exception as exc:
            raise PipelineError("hook", f"cookies {self.name} gagal dibaca: {str(exc)[:120]}") from exc
        path = self._root / f"{self.name}.cookies.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(cookies_to_netscape(cookies), encoding="utf-8")
        return path

    def download(self, candidate: Candidate, dest: Path) -> Path:
        if candidate.kind == "photo":
            if not candidate.renditions:
                raise PipelineError("hook", f"{self.name} {candidate.id} nggak punya URL gambar.")
            return download(self._client, candidate.renditions[0].url, dest, step="hook")
        return run_ytdlp(candidate.page_url, dest, cookies=self._cookies_file(), max_seconds=HOOK_CLIP_MAX_S)

    def close(self) -> None:
        try:
            if self._context is not None:
                self._context.close()
        except Exception:
            pass
        finally:
            self._context = None
            if self._owns_playwright:
                self._playwright.stop()


def read_profile_cookies(name: str, root: Path = BROWSER_PROFILES_DIR) -> list[dict]:
    shared = SharedPlaywright()
    try:
        context = _launch_context(shared.get(), name, root, headless=True)
        try:
            return context.cookies()
        finally:
            context.close()
    finally:
        shared.stop()


def open_login_browser(name: str, root: Path = BROWSER_PROFILES_DIR, prompt: Callable[[str], str] = input) -> None:
    info = platform_info(name)
    shared = SharedPlaywright()
    try:
        context = _launch_context(shared.get(), name, root, headless=False)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(info.home_url)
            prompt(f"Login ke {name} di jendela Chrome, terus tekan Enter di sini...")
        finally:
            context.close()
    finally:
        shared.stop()
