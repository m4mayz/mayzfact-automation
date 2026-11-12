"""Potong jeda panjang di voice FaktaCuil.

Aturan Akmal (2026-11-12): jeda antar kalimat jangan panjang-panjang, maksimal 0,2 detik,
jadi kalimat berikutnya langsung nyambung. Modul ini cuma ngurus hitungan murni
(cari silence → tentukan bagian yang dibuang → geser timing karakter); audio-nya
dipotong pakai ffmpeg di `trim_audio`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

SILENCE_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
SILENCE_END = re.compile(r"silence_end:\s*(-?[\d.]+)")


def parse_silences(stderr: str) -> list[tuple[float, float]]:
    """Ambil pasangan (start, end) dari output `silencedetect` ffmpeg."""
    out: list[tuple[float, float]] = []
    start: float | None = None
    for line in stderr.splitlines():
        m = SILENCE_START.search(line)
        if m:
            start = float(m.group(1))
            continue
        m = SILENCE_END.search(line)
        if m and start is not None:
            out.append((start, float(m.group(1))))
            start = None
    return out


def plan_cuts(silences: list[tuple[float, float]], max_gap_s: float) -> list[tuple[float, float]]:
    """Bagian yang dibuang: kelebihan tiap hening di atas `max_gap_s`.

    Awal hening dibiarkan `max_gap_s` (biar gak kelewat nempel), sisanya dipotong.
    Hening yang lebih pendek dari batas nggak disentuh.
    """
    cuts: list[tuple[float, float]] = []
    for start, end in silences:
        if end - start <= max_gap_s:
            continue
        cut_start = start + max_gap_s
        if end - cut_start > 1e-3:
            cuts.append((cut_start, end))
    return cuts


def keep_segments(duration_s: float, cuts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Rentang audio yang dipertahankan, urut dan nggak tumpang tindih."""
    segments: list[tuple[float, float]] = []
    cursor = 0.0
    for start, end in sorted(cuts):
        start = max(start, cursor)
        end = min(end, duration_s)
        if end <= start:
            continue
        if start > cursor:
            segments.append((cursor, start))
        cursor = end
    if cursor < duration_s:
        segments.append((cursor, duration_s))
    return segments


def shift_time(t: float, cuts: list[tuple[float, float]]) -> float:
    """Waktu asli → waktu setelah potongan (buang berapa detik yang udah lewat)."""
    return t - sum(min(max(t - start, 0.0), end - start) for start, end in cuts)


def shift_alignment(alignment: dict, cuts: list[tuple[float, float]]) -> dict:
    """Geser semua timestamp karakter; struktur alignment nggak diubah."""
    if not cuts:
        return alignment
    shifted = dict(alignment)
    for key in ("character_start_times_seconds", "character_end_times_seconds"):
        times = alignment.get(key)
        if isinstance(times, list):
            shifted[key] = [round(shift_time(float(t), cuts), 6) for t in times]
    return shifted


def detect_silences(path: Path, *, threshold_db: int = -35, min_s: float = 0.15,
                    run: Callable[[list[str]], str] | None = None) -> list[tuple[float, float]]:
    """Baca hening dari `silencedetect` ffmpeg (stderr-nya yang di-parse)."""
    import subprocess

    cmd = ["ffmpeg", "-hide_banner", "-i", str(path),
           "-af", f"silencedetect=noise={threshold_db}dB:d={min_s}", "-f", "null", "NUL"]
    if run is not None:
        return parse_silences(run(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg silencedetect gagal:\n{result.stderr[-800:]}")
    return parse_silences(result.stderr)


def trim_audio(src: Path, dst: Path, segments: list[tuple[float, float]],
               run: Callable[[list[str], str], object]) -> None:
    """Potong audio sesuai `segments` pakai ffmpeg (atrim + concat), tulis ke `dst`."""
    if not segments:
        raise ValueError("nggak ada segmen yang dipertahankan")
    parts = []
    labels = []
    for i, (start, end) in enumerate(segments):
        parts.append(f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[a{i}]")
        labels.append(f"[a{i}]")
    graph = ";".join(parts) + f";{''.join(labels)}concat=n={len(segments)}:v=0:a=1[out]"
    codec = ["-c:a", "libmp3lame", "-b:a", "192k"] if dst.suffix.lower() == ".mp3" else []
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-filter_complex", graph,
         "-map", "[out]", *codec, str(dst)], "tts")
