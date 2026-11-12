"""Step tts: bikin voice.mp3 + tts.json. Cuma jalan kalau suara belum ada (aturan kunci, spec 3.4)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Protocol

from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import _run, audio_duration
from mayzfact.store import (
    RunPaths,
    read_json,
    tmp_path_for,
    write_bytes_atomic,
    write_json_atomic,
)
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
    max_gap_s: float = 0.0,
) -> dict:
    text = script_text(script["beats"])
    stability = getattr(tts, "stability", None)  # provider lama/fake di test boleh nggak punya
    delivery_tag = getattr(tts, "delivery_tag", "")
    provider = getattr(tts, "provider_name", "elevenlabs")
    identity = getattr(tts, "cache_identity", {"provider": provider, "voice_id": tts.voice_id,
                                              "model_id": tts.model_id, "stability": stability})
    audio_format = getattr(tts, "audio_format", "mp3")
    if audio_format not in ("mp3", "wav"):
        raise PipelineError("tts", "audio_format harus mp3 atau wav.")
    audio_file = f"voice.{audio_format}"
    incoming = paths.root / f"voice.incoming.{audio_format}"
    incoming_meta = paths.root / "tts.incoming.json"
    other_incoming = paths.root / ("voice.incoming.mp3" if audio_format == "wav" else "voice.incoming.wav")
    if other_incoming.exists():
        raise PipelineError("tts", f"Audio {other_incoming.name} sudah tersimpan untuk format lain. Jangan ditimpa.")
    native = paths.root / audio_file
    saved_wav = paths.root / "voice.wav"
    if paths.voice_mp3.exists():
        raise PipelineError("tts", "Audio voice.mp3 sudah tersimpan. Jangan ditimpa.")
    if saved_wav.exists() and (audio_format != "wav" or not incoming_meta.exists() or incoming.exists()):
        raise PipelineError("tts", "Audio voice.wav sudah tersimpan. Jangan ditimpa.")
    if audio_format == "wav" and native.exists() and incoming_meta.exists() and not incoming.exists():
        incoming = native
    # Audio yang udah dibayar disimpan dulu. Kalau langkah setelahnya gagal (mis. ffprobe), run berikutnya
    # pakai ulang file ini selama naskahnya sama, jadi ElevenLabs nggak ditagih dua kali.
    pending = read_json(incoming_meta) if incoming.exists() and incoming_meta.exists() else None
    legacy = pending is not None and "identity" not in pending and provider == "elevenlabs" and not delivery_tag
    if (pending is not None and pending["text_sha256"] == text_hash(text)
            and pending.get("audio_format", "mp3") == audio_format
            and (pending.get("identity") == identity or legacy)):
        log(f"[tts] Pakai audio {provider} yang udah tersimpan ({incoming.name})")
        alignment = pending["alignment"]
    else:
        if incoming.exists() or incoming_meta.exists():
            raise PipelineError("tts", f"Audio/metadata {incoming.name} sudah tersimpan untuk naskah/provider/format lain. "
                                "Jangan ditimpa; pulihkan setting lama atau pindahkan backup sebelum bikin suara baru.")
        log(f"[tts] Kirim {len(text)} karakter ke {provider} (voice {tts.voice_id}, model {tts.model_id}, stability {stability})")
        audio, alignment = tts.synthesize(text)
        write_bytes_atomic(incoming, audio)
        pending = {"text_sha256": text_hash(text), "alignment": alignment, "identity": identity,
                   "voice_id": tts.voice_id, "model_id": tts.model_id, "audio_format": audio_format}
        write_json_atomic(incoming_meta, pending)
    raw_alignment = alignment
    normalize = getattr(tts, "normalize_alignment", None)
    if normalize is not None:
        alignment = normalize(text, raw_alignment)
    if max_gap_s > 0 and script.get("narration_mode") == "faktacuil":
        alignment = _apply_pause_rule(incoming, alignment, max_gap_s, log)
    data = {
        "provider": provider,
        "text_sha256": text_hash(text),
        "voice_id": pending.get("voice_id", tts.voice_id),
        "model_id": pending.get("model_id", tts.model_id),
        "stability": stability,
        "characters": len(text),
        "duration_s": round(measure(incoming), 3),
        "alignment": alignment,
        "audio_file": audio_file,
    }
    if delivery_tag:
        data["delivery_tag"] = delivery_tag
        data["raw_alignment"] = raw_alignment
    # tts.json duluan, voice.mp3 terakhir. Keberadaan voice.mp3 = step selesai + naskah dikunci.
    write_json_atomic(paths.tts_json, data)
    if audio_format == "wav":
        if incoming != native:
            os.replace(incoming, native)
        compatible = tmp_path_for(paths.voice_mp3)
        _run(["ffmpeg", "-y", "-v", "error", "-i", str(native), "-vn", "-c:a", "libmp3lame",
              "-b:a", "128k", str(compatible)], "tts")
        os.replace(compatible, paths.voice_mp3)
    else:
        os.replace(incoming, paths.voice_mp3)
    incoming_meta.unlink(missing_ok=True)
    return data


def _apply_pause_rule(incoming: Path, alignment: dict, max_gap_s: float,
                      log: Callable[[str], None]) -> dict:
    """FaktaCuil: hening antar kalimat dipotong sampai maksimal `max_gap_s` detik.

    Dipotong di file audio yang belum dipindah ke voice.mp3, lalu timestamp karakter
    digeser sesuai total potongan supaya plan/timeline tetap nyambung sama suaranya.
    """
    from mayzfact.pauses import (
        detect_silences,
        keep_segments,
        plan_cuts,
        shift_alignment,
        trim_audio,
    )

    cuts = plan_cuts(detect_silences(incoming), max_gap_s)
    if not cuts:
        log(f"[tts] jeda udah <= {max_gap_s:g} detik, audio nggak dipotong")
        return alignment
    duration = audio_duration(incoming)
    total = sum(end - start for start, end in cuts)
    # Jaga-jaga: klip yang hampir semua hening (fixture/dummy) jangan sampai dipotong habis.
    if duration - total < 1.0 or total > 0.6 * duration:
        log("[tts] potongan jeda dilewati: audionya kependekan atau hampir semua hening")
        return alignment
    trimmed = tmp_path_for(incoming)
    trim_audio(incoming, trimmed, keep_segments(duration, cuts), _run)
    os.replace(trimmed, incoming)
    log(f"[tts] potong {len(cuts)} jeda panjang (maks {max_gap_s:g} detik): {duration:.2f} -> {duration - total:.2f} detik")
    return shift_alignment(alignment, cuts)
