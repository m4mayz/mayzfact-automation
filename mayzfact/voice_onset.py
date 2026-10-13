"""Awal kata yang beneran kedengeran.

Alignment ElevenLabs ngitung jeda sebelum kata sebagai bagian dari kata itu (contoh "Number" 9.74-10.56, padahal
suaranya baru mulai 10.49). Akibatnya caption dan card countdown kecepetan. Di sini awal kata digeser ke momen
pertama yang ada suaranya di dalam rentang kata itu, berdasarkan energi voice.mp3.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

STEP_S = 0.01  # envelope per 10 ms
SAMPLE_RATE = 8000
THRESHOLD_OF_PEAK = 0.08  # di atas 8% dari puncak (persentil 99) dianggap ada suara


def voice_envelope(path: Path) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-"],
        capture_output=True, check=True,
    ).stdout
    samples = np.abs(np.frombuffer(raw, dtype=np.int16).astype(np.float32))
    window = int(SAMPLE_RATE * STEP_S)
    usable = len(samples) // window * window
    return samples[:usable].reshape(-1, window).mean(axis=1)


def snap_word_starts(words: list[dict], envelope: np.ndarray) -> list[dict]:
    if len(envelope) == 0:
        return [dict(w) for w in words]
    threshold = THRESHOLD_OF_PEAK * float(np.percentile(envelope, 99))
    voiced = envelope > threshold
    out = []
    for word in words:
        first, last = int(word["start_s"] / STEP_S), min(int(word["end_s"] / STEP_S) + 1, len(voiced))
        hits = np.flatnonzero(voiced[first:last])
        start = round((first + hits[0]) * STEP_S, 3) if len(hits) else word["start_s"]
        out.append(dict(word, start_s=max(word["start_s"], start)))
    return out
