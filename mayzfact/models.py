"""Schema naskah (ditulis agent ke runs/<id>/script.json) yang dipakai step-step setelahnya."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CtaScene(BaseModel):
    """Ilustrasi CTA; kartu kata hanya tetap terbaca untuk run legacy."""

    model_config = ConfigDict(extra="forbid")
    theme: Literal["volcano", "word", "unicorn", "honey", "puppy", "lion", "shark"]
    transform_word: str = Field(min_length=1, max_length=40, pattern=r"^\w+$")
    comment_text: str = Field(min_length=1, max_length=24, pattern=r"\S")
    label: str = Field(default="", max_length=24)

    @model_validator(mode="after")
    def check_label(self):
        if self.theme == "word" and not self.label.strip():
            raise ValueError("theme word butuh label visual")
        return self


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
    narration_mode: Literal["source", "top3"] = "source"  # run lama tanpa field ini tetap pakai aturan source
    approved_word_count: int | None = Field(default=None, strict=True, ge=1, le=500)
    cta_scene: CtaScene | None = None  # opt-in visual saja; nggak masuk hash teks/audio
    beats: list[Beat]

    @model_validator(mode="after")
    def check_scene_mode(self):
        if self.cta_scene is not None and self.narration_mode != "top3":
            raise ValueError("cta_scene cuma untuk narration_mode top3")
        return self

    bgm: str = ""  # sisa lama, nggak dipakai: BGM selalu mystery.mp3 (hook) + main.mp3 (D-038)
    hook_queries: dict[str, HookQuery] = {}  # per index segmen hook (plan/seg_XX), ditulis agent
