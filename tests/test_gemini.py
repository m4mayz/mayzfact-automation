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
    script = GeminiScriptWriter("key", "gemini-test", client=client).write("system rules", "user prompt")
    assert len(script.beats) == 2
    call = client.models.calls[0]
    assert call["model"] == "gemini-test"
    assert call["contents"] == "user prompt"
    assert call["config"].system_instruction == "system rules"
    assert call["config"].response_mime_type == "application/json"


def test_writer_rejects_output_outside_schema():
    writer = GeminiScriptWriter("key", "gemini-test", client=FakeClient(['{"beats": "nope"}']))
    with pytest.raises(PipelineError, match="schema"):
        writer.write("s", "u")


def test_only_rate_limit_and_server_errors_are_retried():
    class FakeApiError(errors.APIError):
        def __init__(self, code):
            self.code = code

    assert _gemini_retryable(FakeApiError(429))
    assert _gemini_retryable(FakeApiError(503))
    assert not _gemini_retryable(FakeApiError(400))
    assert not _gemini_retryable(ValueError("x"))
