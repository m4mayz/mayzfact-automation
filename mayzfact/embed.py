"""Embedding gambar & teks pakai SigLIP (open_clip) di CPU. Model baru di-load waktu pertama dipakai."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import numpy as np
from PIL import Image, ImageOps

from mayzfact.errors import PipelineError

MODEL_NAME = "ViT-B-16-SigLIP"
PRETRAINED = "webli"


class Encoder(Protocol):
    def images(self, paths: list[Path]) -> np.ndarray: ...

    def texts(self, texts: list[str]) -> np.ndarray: ...


def unit(vectors: Any) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / np.maximum(norms, 1e-12)


def mean_unit(vectors: Any) -> np.ndarray:
    return unit(np.asarray(vectors, dtype=np.float32).mean(axis=0))


def can_open_image(path: Path) -> bool:
    try:
        with Image.open(path) as img:
            img.load()
        return True
    except Exception:
        return False


def _open_rgb(path: Path) -> Image.Image:
    with Image.open(path) as img:
        return ImageOps.exif_transpose(img).convert("RGB")


class SiglipEncoder:
    def __init__(self, batch_size: int = 32) -> None:
        self._batch_size = batch_size
        self._model: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import open_clip
            import torch

            model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
        except Exception as exc:
            raise PipelineError(
                "hook",
                f"Model {MODEL_NAME} ({PRETRAINED}) gagal di-load: {exc}. Download pertama butuh internet (±800 MB).",
            ) from exc
        model.eval()
        self._torch = torch
        self._preprocess = preprocess
        self._tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        self._model = model

    def images(self, paths: list[Path]) -> np.ndarray:
        self._load()
        chunks = []
        for start in range(0, len(paths), self._batch_size):
            batch = self._torch.stack([self._preprocess(_open_rgb(p)) for p in paths[start : start + self._batch_size]])
            with self._torch.no_grad():
                chunks.append(self._model.encode_image(batch).float().numpy())
        if not chunks:
            return np.zeros((0, 0), dtype=np.float32)
        return unit(np.concatenate(chunks))

    def texts(self, texts: list[str]) -> np.ndarray:
        self._load()
        with self._torch.no_grad():
            features = self._model.encode_text(self._tokenizer(list(texts))).float().numpy()
        return unit(features)
