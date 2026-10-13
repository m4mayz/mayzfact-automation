"""Tipe hasil resolver link manual."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Media:
    kind: str  # "video" | "photo"
    url: str
