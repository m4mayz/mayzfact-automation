"""Deteksi posisi subjek di frame pakai OWLv2 (open-vocabulary), buat panah/lingkaran (spec Fase 3C-1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from mayzfact.config import MODELS_DIR
from mayzfact.errors import PipelineError

OWL_MODEL = "google/owlv2-base-patch16-ensemble"
OWL_REVISION = "cfd3195ba4ea9592eec887ded089f4c08eff231d"  # di-pin: ukuran download fix 621 MB


class Detector(Protocol):
    def best_box(self, image: Path, query: str) -> tuple[float, tuple[float, float, float, float]] | None: ...


class Owlv2Detector:
    """Kotak skor tertinggi buat query, dinormalisasi 0..1 terhadap ukuran gambar."""

    def __init__(self, cache_dir: Path = MODELS_DIR) -> None:
        self._cache_dir = str(cache_dir)
        self._model: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import Owlv2ForObjectDetection, Owlv2Processor

            self._processor = Owlv2Processor.from_pretrained(OWL_MODEL, revision=OWL_REVISION, cache_dir=self._cache_dir)
            model = Owlv2ForObjectDetection.from_pretrained(OWL_MODEL, revision=OWL_REVISION, cache_dir=self._cache_dir)
        except Exception as exc:
            raise PipelineError("timeline", f"Model {OWL_MODEL} gagal di-load: {exc}. Download pertama butuh internet (621 MB).") from exc
        self._torch = torch
        self._model = model.eval()

    def best_box(self, image: Path, query: str) -> tuple[float, tuple[float, float, float, float]] | None:
        self._load()
        from PIL import Image

        torch = self._torch
        with Image.open(image) as img:
            rgb = img.convert("RGB")
        width, height = rgb.size
        side = max(width, height)  # OWLv2 nge-pad gambar jadi kotak, jadi koordinatnya relatif ke sisi terpanjang
        with torch.no_grad():
            inputs = self._processor(text=[[f"a photo of a {query}"]], images=rgb, return_tensors="pt")
            outputs = self._model(**inputs)
        result = self._processor.post_process_grounded_object_detection(
            outputs, threshold=0.0, target_sizes=torch.tensor([[side, side]])
        )[0]
        if len(result["scores"]) == 0:
            return None
        best = int(result["scores"].argmax())
        x0, y0, x1, y1 = (float(v) for v in result["boxes"][best])
        clip = lambda v, limit: min(max(v, 0.0), limit) / limit  # noqa: E731
        return float(result["scores"][best]), (clip(x0, width), clip(y0, height), clip(x1, width), clip(y1, height))
