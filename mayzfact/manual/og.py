"""Fallback umum: ambil og:video / og:image dari halaman."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

from mayzfact.manual.types import Media

DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def is_login_page(url: str) -> bool:
    """Halaman login / blok (…/login?redirect=…): isinya bukan post, og:image-nya cuma logo situs."""
    return "login" in urlparse(url).path.lower()


_META = re.compile(r'<meta[^>]+(?:property|name)="og:(video(?::url)?|image)"[^>]+content="([^"]+)"', re.IGNORECASE)


def og_media(url: str, *, transport: httpx.BaseTransport | None = None) -> list[Media]:
    with httpx.Client(headers={"User-Agent": DESKTOP_UA}, timeout=15.0, transport=transport, follow_redirects=True) as client:
        response = client.get(url)
    if is_login_page(str(response.url)):  # og:image halaman login = logo situs, bukan isi post
        return []
    html = response.text
    out: list[Media] = []
    for kind, content in _META.findall(html):
        media_url = f"https:{content}" if content.startswith("//") else content
        out.append(Media("video" if kind.lower().startswith("video") else "photo", media_url))
    return out
