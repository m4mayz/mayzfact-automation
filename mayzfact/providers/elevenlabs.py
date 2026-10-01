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
    def __init__(self, api_keys: Sequence[str], voice_id: str, model_id: str, client: httpx.Client) -> None:
        self._api_keys = list(api_keys)
        self.voice_id = voice_id
        self.model_id = model_id
        self._client = client

    def synthesize(self, text: str) -> tuple[bytes, dict]:
        def call(key: str) -> dict:
            return request_json(
                self._client,
                "POST",
                TTS_URL.format(voice_id=self.voice_id),
                step="tts",
                idempotent=False,
                params={"output_format": OUTPUT_FORMAT},
                headers={"xi-api-key": key},
                json={"text": text, "model_id": self.model_id},
                timeout=180.0,
            )

        body = _with_key_fallback(self._api_keys, "tts", call)
        return base64.b64decode(body["audio_base64"]), body["alignment"]


def list_voices(api_keys: Sequence[str], client: httpx.Client) -> list[dict]:
    body = _with_key_fallback(
        api_keys, "voices", lambda key: request_json(client, "GET", VOICES_URL, step="voices", headers={"xi-api-key": key})
    )
    return [
        {"voice_id": v["voice_id"], "name": v.get("name", ""), "labels": v.get("labels") or {}}
        for v in body.get("voices", [])
    ]
