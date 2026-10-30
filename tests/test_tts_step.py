import io
import math
import struct
import wave

import pytest

from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import audio_duration
from mayzfact.steps.tts import run_tts
from mayzfact.store import RunPaths, read_json, write_json_atomic
from mayzfact.text import text_hash
from tests.factories import fake_alignment

SCRIPT = {
    "beats": [
        {"text": "Look at this.", "media": "video", "queries": ["crab"]},
        {"text": "It is old.", "media": "photo", "queries": ["fossil"]},
    ],
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


def test_tts_records_provider_without_logging_elevenlabs_for_local_voice(tmp_path, sine_mp3):
    tts = FakeTTS(sine_mp3.read_bytes())
    tts.provider_name = "voicestudio"
    logs = []
    result = run_tts(RunPaths(tmp_path), SCRIPT, tts, log=logs.append)
    assert result["provider"] == "voicestudio"
    assert "voicestudio" in logs[0]
    assert not any("ElevenLabs" in line for line in logs)


def test_pending_audio_from_different_provider_is_not_overwritten(tmp_path, sine_mp3):
    import pytest

    from mayzfact.errors import PipelineError

    paths = RunPaths(tmp_path)
    old = FakeTTS(sine_mp3.read_bytes())

    def broken_measure(path):
        raise RuntimeError("ffprobe gagal")

    with pytest.raises(RuntimeError):
        run_tts(paths, SCRIPT, old, log=lambda m: None, measure=broken_measure)
    new = FakeTTS(sine_mp3.read_bytes())
    new.provider_name = "voicestudio"
    with pytest.raises(PipelineError, match="tersimpan"):
        run_tts(paths, SCRIPT, new, log=lambda m: None)
    assert not new.texts
    assert (tmp_path / "voice.incoming.mp3").read_bytes() == sine_mp3.read_bytes()


def test_run_tts_records_voice_stability(tmp_path, sine_mp3):
    tts = FakeTTS(sine_mp3.read_bytes())
    tts.stability = 1.0
    data = run_tts(RunPaths(tmp_path), SCRIPT, tts, log=lambda _: None)
    assert data["stability"] == 1.0


@pytest.fixture
def sine_wav():
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440 * i / 24000)))
                                 for i in range(72000)))
    return output.getvalue()


class NativeWavTTS(FakeTTS):
    provider_name = "voicestudio"
    audio_format = "wav"


def test_native_wav_is_preserved_with_compatible_mp3(tmp_path, sine_wav):
    paths = RunPaths(tmp_path)
    tts = NativeWavTTS(sine_wav)
    measured = []

    def measure(path):
        measured.append(path)
        assert path.suffix == ".wav"
        assert path.read_bytes() == sine_wav
        return audio_duration(path)

    data = run_tts(paths, SCRIPT, tts, measure=measure, log=lambda _: None)

    assert (tmp_path / "voice.wav").read_bytes() == sine_wav
    assert data["audio_file"] == "voice.wav"
    assert data["duration_s"] == 3.0
    assert data["alignment"] == fake_alignment("Look at this. It is old.", 2.4)
    assert read_json(paths.tts_json) == data
    assert measured
    assert abs(audio_duration(paths.voice_mp3) - 3.0) < 0.15
    assert paths.voice_mp3.read_bytes() != sine_wav
    assert sorted(p.name for p in tmp_path.iterdir()) == ["tts.json", "voice.mp3", "voice.wav"]


