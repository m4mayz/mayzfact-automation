"""Config: setting biasa di kode, rahasia dari .env + environment variable."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping

from dotenv import dotenv_values

from mayzfact.errors import PipelineError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"
CACHE_DIR = PROJECT_ROOT / "cache"
MODELS_DIR = PROJECT_ROOT / "models"  # cache model ML (SigLIP, OWLv2), di-gitignore


@dataclass(frozen=True)
class Settings:
    # Setting biasa: ubah langsung di sini (bukan lewat .env), biar harness mana pun bisa ngeditnya.
    elevenlabs_voice_id: str = "TX3LPaxmHKxFdv7VOQHJ"
    elevenlabs_model: str = "eleven_v3"
    # 1.0 = "Robust": nada antar kalimat konsisten. Default voice bikin tiap beat kedengeran ganti konteks (D-036).
    elevenlabs_stability: float = 1.0
    target_duration_ratio: float = 0.8
    min_duration_seconds: float = 32.0
    max_shot_seconds: float = 4.0
    fg_min_height_ratio: float = 0.5
    hook_seconds: float = 10.0
    brief_port: int = 3100
    # Rahasia: cuma dari .env, jangan pernah di-print.
    elevenlabs_api_keys: tuple[str, ...] = field(default=(), repr=False)
    youtube_client_secret_json: str = field(default="", repr=False)  # JSON OAuth client
    youtube_token_json: str = field(default="", repr=False)
    ngrok_basic_auth: str = field(default="", repr=False)  # user:password buat tunnel ngrok


def _key_list(raw: str) -> tuple[str, ...]:
    """Beberapa API key dipisah koma, misal `key1,key2`."""
    return tuple(key.strip() for key in raw.split(",") if key.strip())


# .env cuma buat rahasia. Setting lain ada di default Settings di atas.
ENV_FIELDS: dict[str, tuple[str, Callable[[str], object]]] = {
    "ELEVENLABS_API_KEYS": ("elevenlabs_api_keys", _key_list),
    "YOUTUBE_CLIENT_SECRET_JSON": ("youtube_client_secret_json", str),
    "YOUTUBE_TOKEN_JSON": ("youtube_token_json", str),
    "NGROK_BASIC_AUTH": ("ngrok_basic_auth", str),
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
