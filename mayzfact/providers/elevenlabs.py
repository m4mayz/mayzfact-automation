"""Client ElevenLabs: TTS dengan timestamp per karakter + list voice di akun."""

from __future__ import annotations

import base64

import httpx

from mayzfact.net import request_json

TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
VOICES_URL = "https://api.elevenlabs.io/v1/voices"
OUTPUT_FORMAT = "mp3_44100_128"


class ElevenLabsTTS:
    def __init__(self, api_key: str, voice_id: str, model_id: str, client: httpx.Client) -> None:
        self._api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self._client = client

    def synthesize(self, text: str) -> tuple[bytes, dict]:
        body = request_json(
            self._client,
            "POST",
            TTS_URL.format(voice_id=self.voice_id),
            step="tts",
            params={"output_format": OUTPUT_FORMAT},
            headers={"xi-api-key": self._api_key},
            json={"text": text, "model_id": self.model_id},
            timeout=180.0,
        )
        return base64.b64decode(body["audio_base64"]), body["alignment"]


def list_voices(api_key: str, client: httpx.Client) -> list[dict]:
    body = request_json(client, "GET", VOICES_URL, step="voices", headers={"xi-api-key": api_key})
    return [
        {"voice_id": v["voice_id"], "name": v.get("name", ""), "labels": v.get("labels") or {}}
        for v in body.get("voices", [])
    ]
