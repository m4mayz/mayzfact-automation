import threading

import httpx
import pytest

from mayzfact.asr import align_heard
from mayzfact.brief.server import make_server
from mayzfact.config import Settings, load_settings, settings_for_mode
from mayzfact.errors import AwaitingInput, PipelineError
from mayzfact.ffmpeg import audio_duration
from mayzfact.providers.manual import ManualTTS
from mayzfact.steps.tts import run_tts
from mayzfact.store import RunPaths, read_json

SCRIPT = {"beats": [{"text": "Kucing nggak suka air.", "media": "video", "queries": ["cat"]},
                    {"text": "Tekan like ya.", "media": "video", "queries": ["like"]}]}
TEXT = "Kucing nggak suka air. Tekan like ya."


@pytest.fixture
def sine_wav(tmp_path_factory):
    import subprocess

    path = tmp_path_factory.mktemp("wav") / "sine.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=3", str(path)],
                   check=True)
    return path


def heard(*words):
    return [{"word": w, "start": round(i * 0.4, 2), "end": round(i * 0.4 + 0.3, 2)} for i, w in enumerate(words)]


def test_align_heard_uses_heard_times_for_exact_and_respelled_words():
    words = align_heard(TEXT, heard("Kucing", "gak", "suka", "air.", "Tekan", "laik", "ya."), duration=3.0)
    assert [w["word"] for w in words] == ["Kucing", "nggak", "suka", "air.", "Tekan", "like", "ya."]
    assert [w["start"] for w in words] == [0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4]
    assert words[5]["end"] == 2.3


def test_align_heard_fills_unheard_word_between_neighbours():
    words = align_heard(TEXT, heard("Kucing", "nggak", "suka", "Tekan", "like", "ya"), duration=3.0)
    assert [w["word"] for w in words][3] == "air."
    assert words[2]["end"] <= words[3]["start"] < words[3]["end"] <= words[4]["start"]


def test_align_heard_splits_merged_words_by_length():
    words = align_heard("Ini sangat besar.", [{"word": "Ini", "start": 0.0, "end": 0.2},
                                               {"word": "sangatbesar", "start": 0.3, "end": 1.4}], duration=2.0)
    assert words[1]["start"] == 0.3 and words[2]["end"] == 1.4
    assert words[1]["end"] == words[2]["start"]


def test_align_heard_rejects_audio_of_another_script():
    with pytest.raises(PipelineError, match="nggak cocok"):
        align_heard(TEXT, heard("Halo", "semua", "hari", "ini", "kita", "bahas", "gunung"), duration=3.0)


def test_manual_without_upload_writes_request_and_waits(tmp_path):
    paths = RunPaths(tmp_path)
    tts = ManualTTS(transcribe=lambda path: pytest.fail("ASR jangan jalan tanpa upload"))
    with pytest.raises(AwaitingInput, match="tts-request.txt"):
        run_tts(paths, SCRIPT, tts, log=lambda _: None)
    assert (tmp_path / "tts-request.txt").read_text(encoding="utf-8") == TEXT
    assert not paths.voice_mp3.exists() and not paths.tts_json.exists()


def test_manual_upload_becomes_voice_with_aligned_timing(tmp_path, sine_mp3):
    paths = RunPaths(tmp_path)
    (tmp_path / "voice.upload.mp3").write_bytes(sine_mp3.read_bytes())
    seen = []
    tts = ManualTTS(transcribe=lambda path: seen.append(path) or heard(
        "Kucing", "gak", "suka", "air", "Tekan", "like", "ya"))
    data = run_tts(paths, SCRIPT, tts, log=lambda _: None)
    assert data["provider"] == "manual" and data["voice_id"] == "manual"
    assert paths.voice_mp3.read_bytes() == sine_mp3.read_bytes()
    starts = data["alignment"]["character_start_times_seconds"]
    assert starts[TEXT.index("like")] == 2.0
    assert (tmp_path / "voice.upload.mp3").exists()  # file Akmal nggak dihapus
    assert read_json(paths.tts_json)["text_sha256"]


