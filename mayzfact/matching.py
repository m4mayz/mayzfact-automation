"""Aturan ranking & mapping yang dipakai hook dan clips (tanpa model, tanpa network)."""

from __future__ import annotations

from typing import Any, Iterable

HOOK_END_TOLERANCE_S = 0.5






def hook_slot_map(slots: Iterable[Any], winners: int, hook_seconds: float) -> dict[int, int]:
    """Shot yang selesai di dalam area hook dapat pemenang hook sesuai urutan: {slot.index: urutan pemenang}.

    Pakai end_s, bukan start_s: shot yang mulai di detik 9.7 tapi jalan sampai 12 udah masuk narasi isi.
    """
    mapping: dict[int, int] = {}
    for slot in slots:
        if slot.end_s > hook_seconds + HOOK_END_TOLERANCE_S or len(mapping) >= winners:
            break
        mapping[slot.index] = len(mapping)
    return mapping


