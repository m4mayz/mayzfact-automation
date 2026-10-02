"""Search Pixabay (video + foto) → Candidate."""

from __future__ import annotations

import httpx

from mayzfact.cache import SearchCache
from mayzfact.net import request_json
from mayzfact.providers.types import Candidate, Rendition

VIDEO_URL = "https://pixabay.com/api/videos/"
PHOTO_URL = "https://pixabay.com/api/"
PER_PAGE = 30
MAX_QUERY_CHARS = 100
LARGE_IMAGE_MAX = 1280  # largeImageURL maksimal 1280px tanpa full API access


def parse_video(hit: dict, rank: int) -> Candidate | None:
    renditions = tuple(
        Rendition(r["url"], int(r["width"]), int(r["height"]))
        for r in (hit.get("videos") or {}).values()
        if r.get("url") and r.get("width") and r.get("height")
    )
    if not renditions:
        return None
    return Candidate(
        provider="pixabay",
        id=str(hit["id"]),
        kind="video",
        duration_s=float(hit.get("duration") or 0),
        page_url=hit.get("pageURL", ""),
        author=hit.get("user", ""),
        renditions=renditions,
        rank=rank,
        thumbnail_url=next((r["thumbnail"] for r in (hit.get("videos") or {}).values() if r.get("thumbnail")), ""),
    )


def parse_photo(hit: dict, rank: int) -> Candidate | None:
    url = hit.get("largeImageURL")
    width, height = int(hit.get("imageWidth") or 0), int(hit.get("imageHeight") or 0)
    if not url or not width or not height:
        return None
    scale = min(1.0, LARGE_IMAGE_MAX / max(width, height))
    return Candidate(
        provider="pixabay",
        id=str(hit["id"]),
        kind="photo",
        duration_s=None,
        page_url=hit.get("pageURL", ""),
        author=hit.get("user", ""),
        renditions=(Rendition(url, round(width * scale), round(height * scale)),),
        rank=rank,
        thumbnail_url=hit.get("webformatURL") or url,
    )


class Pixabay:
    def __init__(self, api_key: str, client: httpx.Client, cache: SearchCache) -> None:
        self._api_key = api_key
        self._client = client
        self._cache = cache

    def _search(self, url: str, query: str, extra: dict) -> dict:
        params = {"q": query[:MAX_QUERY_CHARS], "per_page": PER_PAGE, "safesearch": "true", **extra}
        cache_key = {"url": url, **params}
        cached = self._cache.get("pixabay", cache_key)
        if cached is not None:
            return cached
        body = request_json(self._client, "GET", url, step="clips", params={"key": self._api_key, **params})
        self._cache.put("pixabay", cache_key, body)
        return body

    def videos(self, query: str) -> list[Candidate]:
        hits = self._search(VIDEO_URL, query, {"video_type": "film"}).get("hits") or []
        return [c for rank, hit in enumerate(hits) if (c := parse_video(hit, rank)) is not None]

    def photos(self, query: str) -> list[Candidate]:
        hits = self._search(PHOTO_URL, query, {"image_type": "photo"}).get("hits") or []
        return [c for rank, hit in enumerate(hits) if (c := parse_photo(hit, rank)) is not None]
