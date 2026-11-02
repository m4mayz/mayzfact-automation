"""D-047: delivery provider-only, alignment exact dan audio berbayar tetap aman."""

import base64
import json

import httpx
import pytest

from mayzfact.config import Settings
from mayzfact.errors import PipelineError
from mayzfact.pipeline import real_deps
from mayzfact.providers.elevenlabs import ElevenLabsTTS
from mayzfact.steps.timeline import run_timeline
from mayzfact.steps.tts import run_tts
from mayzfact.store import RunPaths, read_json, write_json_atomic
from mayzfact.text import text_hash
from mayzfact.timing import beat_timings, word_timings
from tests.factories import fake_alignment


def mock_provider(alignment, *, delivery_tag="calm", audio=b"paid-audio"):
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "audio_base64": base64.b64encode(audio).decode(), "alignment": alignment,
        })

    client = httpx.Client(transport=httpx.MockTransport(respond))
    provider = ElevenLabsTTS(["test-only"], "TX3LPaxmHKxFdv7VOQHJ", "eleven_v3", client,
                             stability=0.5, delivery_tag=delivery_tag)
    return provider, requests


def test_calm_is_sent_only_in_request_and_raw_response_is_preserved():
    text = "These three events look apocalyptic."
    raw = fake_alignment("[calm] " + text, 3.0)
    provider, requests = mock_provider(raw)
    audio, alignment = provider.synthesize(text)
    assert requests == [{"text": "[calm] " + text, "model_id": "eleven_v3", "voice_settings": {"stability": 0.5}}]
    assert audio == b"paid-audio"
    assert alignment == raw  # run_tts wajib menyimpan raw sebelum validasi
    assert text == "These three events look apocalyptic."


def test_tagged_alignment_flows_to_original_text_timing_and_captions(tmp_path):
    texts = ["These events look apocalyptic,", "and number one is deadly."]
    text = " ".join(texts)
    script = {"beats": [{"text": part, "media": "video", "queries": ["events"]} for part in texts]}
    raw = fake_alignment("[calm] " + text, 3.0)
    provider, _ = mock_provider(raw)
    paths = RunPaths(tmp_path)
    data = run_tts(paths, script, provider, measure=lambda _: 3.0, log=lambda _: None)
    expected = {key: values[7:] for key, values in raw.items()}
    assert data["alignment"] == expected
    assert {len(values) for values in data["alignment"].values()} == {len(text)}
    assert data["raw_alignment"] == raw
    assert data["delivery_tag"] == "calm"
    assert data["text_sha256"] == text_hash(text)
    assert data["characters"] == len(text)
    assert data == read_json(paths.tts_json)
    assert paths.voice_mp3.read_bytes() == b"paid-audio"
    assert word_timings(data["alignment"])[0]["start_s"] == raw["character_start_times_seconds"][7]
    assert beat_timings(texts, data["alignment"], 3.0)[1]["start_s"] == round(
        raw["character_start_times_seconds"][7 + len(texts[0]) + 1], 3)
    clips = {"shots": [{"file": "clips/shot_01.mp4", "kind": "video", "start_s": 0.0,
                        "width": 1080, "height": 1920}]}
    timeline = run_timeline(paths, clips, data, fg_min_ratio=0.5, script=script, log=lambda _: None)
    assert timeline["captions"]
    assert "calm" not in json.dumps(timeline)
    assert script["beats"][0]["text"] == texts[0]


@pytest.mark.parametrize("delivery_tag,prefix", [("calm", "[calm]"), ("calm", ""), ("", "")])
def test_alignment_accepts_provider_omitted_separator_or_tag_without_retiming(delivery_tag, prefix):
    text = "These three events."
    raw = fake_alignment(prefix + text, 2.0)
    provider, _ = mock_provider(raw, delivery_tag=delivery_tag)
    result = provider.normalize_alignment(text, raw)
    assert result == {key: values[len(prefix):] for key, values in raw.items()}
    assert raw["characters"] == list(prefix + text)


def test_no_tag_keeps_legacy_raw_alignment_even_when_provider_text_differs():
    raw = fake_alignment("Provider changed this.", 2.0)
    provider, requests = mock_provider(raw, delivery_tag="")
    audio, alignment = provider.synthesize("Original text.")
    assert requests[0]["text"] == "Original text."
    assert audio == b"paid-audio"
    assert provider.normalize_alignment("Original text.", alignment) == raw


