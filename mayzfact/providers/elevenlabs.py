"""Client ElevenLabs: TTS dengan timestamp per karakter + list voice di akun."""

from __future__ import annotations

import base64
from typing import Callable, Sequence

import httpx

from mayzfact.errors import PipelineError
from mayzfact.net import HttpStatusError, request_json

TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
VOICES_URL = "https://api.elevenlabs.io/v1/voices"
OUTPUT_FORMAT = "mp3_44100_128"
# Status yang artinya "key ini nggak bisa dipakai" (kuota habis, key salah, izin kurang): coba key berikutnya.
KEY_REJECTED_STATUS = {401, 402, 403}


def _with_key_fallback(api_keys: Sequence[str], step: str, call: Callable[[str], dict]) -> dict:
    if not api_keys:
        raise PipelineError(step, "Isi dulu di .env: ELEVENLABS_API_KEYS")
    reasons: list[str] = []
    for number, key in enumerate(api_keys, start=1):
        try:
            return call(key)
        except HttpStatusError as exc:
            if exc.status not in KEY_REJECTED_STATUS:
                raise
            reasons.append(f"key #{number}: HTTP {exc.status}")
    raise PipelineError(step, f"Semua {len(api_keys)} key ElevenLabs ditolak ({'; '.join(reasons)}).")


class ElevenLabsTTS:
    def __init__(
        self, api_keys: Sequence[str], voice_id: str, model_id: str, client: httpx.Client,
        stability: float | None = None, delivery_tag: str = ""
    ) -> None:
        self._api_keys = list(api_keys)
        self.voice_id = voice_id
        self.model_id = model_id
        self.stability = stability
        self.delivery_tag = delivery_tag
        self._client = client

    @property
    def cache_identity(self) -> dict:
        identity = {"provider": "elevenlabs", "voice_id": self.voice_id,
                    "model_id": self.model_id, "stability": self.stability}
        if self.delivery_tag:
            identity["delivery_tag"] = self.delivery_tag
        return identity

    def synthesize(self, text: str) -> tuple[bytes, dict]:
        request_text = f"[{self.delivery_tag}] {text}" if self.delivery_tag else text
        body: dict = {"text": request_text, "model_id": self.model_id}
        if self.stability is not None:
            # v3: 0.0 Creative, 0.5 Natural, 1.0 Robust. None = setting bawaan voice di akun.
            body["voice_settings"] = {"stability": self.stability}

        def call(key: str) -> dict:
            return request_json(
                self._client,
                "POST",
                TTS_URL.format(voice_id=self.voice_id),
                step="tts",
                idempotent=False,
                params={"output_format": OUTPUT_FORMAT},
                headers={"xi-api-key": key},
                json=body,
                timeout=180.0,
            )

        body = _with_key_fallback(self._api_keys, "tts", call)
        return base64.b64decode(body["audio_base64"]), body["alignment"]

    def normalize_alignment(self, text: str, alignment: dict) -> dict:
        # Dipanggil run_tts sesudah audio + alignment mentah aman di disk.
        if not self.delivery_tag:
            return alignment
        error = PipelineError("tts", "Alignment ElevenLabs nggak cocok sama teks asli atau panjang array. "
                              "voice.incoming.mp3 aman; perbaiki mapping, jangan generate ulang suara.")
        keys = ("characters", "character_start_times_seconds", "character_end_times_seconds")
        if not isinstance(alignment, dict) or not all(isinstance(alignment.get(key), list) for key in keys):
            raise error
        chars = alignment["characters"]
        if any(len(alignment[key]) != len(chars) for key in keys):
            raise error
        for prefix in (f"[{self.delivery_tag}] ", f"[{self.delivery_tag}]", ""):
            if chars == list(prefix + text):
                # Slicing seragam saja: timestamp ucapan tetap persis dari provider.
                return {**alignment, **{key: alignment[key][len(prefix):] for key in keys}}
        raise error


def list_voices(api_keys: Sequence[str], client: httpx.Client) -> list[dict]:
    body = _with_key_fallback(
        api_keys, "voices", lambda key: request_json(client, "GET", VOICES_URL, step="voices", headers={"xi-api-key": key})
    )
    return [
        {"voice_id": v["voice_id"], "name": v.get("name", ""), "labels": v.get("labels") or {}}
        for v in body.get("voices", [])
    ]
