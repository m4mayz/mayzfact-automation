"""Search Pexels (video + foto) → Candidate."""

from __future__ import annotations

import httpx

from mayzfact.cache import SearchCache
from mayzfact.net import request_json
from mayzfact.providers.types import Candidate, Rendition

VIDEO_URL = "https://api.pexels.com/v1/videos/search"
PHOTO_URL = "https://api.pexels.com/v1/search"
PER_PAGE = 30


def parse_video(item: dict, rank: int) -> Candidate | None:
    renditions = tuple(
        Rendition(f["link"], int(f["width"]), int(f["height"]))
        for f in item.get("video_files") or []
        if f.get("link") and f.get("width") and f.get("height") and f.get("file_type") == "video/mp4"
    )
    if not renditions:
        return None
    return Candidate(
        provider="pexels",
        id=str(item["id"]),
        kind="video",
        duration_s=float(item.get("duration") or 0),
        page_url=item.get("url", ""),
        author=(item.get("user") or {}).get("name", ""),
        renditions=renditions,
        rank=rank,
        thumbnail_url=item.get("image") or "",
    )


def parse_photo(item: dict, rank: int) -> Candidate | None:
    src = (item.get("src") or {}).get("original")
    width, height = int(item.get("width") or 0), int(item.get("height") or 0)
    if not src or not width or not height:
        return None
    return Candidate(
        provider="pexels",
        id=str(item["id"]),
        kind="photo",
        duration_s=None,
        page_url=item.get("url", ""),
        author=item.get("photographer", ""),
        renditions=(Rendition(src, width, height),),
        rank=rank,
        thumbnail_url=(item.get("src") or {}).get("medium") or src,
    )


class Pexels:
    def __init__(self, api_key: str, client: httpx.Client, cache: SearchCache) -> None:
        self._api_key = api_key
        self._client = client
        self._cache = cache

    def _search(self, url: str, query: str, orientation: str | None) -> dict:
        params: dict[str, object] = {"query": query, "per_page": PER_PAGE}
        if orientation:
            params["orientation"] = orientation
        cache_key = {"url": url, **params}
        cached = self._cache.get("pexels", cache_key)
        if cached is not None:
            return cached
        body = request_json(self._client, "GET", url, step="clips", params=params, headers={"Authorization": self._api_key})
        self._cache.put("pexels", cache_key, body)
        return body

    def videos(self, query: str, orientation: str | None = None) -> list[Candidate]:
        items = self._search(VIDEO_URL, query, orientation).get("videos") or []
        return [c for rank, item in enumerate(items) if (c := parse_video(item, rank)) is not None]

    def photos(self, query: str, orientation: str | None = None) -> list[Candidate]:
        items = self._search(PHOTO_URL, query, orientation).get("photos") or []
        return [c for rank, item in enumerate(items) if (c := parse_photo(item, rank)) is not None]
