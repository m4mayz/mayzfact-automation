"""Resolver link RedNote → URL media dari window.__INITIAL_STATE__ halaman note. Port dari scrapr (MIT)."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from mayzfact.errors import PipelineError
from mayzfact.manual.types import Media

DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
_STATE = re.compile(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>", re.S)
_NOTE_ID = re.compile(r"/([a-f0-9]{24})", re.IGNORECASE)


def is_login_page(url: str) -> bool:
    """Halaman login / blok (website-login/error, /login?redirectPath=…): isinya bukan note."""
    path = urlparse(url).path.lower()
    return "login" in path


def rednote_state(html: str) -> dict | None:
    match = _STATE.search(html)
    if not match:
        return None
    try:
        return json.loads(re.sub(r":\s*undefined", ":null", match.group(1)))
    except ValueError:
        return None


def _is_note(value: Any) -> bool:
    return isinstance(value, dict) and any(value.get(k) for k in ("title", "desc", "imageList", "video"))


def find_note(state: Any) -> dict | None:
    if not isinstance(state, dict):
        return None
    for entry in ((state.get("note") or {}).get("noteDetailMap") or {}).values():
        note = (entry or {}).get("note") or entry
        if _is_note(note):
            return note
    for candidate in ((state.get("noteData") or {}).get("data") or {}).get("noteData"), (state.get("note") or {}).get("firstNote"):
        if _is_note(candidate):
            return candidate
    return None


def _https(url: str) -> str:
    return f"https:{url}" if url.startswith("//") else url


def note_media(note: dict) -> list[Media]:
    stream = (((note.get("video") or {}).get("media") or {}).get("stream")) or {}
    for codec in ("h264", "h265", "h266", "av1"):
        for item in stream.get(codec) or []:
            url = item.get("masterUrl") or (item.get("backupUrls") or [None])[0]
            if url:
                return [Media("video", _https(url))]
    photos = []
    for image in note.get("imageList") or []:
        url = (image or {}).get("urlOriginal") or (image or {}).get("urlDefault") or (image or {}).get("url")
        if url:
            photos.append(Media("photo", _https(url)))
    return photos


def resolve_rednote(url: str, *, transport: httpx.BaseTransport | None = None) -> list[Media]:
    headers = {"User-Agent": DESKTOP_UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
    with httpx.Client(headers=headers, timeout=15.0, transport=transport, follow_redirects=True) as client:
        response = client.get(url)
        if is_login_page(str(response.url)):
            raise PipelineError("fetch", "RedNote minta login / nolak akses buat note ini. Save file-nya dari app, terus upload di brief.")
        note = find_note(rednote_state(response.text))
        match = _NOTE_ID.search(str(response.url)) or _NOTE_ID.search(url)
        if not note and match:
            for alt in (f"https://www.xiaohongshu.com/discovery/item/{match.group(1)}", f"https://www.xiaohongshu.com/explore/{match.group(1)}"):
                note = find_note(rednote_state(client.get(alt).text))
                if note:
                    break
    if not note:
        raise PipelineError("fetch", "Data note RedNote nggak ketemu. Coba link lain atau upload file-nya.")
    media = note_media(note)
    if not media:
        raise PipelineError("fetch", "Note RedNote ini nggak punya video/foto yang bisa diambil.")
    return media
