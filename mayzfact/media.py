"""Aturan layout (full/blur), ukuran yang dibutuhin, tier kualitas, dan pilihan rendition."""

from __future__ import annotations

FRAME_W = 1080
FRAME_H = 1920
FULL_MAX_ASPECT = 0.75
PHOTO_ZOOM = 1.08


def layout_for(width: int, height: int) -> str:
    return "full" if width / height <= FULL_MAX_ASPECT else "blur"


def fg_height(width: int, height: int, fg_min_ratio: float) -> int:
    """Tinggi kotak foreground layout blur: tinggi natural selebar 1080, min fg_min_ratio × 1920, max 1920."""
    natural = round(FRAME_W * height / width)
    return min(FRAME_H, max(natural, round(fg_min_ratio * FRAME_H)))


def needed_scale(width: int, height: int, fg_min_ratio: float, zoom: float = 1.0) -> float:
    """Skala media waktu tampil. Kalau > 1, media bakal di-upscale (kurang tajam)."""
    if layout_for(width, height) == "full":
        scale = max(FRAME_W / width, FRAME_H / height)
    else:
        scale = max(FRAME_W / width, fg_min_ratio * FRAME_H / height)
    return scale * zoom


def zoom_for(kind: str) -> float:
    return PHOTO_ZOOM if kind == "photo" else 1.0








def downscale_factor(width: int, height: int, fg_min_ratio: float, zoom: float = 1.0) -> float:
    """Faktor resize buat normalisasi. Cuma ngecilin, nggak pernah ngegedein."""
    return min(1.0, needed_scale(width, height, fg_min_ratio, zoom))
