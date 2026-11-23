"""Whisper lokal buat timing kata suara upload manual, lalu dipasangin ke kata naskah."""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from mayzfact.config import MODELS_DIR
from mayzfact.errors import PipelineError

MIN_MATCH = 0.7  # di bawah ini hampir pasti file suara video lain
_PIPELINES: dict[str, object] = {}


def transcribe_words(path: Path, *, model: str, language: str, cache_dir: Path = MODELS_DIR) -> list[dict]:
    if model not in _PIPELINES:
        import torch
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

        processor = AutoProcessor.from_pretrained(model, cache_dir=cache_dir)
        whisper = AutoModelForSpeechSeq2Seq.from_pretrained(model, cache_dir=cache_dir)
        _PIPELINES[model] = pipeline("automatic-speech-recognition", model=whisper, tokenizer=processor.tokenizer,
                                     feature_extractor=processor.feature_extractor,
                                     device=0 if torch.cuda.is_available() else -1)
    out = _PIPELINES[model](str(path), return_timestamps="word",
                            generate_kwargs={"language": language, "task": "transcribe"})
    return [{"word": c["text"].strip(), "start": c["timestamp"][0], "end": c["timestamp"][1]}
            for c in out.get("chunks", [])]


def _norm(word: str) -> str:
    return "".join(c for c in word.casefold() if c.isalnum())


def _spread(words: list[str], start: float, end: float) -> list[tuple[float, float]]:
    """Bagi rentang waktu ke beberapa kata sesuai panjang hurufnya."""
    weights = [max(1, len(_norm(w))) for w in words]
    total, spans, cursor = sum(weights), [], start
    for i, weight in enumerate(weights):
        stop = end if i == len(words) - 1 else cursor + (end - start) * weight / total
        spans.append((cursor, stop))
        cursor = stop
    return spans


def align_heard(text: str, heard: list[dict], duration: float) -> list[dict]:
    """Satu entri {word, start, end} per kata naskah, waktunya dari kata yang kedengeran."""
    script = [m.group() for m in re.finditer(r"\S+", text) if any(c.isalnum() for c in m.group())]
    clean: list[dict] = []
    for item in heard:
        if not _norm(str(item.get("word", ""))):
            continue
        start = item.get("start")
        start = clean[-1]["end"] if start is None and clean else (start or 0.0)
        end = item.get("end")
        end = min(start + 0.3, duration) if end is None else end
        clean.append({"word": str(item["word"]), "start": float(start), "end": float(end)})
    a = [_norm(w) for w in script]
    b = [_norm(w["word"]) for w in clean]
    times: list[tuple[float, float]] = []
    matched = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "insert":
            continue
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                times.append((clean[j1 + k]["start"], clean[j1 + k]["end"]))
                # Ejaan beda (nggak/gak, like/laik) tetap dihitung cocok, kata lain nggak.
                if tag == "equal" or difflib.SequenceMatcher(None, a[i1 + k], b[j1 + k]).ratio() >= 0.5:
                    matched += 1
        elif tag == "replace":  # kata digabung/dipecah beda sama naskah ("sangat besar" jadi "sangatbesar")
            times += _spread(script[i1:i2], clean[j1]["start"], clean[j2 - 1]["end"])
            if difflib.SequenceMatcher(None, "".join(a[i1:i2]), "".join(b[j1:j2])).ratio() >= 0.5:
                matched += i2 - i1
        else:  # kata naskah nggak kedengeran: isi celah sampai kata berikutnya
            left = times[-1][1] if times else 0.0
            right = clean[j1]["start"] if j1 < len(clean) else duration
            times += _spread(script[i1:i2], left, max(right, left))
    if not script or matched / len(script) < MIN_MATCH:
        percent = round(100 * matched / max(1, len(script)))
        raise PipelineError("tts", f"Suara upload nggak cocok sama naskah ({percent}% kata cocok). "
                                   "Cek file-nya, upload ulang, terus jalanin lagi.")
    words, previous_end = [], 0.0
    for word, (start, end) in zip(script, times, strict=True):
        start = max(start, previous_end)
        end = max(end, start + 0.01)
        words.append({"word": word, "start": start, "end": end})
        previous_end = end
    return words
