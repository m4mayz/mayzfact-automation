"""Normalisasi foto: ikutin orientasi EXIF, jadi RGB, resize (cuma ngecilin), simpan JPG."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageOps

from mayzfact.media import PHOTO_ZOOM, downscale_factor
from mayzfact.store import tmp_path_for


def normalize_photo(src: Path, dest: Path, *, fg_min_ratio: float) -> tuple[int, int]:
    with Image.open(src) as opened:
        img = ImageOps.exif_transpose(opened).convert("RGB")
    factor = downscale_factor(img.width, img.height, fg_min_ratio, PHOTO_ZOOM)
    if factor < 1.0:
        img = img.resize((round(img.width * factor), round(img.height * factor)), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_path_for(dest)
    img.save(tmp, "JPEG", quality=92)
    os.replace(tmp, dest)
    return img.size
