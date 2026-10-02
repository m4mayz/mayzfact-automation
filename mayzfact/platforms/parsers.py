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


def _float(value: Any) -> float | None:
    try:
        return float(value) or None
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _first_url(obj: Any) -> str:
    urls = _list(_dict(obj).get("url_list"))
    return urls[0] if urls and isinstance(urls[0], str) else ""


def _collect(items: Any, build: Callable[[Any, int], Candidate | None], start_rank: int) -> list[Candidate]:
    """Bangun Candidate per item. Item yang bentuknya aneh di-skip, item lain tetap jalan."""
    out: list[Candidate] = []
    for item in _list(items):
        try:
            candidate = build(item, start_rank + len(out))
        except (AttributeError, TypeError, ValueError, KeyError, IndexError):
            candidate = None
        if candidate is not None:
            out.append(candidate)
    return out


def _tiktok_item(item: Any, rank: int) -> Candidate | None:
    item = _dict(item)
    video = _dict(item.get("video"))
    vid = str(item.get("id") or "")
    cover = video.get("originCover") or video.get("cover") or ""
    if not vid or not isinstance(cover, str) or not cover:
        return None
    author = str(_dict(item.get("author")).get("uniqueId") or "")
    width, height = _int(video.get("width")), _int(video.get("height"))
    play = video.get("playAddr") if isinstance(video.get("playAddr"), str) else ""
    return Candidate(
        provider="tiktok", id=vid, kind="video", duration_s=_float(video.get("duration")),
        page_url=f"https://www.tiktok.com/@{author}/video/{vid}", author=author,
        renditions=(Rendition(play, width, height),) if play and width and height else (),
        rank=rank, thumbnail_url=cover,
    )


def parse_tiktok(payload: dict, start_rank: int = 0) -> list[Candidate]:
    payload = _dict(payload)
    items = payload.get("item_list")
    if items is None:
        items = [_dict(entry).get("item") for entry in _list(payload.get("data"))]
    return _collect(items, _tiktok_item, start_rank)


def _douyin_item(entry: Any, rank: int) -> Candidate | None:
    info = _dict(_dict(entry).get("aweme_info"))
    aweme_id = str(info.get("aweme_id") or "")
    video = _dict(info.get("video"))
    cover = _first_url(video.get("cover")) or _first_url(video.get("origin_cover"))
    if not aweme_id or not cover:
        return None
    author = str(_dict(info.get("author")).get("nickname") or "")
    images = _list(info.get("images"))
    if images:
        first = _dict(images[0])
        url, width, height = _first_url(first), _int(first.get("width")), _int(first.get("height"))
        if not url or not width or not height:
            return None
        kind, duration, renditions = "photo", None, (Rendition(url, width, height),)
    else:
        millis = _int(info.get("duration")) or _int(video.get("duration"))
        play = _first_url(video.get("play_addr"))
        width, height = _int(video.get("width")), _int(video.get("height"))
        kind, duration = "video", (millis / 1000 if millis else None)
        renditions = (Rendition(play, width, height),) if play and width and height else ()
    return Candidate(
        provider="douyin", id=aweme_id, kind=kind, duration_s=duration,
        page_url=f"https://www.douyin.com/video/{aweme_id}", author=author,
        renditions=renditions, rank=rank, thumbnail_url=cover,
    )


def parse_douyin(payload: dict, start_rank: int = 0) -> list[Candidate]:
    return _collect(_dict(payload).get("data"), _douyin_item, start_rank)


def _rednote_item(item: Any, rank: int) -> Candidate | None:
    item = _dict(item)
    if item.get("model_type", "note") != "note":
        return None
    card = _dict(item.get("note_card"))
    cover = _dict(card.get("cover"))
    note_id = str(item.get("id") or "")
    url = cover.get("url_default") or cover.get("url") or ""
    if not note_id or not isinstance(url, str) or not url:
        return None
    kind = "video" if card.get("type") == "video" else "photo"
    width, height = _int(cover.get("width")), _int(cover.get("height"))
    user = _dict(card.get("user"))
    token = quote(str(item.get("xsec_token") or ""), safe="")
    return Candidate(
        provider="rednote", id=note_id, kind=kind, duration_s=None,
        page_url=f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={token}&xsec_source=pc_search",
        author=str(user.get("nickname") or user.get("nick_name") or ""),
        renditions=(Rendition(url, width, height),) if kind == "photo" and width and height else (),
        rank=rank, thumbnail_url=url,
    )


def parse_rednote(payload: dict, start_rank: int = 0) -> list[Candidate]:
    return _collect(_dict(_dict(payload).get("data")).get("items"), _rednote_item, start_rank)


def _pinterest_item(pin: Any, rank: int) -> Candidate | None:
    pin = _dict(pin)
    pin_id = str(pin.get("id") or "")
    images = _dict(pin.get("images"))
    orig = _dict(images.get("orig"))
    thumb = _dict(images.get("474x")).get("url") or orig.get("url") or ""
    if not pin_id or not isinstance(thumb, str) or not thumb:
        return None
    videos = _dict(_dict(pin.get("videos")).get("video_list"))
    mp4 = max(
        (v for v in videos.values() if isinstance(v, dict) and str(v.get("url", "")).endswith(".mp4")),
        key=lambda v: _int(v.get("width")), default=None,
    )
    if mp4 and _int(mp4.get("width")) and _int(mp4.get("height")):
        kind, duration = "video", (_int(mp4.get("duration")) / 1000 or None)
        renditions = (Rendition(mp4["url"], _int(mp4["width"]), _int(mp4["height"])),)
    elif orig.get("url") and _int(orig.get("width")) and _int(orig.get("height")):
        kind, duration = "photo", None
        renditions = (Rendition(orig["url"], _int(orig["width"]), _int(orig["height"])),)
    else:
        return None
    return Candidate(
        provider="pinterest", id=pin_id, kind=kind, duration_s=duration,
        page_url=f"https://www.pinterest.com/pin/{pin_id}/", author=str(_dict(pin.get("pinner")).get("username") or ""),
        renditions=renditions, rank=rank, thumbnail_url=thumb,
    )


def parse_pinterest(payload: dict, start_rank: int = 0) -> list[Candidate]:
    results = _dict(_dict(_dict(payload).get("resource_response")).get("data")).get("results")
    return _collect(results, _pinterest_item, start_rank)


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
