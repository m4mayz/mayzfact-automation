"""Schema naskah yang dipakai Gemini dan step-step setelahnya."""

from typing import Literal

from pydantic import BaseModel


class Beat(BaseModel):
    text: str
    media: Literal["video", "photo"]
    queries: list[str]


class Script(BaseModel):
    beats: list[Beat]
    fallback_query: str


class SegmentQueries(BaseModel):
    index: int
    en: list[str]
    zh: list[str]


class HookQueries(BaseModel):
    segments: list[SegmentQueries]
