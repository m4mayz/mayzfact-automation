"""Skor relevansi kandidat stock: SigLIP teks beat vs thumbnail (spec Fase 2 bagian 6)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np

from mayzfact.embed import Encoder, can_open_image
from mayzfact.providers.types import Candidate


class ThumbScorer:
    """Embedding thumbnail & teks di-cache, jadi tiap gambar cuma di-encode sekali per run."""

    def __init__(self, encoder: Encoder, fetch: Callable[[Candidate], Path | None]) -> None:
        self._encoder = encoder
        self._fetch = fetch
        self._images: dict[Path, np.ndarray] = {}
        self._texts: dict[str, np.ndarray] = {}

    def score(self, text: str, candidates: list[Candidate]) -> list[float]:
        paths = [self._fetch(c) for c in candidates]
        valid = [i for i, p in enumerate(paths) if p is not None and (p in self._images or can_open_image(p))]
        new = list(dict.fromkeys(paths[i] for i in valid if paths[i] not in self._images))
        if new:
            for path, vector in zip(new, self._encoder.images(new)):
                self._images[path] = vector
        if text not in self._texts:
            self._texts[text] = self._encoder.texts([text])[0]
        scores = [-1.0] * len(candidates)
        for i in valid:
            scores[i] = float(self._images[paths[i]] @ self._texts[text])
        return scores
