"""Skor relevansi kandidat stock: SigLIP teks beat vs thumbnail (spec Fase 2 bagian 6)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from mayzfact.embed import Encoder, can_open_image
from mayzfact.providers.types import Candidate


class ThumbScorer:
    def __init__(self, encoder: Encoder, fetch: Callable[[Candidate], Path | None]) -> None:
        self._encoder = encoder
        self._fetch = fetch

    def score(self, text: str, candidates: list[Candidate]) -> list[float]:
        paths = [self._fetch(c) for c in candidates]
        valid = [i for i, p in enumerate(paths) if p is not None and can_open_image(p)]
        scores = [-1.0] * len(candidates)
        if valid:
            sims = self._encoder.images([paths[i] for i in valid]) @ self._encoder.texts([text])[0]
            for i, sim in zip(valid, sims):
                scores[i] = float(sim)
        return scores
