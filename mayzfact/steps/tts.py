"""Step tts: bikin voice.mp3 + tts.json. Cuma jalan kalau suara belum ada (aturan kunci, spec 3.4)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Protocol

from mayzfact.errors import PipelineError
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
    provider = getattr(tts, "provider_name", "elevenlabs")
    identity = getattr(tts, "cache_identity", {"provider": provider, "voice_id": tts.voice_id,
                                              "model_id": tts.model_id, "stability": stability})
    incoming = paths.root / "voice.incoming.mp3"
    incoming_meta = paths.root / "tts.incoming.json"
    # Audio yang udah dibayar disimpan dulu. Kalau langkah setelahnya gagal (mis. ffprobe), run berikutnya
    # pakai ulang file ini selama naskahnya sama, jadi ElevenLabs nggak ditagih dua kali.
    pending = read_json(incoming_meta) if incoming.exists() and incoming_meta.exists() else None
    legacy = pending is not None and "identity" not in pending and provider == "elevenlabs"
    if (pending is not None and pending["text_sha256"] == text_hash(text)
            and (pending.get("identity") == identity or legacy)):
        log(f"[tts] Pakai audio {provider} yang udah tersimpan (voice.incoming.mp3)")
        alignment = pending["alignment"]
    else:
        if incoming.exists():
            raise PipelineError("tts", "Audio voice.incoming.mp3 sudah tersimpan untuk naskah/provider lain. "
                                "Jangan ditimpa; pulihkan setting lama atau pindahkan backup sebelum bikin suara baru.")
        log(f"[tts] Kirim {len(text)} karakter ke {provider} (voice {tts.voice_id}, model {tts.model_id}, stability {stability})")
        audio, alignment = tts.synthesize(text)
        write_bytes_atomic(incoming, audio)
        pending = {"text_sha256": text_hash(text), "alignment": alignment, "identity": identity,
                   "voice_id": tts.voice_id, "model_id": tts.model_id}
        write_json_atomic(incoming_meta, pending)
    data = {
        "provider": provider,
        "text_sha256": text_hash(text),
        "voice_id": pending.get("voice_id", tts.voice_id),
        "model_id": pending.get("model_id", tts.model_id),
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
