"""Schema naskah (ditulis agent ke runs/<id>/script.json) yang dipakai step-step setelahnya."""

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
    queries_zh: list[str] = []  # versi Mandarin buat nyari di Douyin, ditulis agent


class HookQuery(BaseModel):
    en: list[str] = []
    zh: list[str] = []


class Script(BaseModel):
    beats: list[Beat]
    bgm: str = ""  # nama file di assets/bgm, dipilih agent; "" = tanpa BGM
    hook_queries: dict[str, HookQuery] = {}  # per index segmen hook (plan/seg_XX), ditulis agent
