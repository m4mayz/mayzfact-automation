"""Client Gemini buat nulis naskah (structured output ke schema Script)."""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from mayzfact.errors import PipelineError
from mayzfact.models import Script
from mayzfact.net import RETRYABLE_STATUS, retry_call


def _gemini_retryable(exc: Exception) -> bool:
    return isinstance(exc, errors.APIError) and exc.code in RETRYABLE_STATUS


class GeminiScriptWriter:
    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        self._client = client or genai.Client(api_key=api_key)
        self._model = model

    def write(self, system: str, user: str) -> Script:
        def call():
            return self._client.models.generate_content(
                model=self._model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=Script,
                ),
            )

        response = retry_call(call, is_retryable=_gemini_retryable, step="script", what="Gemini")
        try:
            return Script.model_validate_json(response.text or "")
        except ValidationError as exc:
            raise PipelineError("script", f"Output Gemini nggak sesuai schema: {exc}") from exc