def test_manual_wav_upload_is_converted_to_mp3(tmp_path, sine_wav):
    paths = RunPaths(tmp_path)
    (tmp_path / "voice.upload.wav").write_bytes(sine_wav.read_bytes())
    tts = ManualTTS(transcribe=lambda path: heard("Kucing", "nggak", "suka", "air", "Tekan", "like", "ya"))
    run_tts(paths, SCRIPT, tts, log=lambda _: None)
    assert paths.voice_mp3.read_bytes()[:3] in (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
    assert abs(audio_duration(paths.voice_mp3) - audio_duration(sine_wav)) < 0.2


def test_manual_wrong_upload_fails_without_writing_voice(tmp_path, sine_mp3):
    paths = RunPaths(tmp_path)
    (tmp_path / "voice.upload.mp3").write_bytes(sine_mp3.read_bytes())
    tts = ManualTTS(transcribe=lambda path: heard("Halo", "semua", "ini", "video", "lain", "banget", "ya"))
    with pytest.raises(PipelineError, match="nggak cocok"):
        run_tts(paths, SCRIPT, tts, log=lambda _: None)
    assert not paths.voice_mp3.exists()


def test_settings_accept_manual_provider(tmp_path):
    (tmp_path / "settings.local.json").write_text(
        '{"faktacuil_tts_provider": "manual", "manual_asr_model": "openai/whisper-base"}', encoding="utf-8")
    settings = load_settings(tmp_path / ".env")
    faktacuil = settings_for_mode(settings, "faktacuil")
    assert faktacuil.tts_provider == "manual"
    assert faktacuil.manual_language == "id" and faktacuil.manual_asr_model == "openai/whisper-base"
    assert settings_for_mode(Settings(), "top3").manual_language == "en"


def test_real_deps_builds_manual_without_loading_whisper():
    from mayzfact.pipeline import real_deps

    deps = real_deps(Settings(tts_provider="manual"))
    try:
        assert isinstance(deps.tts(), ManualTTS)
    finally:
        deps.close()


@pytest.fixture
def voice_server(tmp_path):
    paths = RunPaths(tmp_path / "abc")
    paths.root.mkdir(parents=True)
    (paths.root / "tts-request.txt").write_text("Teks <b>naskah</b> FaktaCuil.", encoding="utf-8")
    srv = make_server(paths, 0, max_upload=1000)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield paths, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def test_voice_page_shows_request_text_without_plan(voice_server):
    paths, base = voice_server
    html = httpx.get(base + "/").text
    assert "Teks &lt;b&gt;naskah&lt;/b&gt; FaktaCuil." in html and "/api/voice" in html


def test_voice_upload_replaces_previous_upload(voice_server):
    paths, base = voice_server
    assert httpx.post(base + "/api/voice", content=b"wav", headers={"X-Filename": "a.WAV"}).status_code == 200
    ok = httpx.post(base + "/api/voice", content=b"mp3", headers={"X-Filename": "eleven.mp3"})
    assert ok.status_code == 200 and ok.json()["file"] == "voice.upload.mp3"
    assert sorted(p.name for p in paths.root.glob("voice.upload*")) == ["voice.upload.mp3"]
    assert "voice.upload.mp3" in httpx.get(base + "/").text


def test_voice_upload_rejects_bad_type_and_locked_voice(voice_server):
    paths, base = voice_server
    assert httpx.post(base + "/api/voice", content=b"x", headers={"X-Filename": "a.exe"}).status_code == 400
    paths.voice_mp3.write_bytes(b"locked")
    assert httpx.post(base + "/api/voice", content=b"x", headers={"X-Filename": "a.mp3"}).status_code == 409


def test_reupload_during_whisper_does_not_mix_audio_and_timing(tmp_path, sine_mp3, sine_wav):
    paths = RunPaths(tmp_path)
    upload = tmp_path / "voice.upload.mp3"
    upload.write_bytes(sine_mp3.read_bytes())

    def transcribe(path):
        upload.write_bytes(b"upload baru")  # Akmal upload ulang pas Whisper jalan
        return heard("Kucing", "nggak", "suka", "air", "Tekan", "like", "ya")

    run_tts(paths, SCRIPT, ManualTTS(transcribe=transcribe), log=lambda _: None)
    assert paths.voice_mp3.read_bytes() == sine_mp3.read_bytes()
    assert not list(tmp_path.glob(".voice.upload.work*"))


def test_new_upload_does_not_silently_reuse_pending_audio(tmp_path, sine_mp3, sine_wav):
    paths = RunPaths(tmp_path)
    (tmp_path / "voice.upload.mp3").write_bytes(sine_mp3.read_bytes())
    words = lambda path: heard("Kucing", "nggak", "suka", "air", "Tekan", "like", "ya")

    def broken_measure(path):
        raise PipelineError("tts", "ffprobe gagal")

    with pytest.raises(PipelineError, match="ffprobe"):
        run_tts(paths, SCRIPT, ManualTTS(transcribe=words), log=lambda _: None, measure=broken_measure)
    (tmp_path / "voice.upload.mp3").unlink()
    (tmp_path / "voice.upload.wav").write_bytes(sine_wav.read_bytes())
    with pytest.raises(PipelineError, match="Jangan ditimpa"):
        run_tts(paths, SCRIPT, ManualTTS(transcribe=words), log=lambda _: None)


def test_voice_upload_rejected_while_previous_upload_is_pending(voice_server):
    paths, base = voice_server
    (paths.root / "voice.incoming.mp3").write_bytes(b"pending")
    assert httpx.post(base + "/api/voice", content=b"x", headers={"X-Filename": "a.mp3"}).status_code == 409