def test_wav_ffmpeg_failure_retries_saved_native_without_synthesis(tmp_path, sine_wav, monkeypatch):
    import mayzfact.steps.tts as tts_step

    paths = RunPaths(tmp_path)
    tts = NativeWavTTS(sine_wav)
    real_run = tts_step._run

    def fail_ffmpeg(cmd, step):
        assert cmd[0] == "ffmpeg"
        assert (tmp_path / "voice.wav").read_bytes() == sine_wav
        assert read_json(paths.tts_json)["audio_file"] == "voice.wav"
        assert read_json(tmp_path / "tts.incoming.json")["alignment"]
        from pathlib import Path

        Path(cmd[-1]).write_bytes(b"partial mp3")
        raise PipelineError("tts", "ffmpeg gagal")

    monkeypatch.setattr(tts_step, "_run", fail_ffmpeg)
    with pytest.raises(PipelineError, match="ffmpeg gagal"):
        run_tts(paths, SCRIPT, tts, log=lambda _: None)
    assert not paths.voice_mp3.exists()
    assert (tmp_path / "voice.wav").read_bytes() == sine_wav
    assert len(tts.texts) == 1

    monkeypatch.setattr(tts_step, "_run", real_run)
    run_tts(paths, SCRIPT, tts, log=lambda _: None)
    assert len(tts.texts) == 1
    assert (tmp_path / "voice.wav").read_bytes() == sine_wav
    assert abs(audio_duration(paths.voice_mp3) - 3.0) < 0.15
    assert not (tmp_path / "tts.incoming.json").exists()


@pytest.mark.parametrize("audio_format", ["flac", "../wav", "../../outside", "", None, ["wav"]])
def test_unsupported_audio_format_is_rejected_before_synthesis_or_write(tmp_path, audio_format):
    tts = FakeTTS(b"never synthesize")
    tts.audio_format = audio_format
    with pytest.raises(PipelineError, match="audio_format"):
        run_tts(RunPaths(tmp_path), SCRIPT, tts, log=lambda _: None)
    assert not tts.texts
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("old_format,new_format", [("mp3", "wav"), ("wav", "mp3")])
def test_pending_audio_from_other_format_is_not_overwritten(tmp_path, sine_wav, old_format, new_format):
    paths = RunPaths(tmp_path)
    old = FakeTTS(sine_wav)
    old.audio_format = old_format

    def fail_measure(path):
        raise RuntimeError("ffprobe gagal")

    with pytest.raises(RuntimeError, match="ffprobe gagal"):
        run_tts(paths, SCRIPT, old, measure=fail_measure, log=lambda _: None)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    new = FakeTTS(sine_wav)
    new.audio_format = new_format
    with pytest.raises(PipelineError, match="tersimpan"):
        run_tts(paths, SCRIPT, new, log=lambda _: None)
    assert not new.texts
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


@pytest.mark.parametrize("existing,new_format", [
    (("voice.mp3",), "mp3"),
    (("voice.mp3",), "wav"),
    (("voice.wav",), "wav"),
    (("voice.wav",), "mp3"),
    (("voice.wav", "voice.incoming.wav"), "wav"),
])
def test_existing_voice_files_are_immutable(tmp_path, sine_wav, existing, new_format):
    for name in existing:
        (tmp_path / name).write_bytes(sine_wav)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    tts = FakeTTS(sine_wav)
    tts.audio_format = new_format
    with pytest.raises(PipelineError, match="tersimpan"):
        run_tts(RunPaths(tmp_path), SCRIPT, tts, log=lambda _: None)
    assert not tts.texts
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


@pytest.mark.parametrize("recorded_format", ["mp3", None])
def test_wav_pending_with_mp3_or_legacy_metadata_is_not_reused(tmp_path, sine_wav, recorded_format):
    tts = NativeWavTTS(sine_wav)
    (tmp_path / "voice.incoming.wav").write_bytes(sine_wav)
    pending = {
        "text_sha256": text_hash("Look at this. It is old."),
        "alignment": fake_alignment("Look at this. It is old.", 2.4),
        "identity": {"provider": "voicestudio", "voice_id": tts.voice_id,
                     "model_id": tts.model_id, "stability": None},
    }
    if recorded_format is not None:
        pending["audio_format"] = recorded_format
    write_json_atomic(tmp_path / "tts.incoming.json", pending)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(PipelineError, match="tersimpan"):
        run_tts(RunPaths(tmp_path), SCRIPT, tts, log=lambda _: None)
    assert not tts.texts
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_orphan_pending_metadata_is_not_overwritten(tmp_path, sine_wav):
    pending = tmp_path / "tts.incoming.json"
    write_json_atomic(pending, {"text_sha256": "different script", "audio_format": "mp3"})
    before = pending.read_bytes()
    tts = NativeWavTTS(sine_wav)
    with pytest.raises(PipelineError, match="tersimpan"):
        run_tts(RunPaths(tmp_path), SCRIPT, tts, log=lambda _: None)
    assert not tts.texts
    assert pending.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["tts.incoming.json"]


