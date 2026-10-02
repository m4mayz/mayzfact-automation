"""Config dari .env + environment variable."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from dotenv import dotenv_values

from mayzfact.errors import PipelineError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"
CACHE_DIR = PROJECT_ROOT / "cache"
BROWSER_PROFILES_DIR = PROJECT_ROOT / "browser-profiles"


@dataclass(frozen=True)
class Settings:
    gemini_api_keys: tuple[str, ...] = ()
    gemini_model: str = "gemini-3.8-flash"
    elevenlabs_api_keys: tuple[str, ...] = ()
    elevenlabs_voice_id: str = ""
    elevenlabs_model: str = "eleven_v3"
    pexels_api_key: str = ""
    pixabay_api_key: str = ""
    target_duration_ratio: float = 0.6
    min_duration_seconds: float = 32.0
    max_shot_seconds: float = 2.5
    photo_ratio: float = 0.3
    fg_min_height_ratio: float = 0.5
    hook_seconds: float = 10.0
    hook_exact_threshold: float = 0.85
    hook_platforms: tuple[str, ...] = ("tiktok", "douyin", "rednote", "pinterest")
    browser_headless: bool = False


def _key_list(raw: str) -> tuple[str, ...]:
    """Beberapa API key dipisah koma, misal `key1,key2`."""
    return tuple(key.strip() for key in raw.split(",") if key.strip())


_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _flag(raw: str) -> bool:
    value = raw.lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(raw)


ENV_FIELDS: dict[str, tuple[str, Callable[[str], object]]] = {
    "GEMINI_API_KEYS": ("gemini_api_keys", _key_list),
    "GEMINI_MODEL": ("gemini_model", str),
    "ELEVENLABS_API_KEYS": ("elevenlabs_api_keys", _key_list),
    "ELEVENLABS_VOICE_ID": ("elevenlabs_voice_id", str),
    "ELEVENLABS_MODEL": ("elevenlabs_model", str),
    "PEXELS_API_KEY": ("pexels_api_key", str),
    "PIXABAY_API_KEY": ("pixabay_api_key", str),
    "TARGET_DURATION_RATIO": ("target_duration_ratio", float),
    "MIN_DURATION_SECONDS": ("min_duration_seconds", float),
    "MAX_SHOT_SECONDS": ("max_shot_seconds", float),
    "PHOTO_RATIO": ("photo_ratio", float),
    "FG_MIN_HEIGHT_RATIO": ("fg_min_height_ratio", float),
    "HOOK_SECONDS": ("hook_seconds", float),
    "HOOK_EXACT_THRESHOLD": ("hook_exact_threshold", float),
    "HOOK_PLATFORMS": ("hook_platforms", _key_list),
    "BROWSER_HEADLESS": ("browser_headless", _flag),
}


def settings_from_env(env: Mapping[str, str | None]) -> Settings:
    values: dict[str, object] = {}
    for env_name, (field_name, cast) in ENV_FIELDS.items():
        raw = (env.get(env_name) or "").strip()
        if not raw:
            continue
        try:
            values[field_name] = cast(raw)
        except ValueError as exc:
            raise PipelineError("config", f"{env_name} nilainya nggak valid: {raw!r}") from exc
    return Settings(**values)


def load_settings(env_file: Path = PROJECT_ROOT / ".env") -> Settings:
    """Isi .env jadi default. Environment variable beneran (termasuk yang kosong) menang."""
    merged: dict[str, str | None] = dict(dotenv_values(env_file)) if env_file.exists() else {}
    merged.update({name: os.environ[name] for name in ENV_FIELDS if name in os.environ})
    return settings_from_env(merged)


def missing_env(settings: Settings, names: list[str]) -> list[str]:
    missing: list[str] = []
    for name in names:
        field_name, _ = ENV_FIELDS[name]
        if not getattr(settings, field_name) and name not in missing:
            missing.append(name)
    return missing
