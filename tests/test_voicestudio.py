import pytest

from mayzfact.errors import PipelineError
from mayzfact.timing import beat_timings, word_timings


def test_word_alignment_keeps_exact_script_and_real_word_boundaries():
    from mayzfact.providers.voicestudio import alignment_from_words

    text = "Look, it's OLD! Number five, the camel."
    tokens = ["look", "it's", "old", "number", "five", "the", "camel"]
    words = [{"word": token, "start": i * 0.5 + 0.1, "end": i * 0.5 + 0.4} for i, token in enumerate(tokens)]
    alignment = alignment_from_words(text, words)
    assert "".join(alignment["characters"]) == text
    timed = word_timings(alignment)
    assert [w["text"] for w in timed] == text.split()
    assert [w["start_s"] for w in timed] == [w["start"] for w in words]
    assert [w["end_s"] for w in timed] == [w["end"] for w in words]
    beats = beat_timings(["Look, it's OLD!", "Number five, the camel."], alignment, 4.0)
    assert beats[1]["start_s"] == 1.6


@pytest.mark.parametrize("words", [
    [{"word": "wrong", "start": 0.1, "end": 0.4}],
    [{"word": "Hello", "start": -1, "end": 0.4}],
    [{"word": "Hello", "start": 0.5, "end": 0.4}],
    [{"word": "Hello", "start": float("nan"), "end": 0.4}],
    [{"word": "Hello", "start": 0.1}], [],
])
def test_bad_transcript_or_timing_is_not_fabricated(words):
    from mayzfact.providers.voicestudio import alignment_from_words

    with pytest.raises(PipelineError, match="VoiceStudio"):
        alignment_from_words("Hello.", words)


def test_countdown_numeral_from_real_asr_keeps_spelled_script():
    from mayzfact.providers.voicestudio import alignment_from_words

    # Cuplikan respons nyata Gen: WhisperX menulis "Number 5.".
    alignment = alignment_from_words("Number five,", [
        {"word": "Number", "start": 2.926, "end": 3.148},
        {"word": "5.", "start": 3.409, "end": 3.570},
    ])
    assert "".join(alignment["characters"]) == "Number five,"
    assert word_timings(alignment)[1]["start_s"] == 3.409
    assert word_timings(alignment)[1]["end_s"] == 3.570
    with pytest.raises(PipelineError):
        alignment_from_words("five", [{"word": "4", "start": 0.1, "end": 0.2}])


def test_standalone_punctuation_keeps_exact_script_without_extra_asr_word():
    from mayzfact.providers.voicestudio import alignment_from_words

    text = "Hello — world!"
    alignment = alignment_from_words(text, [
        {"word": "Hello", "start": 0.1, "end": 0.4},
        {"word": "world", "start": 0.6, "end": 0.9},
    ])
    assert "".join(alignment["characters"]) == text
    words = word_timings(alignment)
    assert words[0]["start_s"] == 0.1 and words[2]["end_s"] == 0.9
    assert words[1]["text"] == "—"
    assert (words[1]["start_s"], words[1]["end_s"]) == (0.4, 0.6)


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("payload", [None, [], "bad"])
def test_non_object_transcription_json_is_actionable(tmp_path, sine_mp3, payload, cached):
    import json

    import httpx

    from mayzfact.providers.voicestudio import VoiceStudioTTS

    def handle(request):
        if request.url.path == "/profiles":
            return httpx.Response(200, json=[{"id": "gen-id", "name": "Gen"}])
        if request.url.path == "/v1/audio/speech":
            return httpx.Response(200, content=sine_mp3.read_bytes(), headers={"content-type": "audio/mpeg"})
        if cached:
            return httpx.Response(200, json={"words": [{"word": "Hello", "start": 0.1, "end": 0.4}]})
        return httpx.Response(200, content=json.dumps(payload), headers={"content-type": "application/json"})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        p = VoiceStudioTTS("http://127.0.0.1:3900", "Gen", "cosyvoice", client, cache_dir=tmp_path)
        if cached:
            p.synthesize("Hello")
            transcript = next(tmp_path.glob("*/transcript.json"))
            transcript.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(PipelineError, match="VoiceStudio"):
            p.synthesize("Hello")


def test_out_of_order_words_are_rejected():
    from mayzfact.providers.voicestudio import alignment_from_words

    with pytest.raises(PipelineError, match="VoiceStudio"):
        alignment_from_words("Hi there", [
            {"word": "Hi", "start": 0.5, "end": 0.8},
            {"word": "there", "start": 0.3, "end": 0.4},
        ])


