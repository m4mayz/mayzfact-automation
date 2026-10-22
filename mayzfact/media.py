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


def screen_box(box: tuple[float, float, float, float], width: int, height: int, *, fg_min_ratio: float) -> tuple[int, int, int, int]:
    """Kotak (0..1 di frame klip) → (x, y, w, h) piksel di layar 1080x1920, ngikutin layout full/blur."""
    if layout_for(width, height) == "full":
        area_y, area_h = 0, FRAME_H
    else:
        area_h = fg_height(width, height, fg_min_ratio)
        area_y = (FRAME_H - area_h) // 2
    scale = max(FRAME_W / width, area_h / height)  # objectFit cover
    off_x = (FRAME_W - width * scale) / 2
    off_y = area_y + (area_h - height * scale) / 2
    x0, y0, x1, y1 = box
    return (round(off_x + x0 * width * scale), round(off_y + y0 * height * scale),
            round((x1 - x0) * width * scale), round((y1 - y0) * height * scale))


def cover_box(box: tuple[float, float, float, float], width: int, height: int, area_w: float, area_h: float) -> dict:
    """Kotak (0..1 di klip) → piksel di area area_w x area_h yang nampilin klip pakai object-fit cover."""
    scale = max(area_w / width, area_h / height)
    off_x = (area_w - width * scale) / 2
    off_y = (area_h - height * scale) / 2
    x0, y0, x1, y1 = box
    return {"x": round(off_x + x0 * width * scale), "y": round(off_y + y0 * height * scale),
            "w": round((x1 - x0) * width * scale), "h": round((y1 - y0) * height * scale)}
