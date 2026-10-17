import httpx
import pytest

from mayzfact.errors import PipelineError
from mayzfact.net import download, request_json, retry_call


def client_with(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_request_json_retries_on_429_then_succeeds():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, json={"ok": True})

    sleeps = []
    result = request_json(client_with(handler), "GET", "https://api.test/x", step="clips", sleep=sleeps.append)
    assert result == {"ok": True}
    assert len(calls) == 3
    assert sleeps == [1.0, 2.0]


def test_request_json_gives_up_after_three_retries():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503, text="down")

    with pytest.raises(PipelineError, match="503"):
        request_json(client_with(handler), "GET", "https://api.test/x", step="clips", sleep=lambda s: None)
    assert len(calls) == 4


def test_request_json_does_not_retry_client_errors():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(401, text="bad key")

    with pytest.raises(PipelineError, match=r"\[clips\].*401"):
        request_json(client_with(handler), "GET", "https://api.test/x", step="clips", sleep=lambda s: None)
    assert len(calls) == 1


def test_download_writes_file_and_skips_when_cached(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=b"video-bytes")

    client = client_with(handler)
    dest = tmp_path / "media" / "clip_1.mp4"
    download(client, "https://cdn.test/a.mp4", dest, step="clips")
    download(client, "https://cdn.test/a.mp4", dest, step="clips")
    assert dest.read_bytes() == b"video-bytes"
    assert len(calls) == 1
    assert sorted(p.name for p in dest.parent.iterdir()) == ["clip_1.mp4"]


def test_download_retries_server_errors(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(502) if len(calls) == 1 else httpx.Response(200, content=b"ok")

    dest = tmp_path / "file.jpg"
    download(client_with(handler), "https://cdn.test/f.jpg", dest, step="clips", sleep=lambda s: None)
    assert dest.read_bytes() == b"ok"


def test_retry_call_wraps_non_retryable_errors():
    def boom():
        raise ValueError("nope")

    with pytest.raises(PipelineError, match=r"\[script\] ElevenLabs gagal: nope"):
        retry_call(boom, is_retryable=lambda e: False, step="script", what="ElevenLabs", sleep=lambda s: None)


def test_non_idempotent_request_is_not_retried_on_read_timeout():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(PipelineError, match="ReadTimeout|slow"):
        request_json(client_with(handler), "POST", "https://api.test/tts", step="tts", idempotent=False, sleep=lambda s: None)
    assert len(calls) == 1


def test_non_idempotent_request_still_retries_connect_errors_and_429():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectError("down", request=request)
        if len(calls) == 2:
            return httpx.Response(429)
        return httpx.Response(200, json={"ok": True})

    assert request_json(client_with(handler), "POST", "https://api.test/tts", step="tts", idempotent=False, sleep=lambda s: None) == {"ok": True}
    assert len(calls) == 3