def test_voicestudio_resolves_gen_generates_mp3_and_aligns(tmp_path, sine_mp3):
    import json

    import httpx

    from mayzfact.providers.voicestudio import VoiceStudioTTS

    calls = []

    def handle(request):
        calls.append(request.url.path)
        if request.url.path == "/profiles":
            return httpx.Response(200, json=[{"id": "gen-id", "name": "Gen"}])
        if request.url.path == "/v1/audio/speech":
            body = json.loads(request.content)
            assert body["voice"] == "gen-id"
            assert body["model"] == "cosyvoice"
            assert body["input"] == "Hello world."
            assert body["language"] == "en"
            assert body["response_format"] == "mp3"
            return httpx.Response(200, content=sine_mp3.read_bytes(), headers={"content-type": "audio/mpeg"})
        assert request.url.path == "/v1/audio/transcriptions"
        assert b"verbose_json" in request.content and b"timestamp_granularities[]" in request.content
        return httpx.Response(200, json={"words": [
            {"word": "Hello", "start": 0.1, "end": 0.5},
            {"word": "world", "start": 0.6, "end": 0.9},
        ]})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        provider = VoiceStudioTTS("http://127.0.0.1:3900", "Gen", "cosyvoice", client, cache_dir=tmp_path)
        audio, alignment = provider.synthesize("Hello world.")
        assert provider.voice_id == "gen-id"
        assert provider.model_id == "cosyvoice"
        assert audio == sine_mp3.read_bytes()
        assert "".join(alignment["characters"]) == "Hello world."
        assert calls == ["/profiles", "/v1/audio/speech", "/v1/audio/transcriptions"]


def test_alignment_retry_reuses_audio_and_success_reuses_alignment(tmp_path, sine_mp3):
    import httpx

    from mayzfact.providers.voicestudio import VoiceStudioTTS

    calls = []

    def handle(request):
        calls.append(request.url.path)
        if request.url.path == "/profiles":
            return httpx.Response(200, json=[{"id": "gen-id", "name": "Gen", "ref_text": "sample"}])
        if request.url.path == "/v1/audio/speech":
            return httpx.Response(200, content=sine_mp3.read_bytes(), headers={"content-type": "audio/mpeg"})
        if calls.count("/v1/audio/transcriptions") == 1:
            return httpx.Response(503, text="ASR belum siap")
        return httpx.Response(200, json={"words": [{"word": "Hello", "start": 0.1, "end": 0.5}]})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        def provider():
            return VoiceStudioTTS("http://127.0.0.1:3900", "Gen", "cosyvoice", client, cache_dir=tmp_path)

        with pytest.raises(PipelineError, match="503"):
            provider().synthesize("Hello.")
        a = provider().synthesize("Hello.")
        b = provider().synthesize("Hello.")
        assert a == b
    assert calls.count("/v1/audio/speech") == 1
    assert calls.count("/v1/audio/transcriptions") == 2


@pytest.mark.parametrize("payload", [None, {}, [{"word": "Hi", "start": True, "end": 2.0}]])
def test_malformed_words_have_actionable_error(payload):
    from mayzfact.providers.voicestudio import alignment_from_words

    with pytest.raises(PipelineError, match="VoiceStudio"):
        alignment_from_words("Hi", payload)


@pytest.mark.parametrize("response", ["not-json", "{}", "[{}]"])
def test_malformed_profiles_are_reported_as_pipeline_error(tmp_path, response):
    import httpx

    from mayzfact.providers.voicestudio import VoiceStudioTTS

    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=response))) as client:
        p = VoiceStudioTTS("http://127.0.0.1:3900", "Gen", "cosyvoice", client, cache_dir=tmp_path)
        with pytest.raises(PipelineError, match="VoiceStudio"):
            p.synthesize("Hello")


def test_connection_error_is_local_only_and_not_retried(tmp_path):
    import httpx

    from mayzfact.providers.voicestudio import VoiceStudioTTS

    calls = []

    def offline(request):
        calls.append(str(request.url))
        raise httpx.ConnectError("refused")

    with httpx.Client(transport=httpx.MockTransport(offline)) as client:
        p = VoiceStudioTTS("http://127.0.0.1:3900", "Gen", "cosyvoice", client, cache_dir=tmp_path)
        with pytest.raises(PipelineError, match="backend lokal"):
            p.synthesize("Hello")
    assert calls == ["http://127.0.0.1:3900/profiles"]


@pytest.mark.parametrize("profiles", [[], [{"id": "a", "name": "Gen"}, {"id": "b", "name": "Gen"}]])
def test_missing_or_ambiguous_gen_never_uses_default(tmp_path, profiles):
    import httpx

    from mayzfact.providers.voicestudio import VoiceStudioTTS

    def handle(request):
        assert request.url.path == "/profiles"
        return httpx.Response(200, json=profiles)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        provider = VoiceStudioTTS("http://127.0.0.1:3900", "Gen", "cosyvoice", client, cache_dir=tmp_path)
        with pytest.raises(PipelineError, match="Profil VoiceStudio"):
            provider.synthesize("Hello.")
