"""Fallback umum: ambil og:video / og:image dari halaman."""

from __future__ import annotations

import re

import httpx

from mayzfact.manual.rednote import DESKTOP_UA
from mayzfact.manual.types import Media

_META = re.compile(r'<meta[^>]+(?:property|name)="og:(video(?::url)?|image)"[^>]+content="([^"]+)"', re.IGNORECASE)


def og_media(url: str, *, transport: httpx.BaseTransport | None = None) -> list[Media]:
    with httpx.Client(headers={"User-Agent": DESKTOP_UA}, timeout=15.0, transport=transport, follow_redirects=True) as client:
        html = client.get(url).text
    out: list[Media] = []
    for kind, content in _META.findall(html):
        media_url = f"https:{content}" if content.startswith("//") else content
        out.append(Media("video" if kind.lower().startswith("video") else "photo", media_url))
    return out
