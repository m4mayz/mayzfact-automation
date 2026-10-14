"""Schema naskah yang dipakai Gemini dan step-step setelahnya."""

from typing import Literal

from pydantic import BaseModel


class Beat(BaseModel):
    text: str
    media: Literal["video", "photo"]
    queries: list[str]
    subject: str = ""  # hewan/objek yang lagi dibahas, dipakai buat nilai relevansi klip
    point: bool = False  # beat ngajak lihat sesuatu di layar → panah/lingkaran (Fase 3C-2)
    emoji: str = ""  # emoji animasi di atas caption, dari daftar mayzfact.emoji.EMOJI
    emoji_word: str = ""  # kata di beat ini tempat emoji muncul


class Script(BaseModel):
    beats: list[Beat]
    fallback_query: str


class SegmentQueries(BaseModel):
    index: int
    en: list[str]
    zh: list[str]


class HookQueries(BaseModel):
    segments: list[SegmentQueries]


class Translation(BaseModel):
    en: str
    zh: str


class Translations(BaseModel):
    items: list[Translation]


class BgmChoice(BaseModel):
    file: str


class BeatMark(BaseModel):
    index: int
    point: bool
    emoji: str
    emoji_word: str


class BeatMarks(BaseModel):
    items: list[BeatMark]