@pytest.mark.parametrize("problem", ["word", "case", "tag", "starts", "ends", "missing", "null"])
def test_invalid_tagged_alignment_fails_after_paid_audio_is_saved_without_retry(tmp_path, problem):
    text = "These three events."
    raw = fake_alignment("[calm] " + text, 2.0)
    if problem == "word":
        raw = fake_alignment("[calm] These four events.", 2.0)
    elif problem == "case":
        raw = fake_alignment("[calm] these three events.", 2.0)
    elif problem == "tag":
        raw = fake_alignment("[excited] " + text, 2.0)
    elif problem == "starts":
        raw["character_start_times_seconds"].pop()
    elif problem == "ends":
        raw["character_end_times_seconds"].append(2.1)
    elif problem == "missing":
        del raw["character_end_times_seconds"]
    elif problem == "null":
        raw = None
    provider, requests = mock_provider(raw)
    paths = RunPaths(tmp_path)
    script = {"beats": [{"text": text}]}
    for _ in range(2):
        with pytest.raises(PipelineError, match="Alignment.*voice.incoming.mp3 aman"):
            run_tts(paths, script, provider, measure=lambda _: 2.0, log=lambda _: None)
        assert (tmp_path / "voice.incoming.mp3").read_bytes() == b"paid-audio"
        assert read_json(tmp_path / "tts.incoming.json")["alignment"] == raw
        assert not paths.voice_mp3.exists()
        assert not paths.tts_json.exists()
    assert len(requests) == 1


@pytest.mark.parametrize("tag", ["calm", ""])
def test_cache_identity_records_tag_only_when_used(tag):
    provider, _ = mock_provider(fake_alignment("Hi", 1.0), delivery_tag=tag)
    expected = {"provider": "elevenlabs", "voice_id": "TX3LPaxmHKxFdv7VOQHJ",
                "model_id": "eleven_v3", "stability": 0.5}
    if tag:
        expected["delivery_tag"] = tag
    assert provider.cache_identity == expected


@pytest.mark.parametrize("old_tag,new_tag", [(None, "calm"), ("", "calm"), ("excited", "calm"), ("calm", "")])
def test_pending_delivery_identity_mismatch_never_reuses_or_overwrites_paid_audio(tmp_path, old_tag, new_tag):
    text = "These three events."
    provider, requests = mock_provider(fake_alignment(text, 2.0), delivery_tag=new_tag)
    (tmp_path / "voice.incoming.mp3").write_bytes(b"old-paid-audio")
    pending = {"text_sha256": text_hash(text), "alignment": fake_alignment(text, 2.0)}
    if old_tag is not None:
        old, _ = mock_provider(pending["alignment"], delivery_tag=old_tag)
        pending["identity"] = old.cache_identity
    write_json_atomic(tmp_path / "tts.incoming.json", pending)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    with pytest.raises(PipelineError, match="tersimpan"):
        run_tts(RunPaths(tmp_path), {"beats": [{"text": text}]}, provider, measure=lambda _: 2.0, log=lambda _: None)
    assert not requests
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before


def test_calm_measure_failure_resumes_raw_pending_without_paying_or_slicing_twice(tmp_path):
    text = "These three events."
    raw = fake_alignment("[calm] " + text, 2.0)
    provider, requests = mock_provider(raw)
    paths = RunPaths(tmp_path)

    def fail_measure(path):
        assert path.read_bytes() == b"paid-audio"
        assert read_json(tmp_path / "tts.incoming.json")["alignment"] == raw
        raise PipelineError("tts", "ffprobe gagal")

    script = {"beats": [{"text": text}]}
    with pytest.raises(PipelineError, match="ffprobe gagal"):
        run_tts(paths, script, provider, measure=fail_measure, log=lambda _: None)
    assert read_json(tmp_path / "tts.incoming.json")["identity"]["delivery_tag"] == "calm"
    data = run_tts(paths, script, provider, measure=lambda _: 2.0, log=lambda _: None)
    assert len(requests) == 1
    assert data["alignment"] == {key: values[7:] for key, values in raw.items()}
    assert data["raw_alignment"] == raw


@pytest.mark.parametrize("tag", ["calm", "", "soft spoken"])
def test_production_factory_forwards_approved_or_local_delivery_to_request(monkeypatch, tag):
    import mayzfact.pipeline as pipeline

    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={
            "audio_base64": base64.b64encode(b"mock-audio").decode(), "alignment": fake_alignment("Hi", 1.0),
        })

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(pipeline, "make_client", lambda: client)
        deps = real_deps(Settings(elevenlabs_api_keys=("test-only",), elevenlabs_delivery_tag=tag))
        try:
            provider = deps.tts()
            assert provider.delivery_tag == tag
            assert provider.stability == 0.5
            provider.synthesize("Hi")
        finally:
            deps.close()
    assert requests == [{"text": f"[{tag}] Hi" if tag else "Hi", "model_id": "eleven_v3",
                         "voice_settings": {"stability": 0.5}}]
