"""Schema naskah yang dipakai Gemini dan step-step setelahnya."""

from typing import Literal

from pydantic import BaseModel


class Beat(BaseModel):
    text: str
    media: Literal["video", "photo"]
    queries: list[str]
    subject: str = ""  # hewan/objek yang lagi dibahas, dipakai buat nilai relevansi klip


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
