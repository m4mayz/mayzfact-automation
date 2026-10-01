"""Client Gemini buat nulis naskah (structured output ke schema Script)."""

from __future__ import annotations

from typing import Any, Callable, Sequence

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from mayzfact.errors import PipelineError
from mayzfact.models import Script
from mayzfact.net import retry_call

SERVER_ERROR_STATUS = {500, 502, 503, 504}
# Kena limit atau key ditolak: pindah ke key berikutnya, jangan nunggu di key yang sama.
KEY_SWITCH_STATUS = {401, 403, 429}


def _gemini_retryable(exc: Exception) -> bool:
    return isinstance(exc, errors.APIError) and exc.code in SERVER_ERROR_STATUS


def _key_rejected(exc: BaseException | None) -> bool:
    if not isinstance(exc, errors.APIError):
        return False
    return exc.code in KEY_SWITCH_STATUS or (exc.code == 400 and "API_KEY_INVALID" in str(exc))


class GeminiScriptWriter:
    def __init__(
        self, api_keys: Sequence[str], model: str, client_factory: Callable[[str], Any] | None = None
    ) -> None:
        self._keys = list(api_keys)
        self._model = model
        self._factory = client_factory or (lambda key: genai.Client(api_key=key))
        self._clients: dict[str, Any] = {}

    def _client(self, key: str) -> Any:
        if key not in self._clients:
            self._clients[key] = self._factory(key)
        return self._clients[key]

    def write(self, system: str, user: str) -> Script:
        reasons: list[str] = []
        for number, key in enumerate(self._keys, start=1):
            client = self._client(key)

            def call():
                return client.models.generate_content(
                    model=self._model,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        response_schema=Script,
                    ),
                )

            try:
                response = retry_call(call, is_retryable=_gemini_retryable, step="script", what="Gemini")
            except PipelineError as exc:
                if _key_rejected(exc.__cause__):
                    reasons.append(f"key #{number}: HTTP {exc.__cause__.code}")
                    continue
                raise
            try:
                return Script.model_validate_json(response.text or "")
            except ValidationError as exc:
                raise PipelineError("script", f"Output Gemini nggak sesuai schema: {exc}") from exc
        raise PipelineError("script", f"Semua {len(self._keys)} key Gemini ditolak ({'; '.join(reasons)}).")
