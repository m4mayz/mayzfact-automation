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

    tts = ElevenLabsTTS(["secret"], "voice123", "eleven_v3", httpx.Client(transport=httpx.MockTransport(handler)))
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

    voices = list_voices(["secret"], httpx.Client(transport=httpx.MockTransport(handler)))
    assert voices == [
        {"voice_id": "abc", "name": "Mark", "labels": {"gender": "male", "accent": "american"}},
        {"voice_id": "def", "name": "Ria", "labels": {}},
    ]
    assert seen[0].url.path == "/v1/voices"
    assert seen[0].headers["xi-api-key"] == "secret"


def test_synthesize_does_not_retry_read_timeout():
    import pytest

    from mayzfact.errors import PipelineError

    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("slow", request=request)

    tts = ElevenLabsTTS(["secret"], "voice123", "eleven_v3", httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(PipelineError):
        tts.synthesize("Hi")
    assert len(calls) == 1


def _keyed_client(responses):
    seen = []

    def handler(request):
        key = request.headers["xi-api-key"]
        seen.append(key)
        status, body = responses[key]
        return httpx.Response(status, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


OK_BODY = {"audio_base64": base64.b64encode(b"ID3audio").decode(), "alignment": ALIGNMENT}
QUOTA = {"detail": {"status": "quota_exceeded", "message": "quota habis"}}


def test_synthesize_falls_back_to_next_key_on_quota():
    client, seen = _keyed_client({"k1": (401, QUOTA), "k2": (200, OK_BODY)})
    tts = ElevenLabsTTS(["k1", "k2"], "voice123", "eleven_v3", client)
    audio, _ = tts.synthesize("Hi")
    assert audio == b"ID3audio"
    assert seen == ["k1", "k2"]


def test_synthesize_does_not_switch_key_on_bad_request():
    import pytest

    from mayzfact.errors import PipelineError

    client, seen = _keyed_client({"k1": (400, {"detail": "bad text"}), "k2": (200, OK_BODY)})
    with pytest.raises(PipelineError, match="400"):
        ElevenLabsTTS(["k1", "k2"], "voice123", "eleven_v3", client).synthesize("Hi")
    assert seen == ["k1"]


def test_synthesize_reports_when_all_keys_fail_without_leaking_keys():
    import pytest

    from mayzfact.errors import PipelineError

    client, seen = _keyed_client({"k1": (401, QUOTA), "k2": (403, {"detail": "no permission"})})
    with pytest.raises(PipelineError, match="Semua 2 key") as exc:
        ElevenLabsTTS(["k1", "k2"], "voice123", "eleven_v3", client).synthesize("Hi")
    assert seen == ["k1", "k2"]
    assert "k1" not in str(exc.value) and "k2" not in str(exc.value)
