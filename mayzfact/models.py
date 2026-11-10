"""Schema naskah (ditulis agent ke runs/<id>/script.json) yang dipakai step-step setelahnya."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CtaScene(BaseModel):
    """Ilustrasi CTA yang diputar sebagai scene besar."""

    model_config = ConfigDict(extra="forbid")
    theme: Literal["volcano", "unicorn", "honey", "puppy", "lion", "shark"]
    transform_word: str = Field(min_length=1, max_length=40, pattern=r"^\w+$")
    comment_text: str = Field(min_length=1, max_length=24, pattern=r"\S")


class Beat(BaseModel):
    text: str
    media: Literal["video", "photo"]
    queries: list[str]
    subject: str = ""  # hewan/objek yang lagi dibahas, dipakai buat nilai relevansi klip
    point: bool = False  # beat ngajak lihat sesuatu di layar → panah/lingkaran (Fase 3C-2)
    emoji: str = ""  # emoji animasi di atas caption, dari daftar mayzfact.emoji.EMOJI
    emoji_word: str = ""  # kata di beat ini tempat emoji muncul
    queries_zh: list[str] = []  # versi Mandarin buat nyari di Douyin, ditulis agent
    keyword: str = ""  # kata di beat ini yang dikasih highlight, dipakai format faktacuil


class HookQuery(BaseModel):
    en: list[str] = []
    zh: list[str] = []


class Script(BaseModel):
    narration_mode: Literal["top3", "faktacuil"]  # pemilih format; format channel lain nanti nambah nilai di sini (D-050)
    approved_word_count: int | None = Field(default=None, strict=True, ge=1, le=500)
    cta_scene: CtaScene
    beats: list[Beat]
    bgm: str = ""  # sisa lama, nggak dipakai: BGM selalu mystery.mp3 (hook) + main.mp3 (D-038)
    hook_queries: dict[str, HookQuery] = {}  # per index segmen hook (plan/seg_XX), ditulis agent
