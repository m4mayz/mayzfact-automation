"""Suara yang di-generate Akmal sendiri di web, di-upload ke run, terus ditimestamp pakai Whisper lokal."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable

from mayzfact.asr import align_heard
from mayzfact.errors import AwaitingInput, PipelineError
from mayzfact.ffmpeg import _run, audio_duration
from mayzfact.providers.voicestudio import alignment_from_words
from mayzfact.store import RunPaths, write_bytes_atomic

UPLOAD_EXTS = (".mp3", ".wav", ".m4a")
UPLOAD_STEM = "voice.upload"
REQUEST_FILE = "tts-request.txt"


def find_uploads(root: Path) -> list[Path]:
    return sorted(root / f"{UPLOAD_STEM}{ext}" for ext in UPLOAD_EXTS if (root / f"{UPLOAD_STEM}{ext}").is_file())


class ManualTTS:
    provider_name = "manual"
    voice_id = "manual"
    model_id = "manual"
    audio_format = "mp3"

    def __init__(self, transcribe: Callable[[Path], list[dict]]) -> None:
        self._transcribe = transcribe
        self._root: Path | None = None
        self._uploads: list[Path] = []
        self._upload: tuple[str, bytes] | None = None
        self.cache_identity = {"provider": "manual"}

    def bind_run(self, paths: RunPaths) -> None:
        # Isi file dibaca sekali: upload ulang pas Whisper jalan nggak boleh nyampur audio baru + timing lama.
        self._root = paths.root
        self._uploads = find_uploads(paths.root)
        self._upload = None
        if len(self._uploads) == 1:
            self._upload = (self._uploads[0].suffix, self._uploads[0].read_bytes())
        # Hash upload ikut identity, jadi audio pending dari upload lama nggak diam-diam dipakai lagi.
        digest = hashlib.sha256(self._upload[1]).hexdigest() if self._upload else None
        self.cache_identity = {"provider": "manual", "upload_sha256": digest}

    def synthesize(self, text: str) -> tuple[bytes, dict]:
        if self._root is None:
            raise PipelineError("tts", "Provider manual belum tahu folder run-nya.")
        root, video_id = self._root, self._root.name
        write_bytes_atomic(root / REQUEST_FILE, text.encode("utf-8"))
        if not self._uploads:
            raise AwaitingInput("tts", f"Nunggu suara. Paste isi runs/{video_id}/{REQUEST_FILE} ke web ElevenLabs, "
                                       f"generate, terus upload lewat `mayzfact brief {video_id}` (atau taruh file di "
                                       f"runs/{video_id}/{UPLOAD_STEM}.mp3). Habis itu jalanin lagi.")
        if self._upload is None:
            raise PipelineError("tts", f"Ada {len(self._uploads)} file {UPLOAD_STEM}.*, sisain satu aja.")
        suffix, data = self._upload
        work, mp3 = root / f".voice.upload.work{suffix}", root / ".voice.upload.work.mp3"
        try:
            write_bytes_atomic(work, data)
            if suffix != ".mp3":
                _run(["ffmpeg", "-y", "-v", "error", "-i", str(work), "-vn", "-c:a", "libmp3lame", "-b:a", "128k",
                      str(mp3)], "tts")
            words = align_heard(text, self._transcribe(mp3), audio_duration(mp3))
            return mp3.read_bytes(), alignment_from_words(text, words)
        finally:
            work.unlink(missing_ok=True)
            mp3.unlink(missing_ok=True)