def test_plan_voice_onset_uses_native_wav_from_tts_metadata(tmp_path, sine_wav, monkeypatch):
    import mayzfact.voice_onset as onset
    from mayzfact.steps.plan import _voiced_words

    paths = RunPaths(tmp_path)
    data = run_tts(paths, SCRIPT, NativeWavTTS(sine_wav), log=lambda _: None)
    read_paths = []
    real_envelope = onset.voice_envelope

    def envelope(path):
        read_paths.append(path)
        return real_envelope(path)

    monkeypatch.setattr(onset, "voice_envelope", envelope)
    words = _voiced_words(paths, data, lambda _: None)
    assert words and words[0]["text"] == "Look"
    assert read_paths == [tmp_path / "voice.wav"]


def test_legacy_paid_mp3_pending_without_identity_or_format_is_resumed(tmp_path, sine_mp3):
    paths = RunPaths(tmp_path)
    (tmp_path / "voice.incoming.mp3").write_bytes(sine_mp3.read_bytes())
    text = "Look at this. It is old."
    write_json_atomic(tmp_path / "tts.incoming.json", {
        "text_sha256": text_hash(text), "alignment": fake_alignment(text, 2.4),
        "voice_id": "paid-voice", "model_id": "paid-model",
    })
    tts = FakeTTS(b"never synthesize")
    data = run_tts(paths, SCRIPT, tts, log=lambda _: None)
    assert not tts.texts
    assert paths.voice_mp3.read_bytes() == sine_mp3.read_bytes()
    assert (data["voice_id"], data["model_id"]) == ("paid-voice", "paid-model")
    assert data["audio_file"] == "voice.mp3"


def test_native_wav_flows_from_tts_to_remotion_timeline(tmp_path, sine_wav):
    from mayzfact.steps.timeline import run_timeline

    paths = RunPaths(tmp_path)
    tts = run_tts(paths, SCRIPT, NativeWavTTS(sine_wav), log=lambda _: None)
    clips = {"shots": [{"file": "clips/shot_01.mp4", "kind": "video", "start_s": 0.0,
                        "width": 1080, "height": 1920}]}
    timeline = run_timeline(paths, clips, tts, fg_min_ratio=0.5, script=SCRIPT, log=lambda _: None)
    assert timeline["audio"] == "voice.wav"
    assert timeline["durationInFrames"] == 90
    assert timeline["captions"]
    assert (paths.root / timeline["audio"]).read_bytes() == sine_wav
    assert paths.voice_mp3.is_file()


@pytest.mark.parametrize("changed", ["script", "provider_name", "voice_id", "model_id", "audio_format"])
def test_saved_native_after_ffmpeg_failure_cannot_be_replaced_by_other_request(tmp_path, sine_wav, monkeypatch, changed):
    import mayzfact.steps.tts as tts_step

    paths = RunPaths(tmp_path)

    def fail_ffmpeg(cmd, step):
        raise PipelineError("tts", "ffmpeg gagal")

    monkeypatch.setattr(tts_step, "_run", fail_ffmpeg)
    with pytest.raises(PipelineError, match="ffmpeg gagal"):
        run_tts(paths, SCRIPT, NativeWavTTS(sine_wav), log=lambda _: None)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    tts = NativeWavTTS(sine_wav)
    script = SCRIPT
    if changed == "script":
        script = {"beats": [{"text": "Different script."}]}
    else:
        setattr(tts, changed, "mp3" if changed == "audio_format" else "different")
    with pytest.raises(PipelineError, match="tersimpan"):
        run_tts(paths, script, tts, log=lambda _: None)
    assert not tts.texts
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
