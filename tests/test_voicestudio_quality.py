import io
import json
import wave

import httpx
import pytest

from mayzfact.config import Settings
from mayzfact.errors import PipelineError
from mayzfact.pipeline import real_deps
from mayzfact.providers.voicestudio import VoiceStudioTTS


def wav_bytes():
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(bytes(24000 * 2 * 3))
    return out.getvalue()


def test_native_wav_and_direction_reach_api_and_do_not_reuse_other_take(tmp_path, sine_mp3):
    native = wav_bytes()
    calls = []

    def handle(request):
        if request.url.path == "/profiles":
            return httpx.Response(200, json=[{"id": "gen-id", "name": "Gen"}])
        if request.url.path == "/v1/audio/speech":
            body = json.loads(request.content)
            calls.append(body)
            assert not ({"num_step", "guidance_scale", "temperature", "class_temperature"} & body.keys())
            assert body["voice"] == "gen-id" and body["speed"] == 1.0 and body["seed"] == 0
            if body["response_format"] == "wav":
                return httpx.Response(200, content=native, headers={"content-type": "audio/wav"})
            return httpx.Response(200, content=sine_mp3.read_bytes(), headers={"content-type": "audio/mpeg"})
        assert b"audio/wav" in request.content or b"audio/mpeg" in request.content
        return httpx.Response(200, json={"words": [{"word": "Hello", "start": 0.1, "end": 0.4}]})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        def make(direction, kind):
            return VoiceStudioTTS("http://127.0.0.1:3900", "Gen", "cosyvoice", client,
                                  cache_dir=tmp_path, instruct=direction, audio_format=kind)

        control = make("", "wav")
        expressive = make("Speak with lively natural intonation.", "wav")
        assert control.synthesize("Hello")[0] == native
        assert expressive.synthesize("Hello")[0] == native
        expressive.synthesize("Hello")
        make("Speak with lively natural intonation.", "mp3").synthesize("Hello")
        assert control.cache_identity != expressive.cache_identity
        assert expressive.audio_format == "wav"
    assert len(calls) == 3
    assert calls[0].get("instruct", "") == ""
    assert calls[1]["instruct"] == "Speak with lively natural intonation."
    assert len(list(tmp_path.glob("*/voice.wav"))) == 2


def test_factory_forwards_local_quality_options():
    deps = real_deps(Settings(tts_provider="voicestudio", voicestudio_voice="Gen",
                              voicestudio_audio_format="wav", voicestudio_instruct="Speak expressively."))
    try:
        provider = deps.tts()
        assert provider.audio_format == "wav"
        assert provider.instruct == "Speak expressively."
    finally:
        deps.close()


@pytest.mark.parametrize("kind", ["../../voice", "aac", "WAV"])
def test_unknown_audio_format_rejected_before_request(tmp_path, kind):
    with httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail("No request allowed"))) as client:
        with pytest.raises(PipelineError):
            VoiceStudioTTS("http://127.0.0.1:3900", "Gen", "cosyvoice", client,
                           cache_dir=tmp_path, audio_format=kind)
