"""Kotak blur di atas teks yang kebaca di klip: watermark, username, subtitle bawaan (D-038)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol

from mayzfact.ffmpeg import extract_frame
from mayzfact.store import RunPaths, read_json, write_json_atomic

MIN_TEXT_SCORE = 0.8  # keyakinan RapidOCR baca teksnya; di bawah ini biasanya tekstur/pola (percikan api "ni" 0.65)
MIN_LINE_RATIO = 1.2  # baris teks lebih lebar dari tingginya; kotak persegi/tinggi biasanya salah deteksi
MIN_TEXT_CHARS = 2
PAD = 0.012  # kotak dilebarin dikit biar ujung huruf ikut ketutup
SAMPLES = (0.2, 0.5, 0.8)  # posisi frame sampel di klip video (teks yang muncul sebentar bisa kelewat)
DETECT_WIDTH = 720

Box = tuple[float, float, float, float]


class TextDetector(Protocol):
    def boxes(self, image: Path) -> list[Box]: ...


def text_boxes_from_ocr(result: Any, *, width: int, height: int, min_score: float = MIN_TEXT_SCORE) -> list[Box]:
    """Hasil RapidOCR [(4 titik, teks, skor)] → kotak 0..1 buat teks yang yakin kebaca."""
    out: list[Box] = []
    for points, text, score in result or []:
        if float(score) < min_score or len(str(text).strip()) < MIN_TEXT_CHARS:
            continue
        xs = [float(p[0]) for p in points]
        ys = [float(p[1]) for p in points]
        if max(xs) - min(xs) < MIN_LINE_RATIO * (max(ys) - min(ys)):
            continue
        out.append((min(xs) / width, min(ys) / height, max(xs) / width, max(ys) / height))
    return out


def merge_boxes(boxes: list[Box], *, pad: float = PAD) -> list[Box]:
    """Kotak dilebarin `pad`, dipotong ke 0..1, terus yang numpuk digabung jadi satu."""
    merged = [(max(0.0, x0 - pad), max(0.0, y0 - pad), min(1.0, x1 + pad), min(1.0, y1 + pad)) for x0, y0, x1, y1 in boxes]
    changed = True
    while changed:  # ponytail: O(n²) per putaran; kotak per klip cuma belasan
        changed = False
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                a, b = merged[i], merged[j]
                if a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]:
                    merged[i] = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
                    del merged[j]
                    changed = True
                    break
            if changed:
                break
    return merged


class RapidTextDetector:
    """Deteksi + baca teks pakai RapidOCR (ONNX, CPU). Model-nya ikut paket pip, nggak download lagi."""

    def __init__(self) -> None:
        self._engine: Any = None

    def boxes(self, image: Path) -> list[Box]:
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()
        from PIL import Image

        with Image.open(image) as img:
            width, height = img.size
        result, _ = self._engine(str(image), use_det=True, use_cls=False, use_rec=True)
        return text_boxes_from_ocr(result, width=width, height=height)


def _clip_boxes(paths: RunPaths, clip: dict, source: Path, detector: TextDetector) -> list[Box]:
    if clip["kind"] != "video":
        return merge_boxes(detector.boxes(source))
    duration = clip["end_s"] - clip["start_s"]
    found: list[Box] = []
    for i, pos in enumerate(SAMPLES):
        frame = extract_frame(source, duration * pos, paths.root / "textblur" / f"{source.stem}_{i}.jpg", width=DETECT_WIDTH)
        found.extend(detector.boxes(frame))
    return merge_boxes(found)


def prepare_text_blurs(paths: RunPaths, clips: dict, detector: TextDetector, *,
                       log: Callable[[str], None]) -> dict[str, list[Box]]:
    """{file klip: [kotak 0..1]} buat klip yang ada teksnya. Di-cache di textblur.json per file + ukuran + waktu ubah."""
    cache_path = paths.root / "textblur.json"
    cache = read_json(cache_path) if cache_path.exists() else {}
    out: dict[str, list[Box]] = {}
    for clip in clips["shots"]:
        source = paths.root / clip["file"]
        if not source.exists():
            continue
        stat = source.stat()
        key = f"{stat.st_size}-{stat.st_mtime_ns}"
        if cache.get(clip["file"], {}).get("key") == key:
            boxes = [tuple(b) for b in cache[clip["file"]]["boxes"]]
        else:
            try:
                boxes = _clip_boxes(paths, clip, source, detector)
            except Exception as exc:  # blur cuma hiasan: 1 klip gagal, klip lain tetap jalan
                log(f"[timeline] blur teks {clip['file']} dilewat: {type(exc).__name__}: {exc}")
                continue
            cache[clip["file"]] = {"key": key, "boxes": [list(b) for b in boxes]}
            write_json_atomic(cache_path, cache)
            if boxes:
                log(f"[timeline] blur teks {clip['file']}: {len(boxes)} kotak")
        if boxes:
            out[clip["file"]] = boxes
    return out
