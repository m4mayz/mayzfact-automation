"""Pembuat data palsu buat test."""

from __future__ import annotations

from mayzfact.models import Beat, Script


def make_script(n_beats: int = 10, photo_every: int = 3, words_per_beat: int = 11) -> Script:
    """Naskah dengan kata unik (w0x0, w0x1, ...) biar overlap ke source selalu 0."""
    beats = [
        Beat(
            text=" ".join(f"w{i}x{j}" for j in range(words_per_beat)) + ".",
            media="photo" if i % photo_every == 1 else "video",
            queries=[f"query {i}", "animal close up"],
        )
        for i in range(n_beats)
    ]
    return Script(beats=beats, fallback_query="ocean animals")
