"""Gabungin hasil Pexels + Pixabay buat 1 query."""

from __future__ import annotations

from mayzfact.providers.pexels import Pexels
from mayzfact.providers.pixabay import Pixabay
from mayzfact.providers.types import Candidate


def merge_candidates(lists: list[list[Candidate]]) -> list[Candidate]:
    seen: set[tuple[str, str]] = set()
    merged: list[Candidate] = []
    for items in lists:
        for candidate in items:
            key = (candidate.provider, candidate.id)
            if key not in seen:
                seen.add(key)
                merged.append(candidate)
    return merged


class StockSearch:
    def __init__(self, pexels: Pexels, pixabay: Pixabay) -> None:
        self.pexels = pexels
        self.pixabay = pixabay

    def candidates(self, kind: str, query: str) -> list[Candidate]:
        if kind == "video":
            lists = [self.pexels.videos(query, "portrait"), self.pexels.videos(query), self.pixabay.videos(query)]
        else:
            lists = [self.pexels.photos(query, "portrait"), self.pexels.photos(query), self.pixabay.photos(query)]
        return merge_candidates(lists)
