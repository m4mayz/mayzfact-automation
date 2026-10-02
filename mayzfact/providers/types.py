"""Tipe hasil search stock yang sama buat semua provider."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rendition:
    url: str
    width: int
    height: int


@dataclass(frozen=True)
class Candidate:
    provider: str  # "pexels" | "pixabay"
    id: str
    kind: str  # "video" | "photo"
    duration_s: float | None  # None buat foto
    page_url: str
    author: str
    renditions: tuple[Rendition, ...]
    rank: int  # posisi di hasil search provider (0 = paling relevan)
    thumbnail_url: str = ""  # gambar kecil buat scoring SigLIP
