"""Schema naskah (ditulis agent ke runs/<id>/script.json) yang dipakai step-step setelahnya."""

import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Stiker FaktaCuil dipisah dari tema top3 biar stiker baru FaktaCuil nggak ikut ke top3 (D-061).
FaktaCuilTheme = Literal["volcano", "unicorn", "honey", "puppy", "lion", "shark", "toilet", "cat", "zebra"]


def _is_emoji(value: str) -> bool:
    """1-16 karakter, tanpa ASCII/spasi, karakter pertama kategori So (emoji)."""
    return (1 <= len(value) <= 16 and not any(c.isascii() or c.isspace() for c in value)
            and unicodedata.category(value[0]) == "So")


class CtaScene(BaseModel):
    """Ilustrasi CTA top3 yang diputar sebagai scene besar. FaktaCuil pakai FaktaCuilCtaScene."""

    model_config = ConfigDict(extra="forbid")
    theme: Literal["volcano", "unicorn", "honey", "puppy", "lion", "shark", "toilet", "cat", "zebra"]
    transform_word: str = Field(min_length=1, max_length=40, pattern=r"^\w+$")
    comment_text: str = Field(min_length=1, max_length=24, pattern=r"\S")


class FaktaCuilCtaScene(BaseModel):
    """CTA FaktaCuil v2: tengah (lucky/subscribe) atau akhir (emoji), opsional."""

    model_config = ConfigDict(extra="forbid")
    format: Literal["lucky", "subscribe", "emoji"]
    theme: FaktaCuilTheme | None = None
    emoji: str = ""

    @model_validator(mode="after")
    def _fields_match_format(self):
        if self.format == "emoji":
            if self.theme is not None:
                raise ValueError("emoji CTA must not set theme.")
            if not _is_emoji(self.emoji):
                raise ValueError("emoji CTA needs one emoji character (a single pictograph).")
        else:
            if self.theme is None:
                raise ValueError(f"{self.format} CTA needs a sticker theme.")
            if self.emoji:
                raise ValueError(f"{self.format} CTA must not set emoji.")
        return self


class CtaQuiz(BaseModel):
    """CTA-2: kuis hitung kata. `answer` dicek check-script dan dipakai metadata, bukan render."""

    model_config = ConfigDict(extra="forbid")
    word: str = Field(min_length=1, max_length=40, pattern=r"^[\w-]+$")
    answer: int = Field(strict=True, ge=1, le=99)


class Beat(BaseModel):
    text: str
    media: Literal["video", "photo"]
    queries: list[str]
    subject: str = ""  # hewan/objek yang lagi dibahas, dipakai buat nilai relevansi klip
    point: bool = False  # beat ngajak lihat sesuatu di layar → panah/lingkaran (Fase 3C-2)
    emoji: str = ""  # emoji animasi di atas caption, dari daftar mayzfact.emoji.EMOJI
    emoji_word: str = ""  # kata di beat ini tempat emoji muncul
    queries_zh: list[str] = []  # versi Mandarin buat nyari di Douyin, ditulis agent (diabaikan FaktaCuil)
    keyword: str = ""  # kata di beat ini yang dikasih highlight, dipakai format faktacuil


class HookQuery(BaseModel):
    en: list[str] = []
    zh: list[str] = []


class Script(BaseModel):
    narration_mode: Literal["top3", "faktacuil"]  # pemilih format; format channel lain nanti nambah nilai di sini (D-050)
    approved_word_count: int | None = Field(default=None, strict=True, ge=1, le=500)
    cta_scene: CtaScene | FaktaCuilCtaScene | None = None
    cta_quiz: CtaQuiz | None = None
    beats: list[Beat]
    bgm: str = ""  # sisa lama, nggak dipakai: BGM selalu mystery.mp3 (hook) + main.mp3 (D-038)
    hook_queries: dict[str, HookQuery] = {}  # per index segmen hook (plan/seg_XX), ditulis agent

    @field_validator("cta_scene", mode="before")
    @classmethod
    def _pick_scene_model(cls, value, info):
        # Union bikin error cabang lain nutupin alasan asli; validasi pakai model sesuai narration_mode duluan.
        if not isinstance(value, dict):
            return value
        model = {"faktacuil": FaktaCuilCtaScene, "top3": CtaScene}.get(info.data.get("narration_mode"))
        return model.model_validate(value) if model else value

    @model_validator(mode="after")
    def _cta_matches_mode(self):
        if self.narration_mode == "top3":
            if not isinstance(self.cta_scene, CtaScene):
                raise ValueError("Top 3 scripts need their own cta_scene (theme, transform_word, comment_text) (D-050).")
            if self.cta_quiz is not None:
                raise ValueError("Top 3 scripts must not set cta_quiz.")
        elif isinstance(self.cta_scene, CtaScene):
            raise ValueError("FaktaCuil cta_scene must not use transform_word/comment_text or a removed format; "
                             "use format lucky, subscribe, or emoji (D-061).")
        return self
