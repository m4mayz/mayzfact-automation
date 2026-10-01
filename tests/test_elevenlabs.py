import base64
import json

import httpx

from mayzfact.providers.elevenlabs import ElevenLabsTTS, list_voices

ALIGNMENT = {"characters": ["H", "i"], "character_start_times_seconds": [0.0, 0.1], "character_end_times_seconds": [0.1, 0.2]}


def test_synthesize_calls_with_timestamps_endpoint():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"audio_base64": base64.b64encode(b"ID3audio").decode(), "alignment": ALIGNMENT})

    tts = ElevenLabsTTS("secret", "voice123", "eleven_v3", httpx.Client(transport=httpx.MockTransport(handler)))
    audio, alignment = tts.synthesize("Hi")
    assert audio == b"ID3audio"
    assert alignment == ALIGNMENT
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/text-to-speech/voice123/with-timestamps"
    assert request.url.params["output_format"] == "mp3_44100_128"
    assert request.headers["xi-api-key"] == "secret"
    assert json.loads(request.content) == {"text": "Hi", "model_id": "eleven_v3"}


def test_list_voices_normalizes_labels():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"voices": [
            {"voice_id": "abc", "name": "Mark", "labels": {"gender": "male", "accent": "american"}},
            {"voice_id": "def", "name": "Ria", "labels": None},
        ]})

    voices = list_voices("secret", httpx.Client(transport=httpx.MockTransport(handler)))
    assert voices == [
        {"voice_id": "abc", "name": "Mark", "labels": {"gender": "male", "accent": "american"}},
        {"voice_id": "def", "name": "Ria", "labels": {}},
    ]
    assert seen[0].url.path == "/v1/voices"
    assert seen[0].headers["xi-api-key"] == "secret"
