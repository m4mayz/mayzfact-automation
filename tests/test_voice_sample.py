import pytest

from mayzfact import cli
from mayzfact.config import Settings
from mayzfact.faktacuil import VOICE_SAMPLE_TEXT_ID
from mayzfact.text import words


def test_voice_sample_writes_mp3_and_reports_tempo(monkeypatch, tmp_path, capsys):
    calls = []

    class Fake:
        def __init__(self, keys, voice_id, model_id, client, stability=None, delivery_tag=""):
            calls.append((voice_id, model_id, stability, delivery_tag))

        def synthesize(self, text):
            assert text == VOICE_SAMPLE_TEXT_ID
            return b"ID3fake", {}

    monkeypatch.setattr(cli, "ElevenLabsTTS", Fake)
    monkeypatch.setattr(cli, "VOICE_SAMPLE_DIR", tmp_path)
    monkeypatch.setattr(cli, "audio_duration", lambda path: 16.0)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(elevenlabs_api_keys=("k",)))
    assert cli.main(["voice-sample", "VOICE123", "--name", "cewek-1"]) == 0
    assert (tmp_path / "cewek-1.mp3").read_bytes() == b"ID3fake"
    assert calls == [("VOICE123", "eleven_v3", 0.5, "")]
    out = capsys.readouterr().out
    assert "kata/detik" in out and f"{len(words(VOICE_SAMPLE_TEXT_ID)) / 16.0:.2f}" in out


def test_voice_sample_refuses_to_overwrite(monkeypatch, tmp_path, capsys):
    (tmp_path / "cewek-1.mp3").write_bytes(b"old")
    monkeypatch.setattr(cli, "VOICE_SAMPLE_DIR", tmp_path)
    monkeypatch.setattr(cli, "ElevenLabsTTS", lambda *a, **k: pytest.fail("nggak boleh request"))
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(elevenlabs_api_keys=("k",)))
    assert cli.main(["voice-sample", "VOICE123", "--name", "cewek-1"]) == 1
    assert (tmp_path / "cewek-1.mp3").read_bytes() == b"old"


def test_voice_sample_rejects_unsafe_name(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "VOICE_SAMPLE_DIR", tmp_path)
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(elevenlabs_api_keys=("k",)))
    assert cli.main(["voice-sample", "VOICE123", "--name", "../x"]) == 1
