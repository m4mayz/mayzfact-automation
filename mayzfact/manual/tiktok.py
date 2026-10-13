"""Resolver link TikTok lewat tiktokio.com (pendekatan scrapr, MIT): situs itu yang ngambil dari TikTok, kita tinggal parse link download-nya.

yt-dlp langsung ke TikTok butuh impersonation fingerprint TLS (curl_cffi), dan itu sengaja nggak dipakai.
"""

from __future__ import annotations

import re
from html import unescape

import httpx

from mayzfact.errors import PipelineError
from mayzfact.manual.rednote import DESKTOP_UA
from mayzfact.manual.types import Media

API = "https://tiktokio.com/api/v1/tk/html"
_LINK = re.compile(r'<a\s[^>]*href="([^"]+)"[^>]*class="download-btn ([^"]+)"', re.IGNORECASE)
_ITEM = re.compile(r'class="image-item"(.*?)</div>', re.S | re.IGNORECASE)
_HREF = re.compile(r'href="([^"]+)"')
_SRC = re.compile(r'src="([^"]+)"')
_CLASS_ORDER = ("download-btn-green", "download-btn-blue")  # HD dulu, terus SD; dua-duanya tanpa watermark


def resolve_tiktok(url: str, *, transport: httpx.BaseTransport | None = None) -> list[Media]:
    clean = url.strip().split("?")[0]
    headers = {"User-Agent": DESKTOP_UA, "Origin": "https://tiktokio.com", "Referer": "https://tiktokio.com/"}
    with httpx.Client(headers=headers, timeout=30.0, transport=transport, follow_redirects=True) as client:
        html = client.post(API, json={"vid": clean, "prefix": "tiktokio.com"}).text
    photos = []
    for block in _ITEM.findall(html):
        link = _HREF.search(block) or _SRC.search(block)
        if link:
            photos.append(Media("photo", unescape(link.group(1))))
    if photos:
        return photos
    links = {css: unescape(href) for href, css in _LINK.findall(html)}
    videos = [Media("video", links[c]) for c in _CLASS_ORDER if c in links]
    if not videos:
        raise PipelineError("fetch", "tiktokio nggak ngasih link download. Coba link lain atau upload file-nya.")
    return videos
