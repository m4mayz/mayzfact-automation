"""Aturan ranking & mapping yang dipakai hook dan clips (tanpa model, tanpa network)."""

from __future__ import annotations

from typing import Any, Iterable, Sequence


def top_k(scores: Sequence[float], k: int) -> list[int]:
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:k]


def match_label(score: float, threshold: float) -> str:
    return "exact" if score >= threshold else "similar"


def hook_slot_map(slots: Iterable[Any], winners: int, hook_seconds: float) -> dict[int, int]:
    """Shot yang mulai sebelum hook_seconds dapat pemenang hook sesuai urutan: {slot.index: urutan pemenang}."""
    mapping: dict[int, int] = {}
    for slot in slots:
        if slot.start_s >= hook_seconds or len(mapping) >= winners:
            break
        mapping[slot.index] = len(mapping)
    return mapping


def rerank_key(score: float, tier_value: int, provider_rank: int) -> tuple:
    """Tier 3 (bakal di-upscale) di belakang. Sisanya skor tertinggi duluan, terus tier, terus provider."""
    return (tier_value == 3, -score, tier_value, provider_rank)
