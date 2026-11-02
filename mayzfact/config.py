"""Config: setting biasa di kode, rahasia dari .env + environment variable."""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import urlsplit

from dotenv import dotenv_values

from mayzfact.errors import PipelineError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"
CACHE_DIR = PROJECT_ROOT / "cache"
MODELS_DIR = PROJECT_ROOT / "models"  # cache model ML (SigLIP, OWLv2), di-gitignore


@dataclass(frozen=True)
class Settings:
    # Setting biasa: ubah langsung di sini (bukan lewat .env), biar harness mana pun bisa ngeditnya.
    tts_provider: str = "elevenlabs"  # override per-PC lewat settings.local.json, bukan .env
    voicestudio_url: str = "http://127.0.0.1:3900"
    voicestudio_voice: str = "default"  # isi nama/ID profil secara eksplisit di override lokal
    voicestudio_engine: str = "cosyvoice"
    voicestudio_instruct: str = ""  # arahan delivery, bukan tag di naskah/caption
    voicestudio_audio_format: str = "mp3"  # WAV opt-in lokal; default lama tetap
    voicestudio_timeout: float = 900.0  # model lokal cold-start bisa lama
    elevenlabs_voice_id: str = "TX3LPaxmHKxFdv7VOQHJ"
    elevenlabs_model: str = "eleven_v3"
    # D-047: sample 2 disetujui, Natural + tag delivery hanya di request provider.
    elevenlabs_stability: float = 0.5
    elevenlabs_delivery_tag: str = "calm"  # kosong = tanpa prefix, bukan isi naskah/caption
    video_speed: float = 1.1  # hasil render dipercepat (gambar + suara, nada tetap); 1.0 = normal (D-039, dulu 1,2)
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
    settings = settings_from_env(merged)
    local_file = env_file.with_name("settings.local.json")
    if not local_file.exists():
        return settings
    try:
        values = json.loads(local_file.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ValueError("harus object JSON")
        allowed = {"tts_provider", "voicestudio_url", "voicestudio_voice", "voicestudio_engine",
                   "voicestudio_timeout", "voicestudio_instruct", "voicestudio_audio_format",
                   "elevenlabs_delivery_tag", "elevenlabs_stability"}
        if values.keys() - allowed:
            raise ValueError("ada field di luar setting TTS yang didukung")
        for name, value in values.items():
            if name == "elevenlabs_delivery_tag":
                if (not isinstance(value, str) or len(value) > 64 or value != value.strip()
                        or any(char in "[]" or not char.isprintable() for char in value)):
                    raise ValueError("elevenlabs_delivery_tag harus kosong atau nama tag maksimal 64 karakter, "
                                     "tanpa bracket, control character atau spasi tepi")
            elif name == "elevenlabs_stability":
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError("elevenlabs_stability harus angka finite antara 0 dan 1")
            elif name == "voicestudio_timeout":
                if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                    raise ValueError("voicestudio_timeout harus angka positif")
            elif name == "voicestudio_instruct":
                if not isinstance(value, str) or len(value) > 4096:
                    raise ValueError("voicestudio_instruct harus teks maksimal 4096 karakter")
            elif not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} harus teks yang nggak kosong")
        settings = replace(settings, **values)
        if settings.tts_provider not in {"elevenlabs", "voicestudio"}:
            raise ValueError("tts_provider harus elevenlabs atau voicestudio")
        if settings.voicestudio_audio_format not in {"mp3", "wav"}:
            raise ValueError("voicestudio_audio_format harus mp3 atau wav")
        url = urlsplit(settings.voicestudio_url)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"}
                or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}):
            raise ValueError("voicestudio_url harus HTTP loopback lokal tanpa path/kredensial")
        return settings
    except (OSError, ValueError, TypeError) as exc:
        raise PipelineError("config", f"settings.local.json nggak valid: {exc}") from exc


def missing_env(settings: Settings, names: list[str]) -> list[str]:
    missing: list[str] = []
    for name in names:
        field_name, _ = ENV_FIELDS[name]
        if not getattr(settings, field_name) and name not in missing:
            missing.append(name)
    return missing
