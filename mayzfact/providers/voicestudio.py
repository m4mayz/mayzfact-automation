"""VoiceStudio lokal: MP3 + timing kata dipetakan ke kontrak karakter mayzfact."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import httpx

from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import audio_duration
from mayzfact.store import read_json, write_bytes_atomic, write_json_atomic


def alignment_from_words(text: str, words: list[dict]) -> dict:
    """Karakter dalam satu kata berbagi batas kata asli, bukan estimasi timing fonem."""
    spans = [span for span in re.finditer(r"\S+", text) if any(c.isalnum() for c in span.group())]
    error = "Timing VoiceStudio nggak cocok sama naskah; audio aman di cache."
    if not spans or not isinstance(words, list) or len(spans) != len(words):
        raise PipelineError("tts", error)
    starts = [0.0] * len(text)
    ends = [0.0] * len(text)
    previous_end = 0.0
    for span, word in zip(spans, words, strict=True):
        try:
            if type(word["start"]) not in (int, float) or type(word["end"]) not in (int, float):
                raise ValueError("timing harus angka")
            start, end = float(word["start"]), float(word["end"])
            source = "".join(c for c in span.group().casefold() if c.isalnum())
            heard = "".join(c for c in word["word"].casefold() if c.isalnum())
            # ASR sering menulis angka countdown sebagai digit; nilainya harus tetap sama persis.
            numbers = {name: str(i) for i, name in enumerate(
                ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"))}
            source, heard = numbers.get(source, source), numbers.get(heard, heard)
            valid = source and source == heard and math.isfinite(start) and math.isfinite(end)
            valid = valid and previous_end <= start < end
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise PipelineError("tts", error) from exc
        if not valid:
            raise PipelineError("tts", error + f" Kata: {span.group()!r}.")
        previous_end = end
        for index in range(span.start(), span.end()):
            starts[index], ends[index] = start, end
    for left, right in zip(spans, spans[1:]):
        for index in range(left.end(), right.start()):
            starts[index], ends[index] = ends[left.end() - 1], starts[right.start()]
    for index in range(spans[-1].end(), len(text)):
        starts[index] = ends[index] = previous_end
    return {"characters": list(text), "character_start_times_seconds": starts, "character_end_times_seconds": ends}


class VoiceStudioTTS:
    provider_name = "voicestudio"

    def __init__(self, base_url: str, voice: str, engine: str, client: httpx.Client, *, cache_dir: Path,
                 timeout: float = 900.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.voice_id = voice
        self.model_id = engine
        self._client = client
        self._cache_dir = cache_dir
        self._timeout = timeout
        self.cache_identity = {"provider": self.provider_name, "url": self.base_url,
                               "voice": voice, "model": engine, "language": "en", "speed": 1.0, "seed": 0}

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            response = self._client.request(method, self.base_url + path, timeout=self._timeout,
                                            follow_redirects=False, **kwargs)
        except httpx.TransportError as exc:
            raise PipelineError("tts", f"VoiceStudio nggak bisa dihubungi: {exc}. Jalankan backend lokal dulu.") from exc
        if not 200 <= response.status_code < 300:
            raise PipelineError("tts", f"VoiceStudio {path}: HTTP {response.status_code}: {response.text[:500]}")
        return response

    def synthesize(self, text: str) -> tuple[bytes, dict]:
        try:
            return self._synthesize(text)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise PipelineError("tts", f"Respons/cache VoiceStudio nggak valid: {exc}. Audio yang tersimpan tetap aman.") from exc

    def _synthesize(self, text: str) -> tuple[bytes, dict]:
        profiles = self._request("GET", "/profiles").json()
        if (not isinstance(profiles, list)
                or any(not isinstance(p, dict) or not p.get("id") or not p.get("name") for p in profiles)):
            raise PipelineError("tts", "Daftar profil VoiceStudio nggak valid.")
        matches = [p for p in profiles if p["id"] == self.voice_id]
        if not matches:
            matches = [p for p in profiles if p["name"] == self.voice_id]
        if len(matches) != 1:
            raise PipelineError("tts", f"Profil VoiceStudio {self.voice_id!r} nggak ketemu atau namanya duplikat.")
        self.voice_id = matches[0]["id"]
        body = {"model": self.model_id, "input": text, "voice": self.voice_id, "language": "en",
                "response_format": "mp3", "speed": 1.0, "seed": 0}
        identity = json.dumps({"url": self.base_url, "request": body, "profile": matches[0]}, sort_keys=True)
        key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        directory = self._cache_dir / key
        path = directory / "voice.mp3"
        transcript = directory / "transcript.json"
        if not path.exists():
            response = self._request("POST", "/v1/audio/speech", json=body)
            write_bytes_atomic(path, response.content)  # simpan dulu sebelum alignment bisa gagal
        audio = path.read_bytes()
        duration = audio_duration(path)
        if transcript.exists():
            result = read_json(transcript)
        else:
            result = self._request("POST", "/v1/audio/transcriptions",
                                   files={"file": ("voice.mp3", audio, "audio/mpeg")},
                                   data={"model": "whisper-1", "language": "en", "prompt": text,
                                         "response_format": "verbose_json", "timestamp_granularities[]": "word"}).json()
            write_json_atomic(directory / "transcript.last.json", result)
        if not isinstance(result, dict):
            raise PipelineError("tts", "Respons/cache transkripsi VoiceStudio harus object JSON dengan words; "
                                "periksa respons ASR/cache transkrip. Audio yang tersimpan tetap aman.")
        alignment = alignment_from_words(text, result.get("words", []))
        if max(alignment["character_end_times_seconds"]) > duration + 0.1:
            raise PipelineError("tts", "Timing VoiceStudio lewat akhir audio; audio aman di cache.")
        write_json_atomic(transcript, result)
        return audio, alignment
