"""Step tts: bikin voice.mp3 + tts.json. Cuma jalan kalau suara belum ada (aturan kunci, spec 3.4)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Protocol

from mayzfact.ffmpeg import audio_duration
from mayzfact.store import RunPaths, read_json, write_bytes_atomic, write_json_atomic
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
    stability = getattr(tts, "stability", None)  # provider lama/fake di test boleh nggak punya
    incoming = paths.root / "voice.incoming.mp3"
    incoming_meta = paths.root / "tts.incoming.json"
    # Audio yang udah dibayar disimpan dulu. Kalau langkah setelahnya gagal (mis. ffprobe), run berikutnya
    # pakai ulang file ini selama naskahnya sama, jadi ElevenLabs nggak ditagih dua kali.
    pending = read_json(incoming_meta) if incoming.exists() and incoming_meta.exists() else None
    if pending is not None and pending["text_sha256"] == text_hash(text):
        log("[tts] Pakai audio ElevenLabs yang udah dibayar sebelumnya (voice.incoming.mp3)")
        alignment = pending["alignment"]
    else:
        log(f"[tts] Kirim {len(text)} karakter ke ElevenLabs (voice {tts.voice_id}, model {tts.model_id}, stability {stability})")
        audio, alignment = tts.synthesize(text)
        write_bytes_atomic(incoming, audio)
        write_json_atomic(incoming_meta, {"text_sha256": text_hash(text), "alignment": alignment})
    data = {
        "text_sha256": text_hash(text),
        "voice_id": tts.voice_id,
        "model_id": tts.model_id,
        "stability": stability,
        "characters": len(text),
        "duration_s": round(measure(incoming), 3),
        "alignment": alignment,
    }
    # tts.json duluan, voice.mp3 terakhir. Keberadaan voice.mp3 = step selesai + naskah dikunci.
    write_json_atomic(paths.tts_json, data)
    os.replace(incoming, paths.voice_mp3)
    incoming_meta.unlink(missing_ok=True)
    return data
