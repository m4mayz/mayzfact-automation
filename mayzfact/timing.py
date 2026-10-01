"""Timing beat dari alignment per karakter ElevenLabs."""

from __future__ import annotations

from mayzfact.errors import PipelineError


def beat_offsets(texts: list[str]) -> list[int]:
    """Posisi karakter awal tiap beat di dalam ' '.join(texts)."""
    offsets: list[int] = []
    position = 0
    for text in texts:
        offsets.append(position)
        position += len(text) + 1
    return offsets


def beat_timings(texts: list[str], alignment: dict, audio_duration_s: float) -> list[dict]:
    """Beat pertama mulai 0.0, beat i selesai pas beat i+1 mulai, beat terakhir selesai di akhir audio."""
    full_text = " ".join(texts)
    chars = alignment["characters"]
    starts = alignment["character_start_times_seconds"]
    if len(chars) != len(full_text) or "".join(chars) != full_text or len(starts) != len(chars):
        raise PipelineError(
            "clips",
            "Alignment ElevenLabs nggak cocok sama teks naskah. voice.mp3 aman; "
            "benerin cara mapping-nya, jangan generate ulang suara.",
        )
    begins = [0.0] + [float(starts[offset]) for offset in beat_offsets(texts)[1:]]
    timings: list[dict] = []
    for index, start in enumerate(begins):
        end = begins[index + 1] if index + 1 < len(begins) else float(audio_duration_s)
        if end <= start:
            raise PipelineError("clips", f"Timing beat {index + 1} nggak valid ({start:.2f}s - {end:.2f}s).")
        timings.append({"start_s": round(start, 3), "end_s": round(end, 3)})
    return timings
