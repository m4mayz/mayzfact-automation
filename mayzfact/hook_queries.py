"""Query search per segmen hook: dari Gemini vision, fallback dari transcript (spec Fase 2 4.3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Protocol

from google.genai import types

from mayzfact.errors import PipelineError
from mayzfact.models import HookQueries
from mayzfact.text import words

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "hook_queries.md"
FALLBACK_WORDS = 8
MAX_QUERIES = 2


class HookQueryWriter(Protocol):
    def generate(self, system: str, contents: Any, schema: type, step: str = "script") -> Any: ...


def transcript_near(transcript: list[dict], start_s: float, end_s: float) -> str:
    return " ".join(s["text"] for s in transcript if s["start"] < end_s and s["start"] + s["duration"] > start_s)


def fallback_queries(infos: list[dict]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for info in infos:
        snippet = " ".join(words(info["transcript"])[:FALLBACK_WORDS])
        out[info["index"]] = {"en": [snippet] if snippet else [], "zh": []}
    return out


def build_contents(infos: list[dict], frames: list[Path]) -> list:
    parts: list = ["Write search queries for every segment below."]
    for info, frame in zip(infos, frames, strict=True):
        parts.append(
            f"Segment {info['index']} ({info['start_s']:.1f}s-{info['end_s']:.1f}s). Narration: {info['transcript'] or '-'}"
        )
        parts.append(types.Part.from_bytes(data=frame.read_bytes(), mime_type="image/jpeg"))
    return parts


def _clean(queries: list[str]) -> list[str]:
    return [q.strip() for q in queries if q.strip()][:MAX_QUERIES]


def describe_segments(
    writer: HookQueryWriter | None,
    infos: list[dict],
    frames: list[Path],
    log: Callable[[str], None] = print,
) -> dict[int, dict]:
    fallback = fallback_queries(infos)
    if writer is None or not infos:
        return fallback
    try:
        result = writer.generate(PROMPT_PATH.read_text(encoding="utf-8"), build_contents(infos, frames), HookQueries, step="hook")
    except PipelineError as exc:
        log(f"[hook] Gemini gagal bikin query, pakai transcript: {exc.message[:120]}")
        return fallback
    out = dict(fallback)
    for segment in result.segments:
        if segment.index in out:
            out[segment.index] = {"en": _clean(segment.en) or fallback[segment.index]["en"], "zh": _clean(segment.zh)}
    return out


TRANSLATE_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "translate_queries.md"


def translate_queries(writer: HookQueryWriter | None, queries: list[str], log: Callable[[str], None] = print) -> dict[str, str]:
    if writer is None or not queries:
        return {}
    from mayzfact.models import Translations

    try:
        result = writer.generate(
            TRANSLATE_PROMPT_PATH.read_text(encoding="utf-8"), json.dumps(queries, ensure_ascii=False), Translations, step="plan"
        )
    except PipelineError as exc:
        log(f"[plan] Gemini gagal nerjemahin keyword, kolom 中文 dikosongin: {exc.message[:120]}")
        return {}
    wanted = set(queries)
    return {item.en: item.zh.strip() for item in result.items if item.en in wanted and item.zh.strip()}
