from mayzfact.steps.tts import run_tts
from mayzfact.store import RunPaths, read_json
from mayzfact.text import text_hash
from tests.factories import fake_alignment

SCRIPT = {
    "beats": [
        {"text": "Look at this.", "media": "video", "queries": ["crab"]},
        {"text": "It is old.", "media": "photo", "queries": ["fossil"]},
    ],
    "fallback_query": "animals",
}


class FakeTTS:
    voice_id = "voice123"
    model_id = "eleven_v3"

    def __init__(self, audio: bytes):
        self.audio = audio
        self.texts: list[str] = []

    def synthesize(self, text: str):
        self.texts.append(text)
        return self.audio, fake_alignment(text, 2.4)


def test_run_tts_writes_voice_and_metadata(tmp_path, sine_mp3):
    paths = RunPaths(tmp_path)
    tts = FakeTTS(sine_mp3.read_bytes())
    logs: list[str] = []
    data = run_tts(paths, SCRIPT, tts, log=logs.append)

    assert tts.texts == ["Look at this. It is old."]
    assert paths.voice_mp3.read_bytes() == sine_mp3.read_bytes()
    saved = read_json(paths.tts_json)
    assert saved == data
    assert saved["text_sha256"] == text_hash("Look at this. It is old.")
    assert saved["characters"] == 24
    assert (saved["voice_id"], saved["model_id"]) == ("voice123", "eleven_v3")
    assert abs(saved["duration_s"] - 3.0) < 0.15
    assert saved["alignment"]["characters"][0] == "L"
    assert "24 karakter" in logs[0]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["tts.json", "voice.mp3"]


def test_failed_measure_does_not_bill_elevenlabs_twice(tmp_path, sine_mp3):
    from mayzfact.errors import PipelineError

    paths = RunPaths(tmp_path)
    tts = FakeTTS(sine_mp3.read_bytes())

    def broken_measure(path):
        raise PipelineError("tts", "ffprobe gagal")

    import pytest

    with pytest.raises(PipelineError):
        run_tts(paths, SCRIPT, tts, log=lambda m: None, measure=broken_measure)
    assert not paths.voice_mp3.exists()

    run_tts(paths, SCRIPT, tts, log=lambda m: None)
    assert len(tts.texts) == 1
    assert paths.voice_mp3.read_bytes() == sine_mp3.read_bytes()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["tts.json", "voice.mp3"]
