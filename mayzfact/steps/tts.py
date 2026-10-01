"""Step tts: bikin voice.mp3 + tts.json. Cuma jalan kalau suara belum ada (aturan kunci, spec 3.4)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Protocol

from mayzfact.ffmpeg import audio_duration
from mayzfact.store import RunPaths, write_bytes_atomic, write_json_atomic
from mayzfact.text import script_text, text_hash


class TTSProvider(Protocol):
    voice_id: str
    model_id: str

    def synthesize(self, text: str) -> tuple[bytes, dict]: ...


def run_tts(
    paths: RunPaths,
    script: dict,
    tts: TTSProvider,
    *,
    log: Callable[[str], None] = print,
    measure: Callable[[Path], float] = audio_duration,
) -> dict:
    text = script_text(script["beats"])
    log(f"[tts] Kirim {len(text)} karakter ke ElevenLabs (voice {tts.voice_id}, model {tts.model_id})")
    audio, alignment = tts.synthesize(text)
    incoming = paths.root / "voice.incoming.mp3"
    write_bytes_atomic(incoming, audio)
    data = {
        "text_sha256": text_hash(text),
        "voice_id": tts.voice_id,
        "model_id": tts.model_id,
        "characters": len(text),
        "duration_s": round(measure(incoming), 3),
        "alignment": alignment,
    }
    # tts.json duluan, voice.mp3 terakhir. Keberadaan voice.mp3 = step selesai + naskah dikunci.
    write_json_atomic(paths.tts_json, data)
    os.replace(incoming, paths.voice_mp3)
    return data
