from types import SimpleNamespace

import pytest
from google.genai import errors

from mayzfact.errors import PipelineError
from mayzfact.providers.gemini import GeminiScriptWriter, _gemini_retryable
from tests.factories import make_script

VALID_JSON = make_script(n_beats=2).model_dump_json()


class FakeModels:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return SimpleNamespace(text=self.outputs.pop(0))


class FakeClient:
    def __init__(self, outputs):
        self.models = FakeModels(outputs)


def test_writer_parses_structured_output_and_sends_config():
    client = FakeClient([VALID_JSON])
    script = GeminiScriptWriter(["key"], "gemini-test", client_factory=lambda key: client).write("system rules", "user prompt")
    assert len(script.beats) == 2
    call = client.models.calls[0]
    assert call["model"] == "gemini-test"
    assert call["contents"] == "user prompt"
    assert call["config"].system_instruction == "system rules"
    assert call["config"].response_mime_type == "application/json"


def test_writer_rejects_output_outside_schema():
    writer = GeminiScriptWriter(["key"], "gemini-test", client_factory=lambda key: FakeClient(['{"beats": "nope"}']))
    with pytest.raises(PipelineError, match="schema"):
        writer.write("s", "u")


def test_only_rate_limit_and_server_errors_are_retried():
    class FakeApiError(errors.APIError):
        def __init__(self, code):
            self.code = code

    assert not _gemini_retryable(FakeApiError(429))
    assert _gemini_retryable(FakeApiError(503))
    assert not _gemini_retryable(FakeApiError(400))
    assert not _gemini_retryable(ValueError("x"))


class FakeApiError(errors.APIError):
    def __init__(self, code, message=""):
        self.code = code
        self.text = message

    def __str__(self):
        return f"{self.code} {self.text}"


class FailingModels:
    def __init__(self, exc):
        self.exc = exc
        self.calls = 0

    def generate_content(self, *, model, contents, config):
        self.calls += 1
        raise self.exc


def _clients(mapping):
    used = []

    def factory(key):
        used.append(key)
        return mapping[key]

    return factory, used


def test_writer_switches_key_on_rate_limit_or_invalid_key():
    for exc in (FakeApiError(429, "RESOURCE_EXHAUSTED"), FakeApiError(400, "API_KEY_INVALID"), FakeApiError(403, "PERMISSION_DENIED")):
        bad = SimpleNamespace(models=FailingModels(exc))
        factory, used = _clients({"k1": bad, "k2": FakeClient([VALID_JSON])})
        script = GeminiScriptWriter(["k1", "k2"], "gemini-test", client_factory=factory).write("s", "u")
        assert len(script.beats) == 2
        assert used == ["k1", "k2"]
        assert bad.models.calls == 1


def test_writer_does_not_switch_key_on_other_bad_request():
    bad = SimpleNamespace(models=FailingModels(FakeApiError(400, "INVALID_ARGUMENT schema")))
    factory, used = _clients({"k1": bad, "k2": FakeClient([VALID_JSON])})
    with pytest.raises(PipelineError):
        GeminiScriptWriter(["k1", "k2"], "gemini-test", client_factory=factory).write("s", "u")
    assert used == ["k1"]


def test_writer_reports_when_all_keys_fail():
    factory, _ = _clients({
        "k1": SimpleNamespace(models=FailingModels(FakeApiError(429, "RESOURCE_EXHAUSTED"))),
        "k2": SimpleNamespace(models=FailingModels(FakeApiError(429, "RESOURCE_EXHAUSTED"))),
    })
    with pytest.raises(PipelineError, match="Semua 2 key Gemini") as exc:
        GeminiScriptWriter(["k1", "k2"], "gemini-test", client_factory=factory).write("s", "u")
    assert "k1" not in str(exc.value)
