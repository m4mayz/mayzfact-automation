"""Parse JSON search internal platform jadi Candidate. Item yang field-nya kurang di-skip, nggak bikin crash."""

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import quote

from mayzfact.providers.types import Candidate, Rendition


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _first_url(obj: Any) -> str:
    urls = (obj or {}).get("url_list") or [] if isinstance(obj, dict) else []
    return urls[0] if urls else ""


def parse_tiktok(payload: dict, start_rank: int = 0) -> list[Candidate]:
    items = payload.get("item_list")
    if items is None:
        items = [entry.get("item") for entry in payload.get("data") or [] if isinstance(entry, dict)]
    out: list[Candidate] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        video = item.get("video") or {}
        vid = str(item.get("id") or "")
        cover = video.get("originCover") or video.get("cover") or ""
        if not vid or not cover:
            continue
        author = (item.get("author") or {}).get("uniqueId", "")
        width, height = _int(video.get("width")), _int(video.get("height"))
        play = video.get("playAddr") or ""
        out.append(Candidate(
            provider="tiktok", id=vid, kind="video",
            duration_s=float(video.get("duration") or 0) or None,
            page_url=f"https://www.tiktok.com/@{author}/video/{vid}", author=author,
            renditions=(Rendition(play, width, height),) if play and width and height else (),
            rank=start_rank + len(out), thumbnail_url=cover,
        ))
    return out


def parse_douyin(payload: dict, start_rank: int = 0) -> list[Candidate]:
    out: list[Candidate] = []
    for entry in payload.get("data") or []:
        info = (entry or {}).get("aweme_info") if isinstance(entry, dict) else None
        if not info:
            continue
        aweme_id = str(info.get("aweme_id") or "")
        video = info.get("video") or {}
        cover = _first_url(video.get("cover")) or _first_url(video.get("origin_cover"))
        if not aweme_id or not cover:
            continue
        author = (info.get("author") or {}).get("nickname", "")
        images = info.get("images") or []
        if images:
            first = images[0] or {}
            url, width, height = _first_url(first), _int(first.get("width")), _int(first.get("height"))
            if not url or not width or not height:
                continue
            kind, duration, renditions = "photo", None, (Rendition(url, width, height),)
        else:
            millis = _int(info.get("duration")) or _int(video.get("duration"))
            play = _first_url(video.get("play_addr"))
            width, height = _int(video.get("width")), _int(video.get("height"))
            kind, duration = "video", (millis / 1000 if millis else None)
            renditions = (Rendition(play, width, height),) if play and width and height else ()
        out.append(Candidate(
            provider="douyin", id=aweme_id, kind=kind, duration_s=duration,
            page_url=f"https://www.douyin.com/video/{aweme_id}", author=author,
            renditions=renditions, rank=start_rank + len(out), thumbnail_url=cover,
        ))
    return out


def parse_rednote(payload: dict, start_rank: int = 0) -> list[Candidate]:
    out: list[Candidate] = []
    for item in (payload.get("data") or {}).get("items") or []:
        if not isinstance(item, dict) or item.get("model_type", "note") != "note":
            continue
        card = item.get("note_card") or {}
        cover = card.get("cover") or {}
        note_id = str(item.get("id") or "")
        url = cover.get("url_default") or cover.get("url") or ""
        if not note_id or not url:
            continue
        kind = "video" if card.get("type") == "video" else "photo"
        width, height = _int(cover.get("width")), _int(cover.get("height"))
        user = card.get("user") or {}
        token = quote(item.get("xsec_token", ""), safe="")
        out.append(Candidate(
            provider="rednote", id=note_id, kind=kind, duration_s=None,
            page_url=f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={token}&xsec_source=pc_search",
            author=user.get("nickname") or user.get("nick_name", ""),
            renditions=(Rendition(url, width, height),) if kind == "photo" and width and height else (),
            rank=start_rank + len(out), thumbnail_url=url,
        ))
    return out


def parse_pinterest(payload: dict, start_rank: int = 0) -> list[Candidate]:
    results = ((payload.get("resource_response") or {}).get("data") or {}).get("results") or []
    out: list[Candidate] = []
    for pin in results:
        if not isinstance(pin, dict):
            continue
        pin_id = str(pin.get("id") or "")
        images = pin.get("images") or {}
        orig = images.get("orig") or {}
        thumb = (images.get("474x") or {}).get("url") or orig.get("url", "")
        videos = ((pin.get("videos") or {}).get("video_list")) or {}
        mp4 = max(
            (v for v in videos.values() if isinstance(v, dict) and str(v.get("url", "")).endswith(".mp4")),
            key=lambda v: _int(v.get("width")), default=None,
        )
        if not pin_id or not thumb:
            continue
        if mp4 and _int(mp4.get("width")) and _int(mp4.get("height")):
            kind, duration = "video", (_int(mp4.get("duration")) / 1000 or None)
            renditions = (Rendition(mp4["url"], _int(mp4["width"]), _int(mp4["height"])),)
        elif orig.get("url") and _int(orig.get("width")) and _int(orig.get("height")):
            kind, duration = "photo", None
            renditions = (Rendition(orig["url"], _int(orig["width"]), _int(orig["height"])),)
        else:
            continue
        out.append(Candidate(
            provider="pinterest", id=pin_id, kind=kind, duration_s=duration,
            page_url=f"https://www.pinterest.com/pin/{pin_id}/", author=(pin.get("pinner") or {}).get("username", ""),
            renditions=renditions, rank=start_rank + len(out), thumbnail_url=thumb,
        ))
    return out


PARSERS: dict[str, Callable[[dict, int], list[Candidate]]] = {
    "tiktok": parse_tiktok,
    "douyin": parse_douyin,
    "rednote": parse_rednote,
    "pinterest": parse_pinterest,
}

# (template URL halaman search, pola URL response JSON yang ditangkep)
SEARCH_PAGES: dict[str, tuple[str, tuple[str, ...]]] = {
    "tiktok": ("https://www.tiktok.com/search/video?q={q}", ("/api/search/item/full", "/api/search/general/full")),
    "douyin": ("https://www.douyin.com/search/{q}?type=video", ("/aweme/v1/web/search/item", "/aweme/v1/web/general/search")),
    "rednote": (
        "https://www.xiaohongshu.com/search_result?keyword={q}&source=web_search_result_notes",
        ("/api/sns/web/v1/search/notes",),
    ),
    "pinterest": ("https://www.pinterest.com/search/pins/?q={q}", ("/resource/BaseSearchResource/get",)),
}


def search_url(platform: str, query: str) -> str:
    template, _ = SEARCH_PAGES[platform]
    return template.format(q=quote(query, safe=""))
