"""Gabungin hasil Pexels + Pixabay buat 1 query."""

from __future__ import annotations

from typing import Any, Callable

from mayzfact.platforms.base import PlatformBlocked
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


class PlatformMediaSearch:
    """Platform login (misalnya Pinterest) sebagai sumber klip biasa. 1 search per query, hasilnya dipakai video & foto."""

    def __init__(self, platform: Any, log: Callable[[str], None] = print) -> None:
        self._platform = platform
        self._log = log
        self._results: dict[str, list[Candidate]] = {}
        self._blocked = False

    def candidates(self, kind: str, query: str) -> list[Candidate]:
        if query not in self._results:
            if self._blocked:
                return []
            try:
                self._results[query] = self._platform.search(query)
            except PlatformBlocked as exc:
                self._blocked = True
                self._log(f"[clips] {self._platform.name} di-skip ({exc.reason})")
                return []
        return [c for c in self._results[query] if c.kind == kind]


class CombinedSearch:
    def __init__(self, sources: list[Any]) -> None:
        self._sources = sources

    def candidates(self, kind: str, query: str) -> list[Candidate]:
        return merge_candidates([source.candidates(kind, query) for source in self._sources])
