"""Utilitas teks: bersihin naskah, hitung kata, overlap n-gram, hash."""

from __future__ import annotations

import hashlib
import re

_SIMPLE = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", " ": " "})
_EM_DASH = re.compile(r"\s*—\s*")
_WORD = re.compile(r"[a-z0-9']+")


def clean_text(text: str) -> str:
    """Tanda baca 'fancy' jadi ASCII + spasi dirapihin, biar teks ke TTS = karakter di alignment."""
    text = text.translate(_SIMPLE).replace("…", "...")
    text = _EM_DASH.sub(", ", text)
    return " ".join(text.split())


def words(text: str) -> list[str]:
    return _WORD.findall(clean_text(text).lower())


def ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def ngram_overlap(new_text: str, source_text: str, n: int = 4) -> float:
    """Porsi n-gram unik di naskah baru yang juga muncul di source (0.0 - 1.0)."""
    new_grams = ngrams(words(new_text), n)
    if not new_grams:
        return 0.0
    return len(new_grams & ngrams(words(source_text), n)) / len(new_grams)


def beat_texts(beats: list[dict]) -> list[str]:
    return [clean_text(beat["text"]) for beat in beats]


def script_text(beats: list[dict]) -> str:
    """Teks utuh yang dikirim ke TTS: teks beat yang udah bersih, digabung pakai 1 spasi."""
    return " ".join(beat_texts(beats))


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
