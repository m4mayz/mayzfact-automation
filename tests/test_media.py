import pytest

from mayzfact.media import downscale_factor, fg_height, layout_for, needed_scale, pick_rendition, tier
from mayzfact.providers.types import Candidate, Rendition
from tests.factories import cand


@pytest.mark.parametrize(
    ("width", "height", "layout"),
    [(1080, 1920, "full"), (1440, 1920, "full"), (1080, 1350, "blur"), (1920, 1080, "blur"), (1000, 1000, "blur")],
)
def test_layout_for(width, height, layout):
    assert layout_for(width, height) == layout


@pytest.mark.parametrize(
    ("width", "height", "ratio", "expected"),
    [(1920, 1080, 0.5, 960), (1080, 1080, 0.5, 1080), (1440, 1080, 0.5, 960), (1920, 1080, 0.4, 768), (1080, 1350, 0.5, 1350)],
)
def test_fg_height(width, height, ratio, expected):
    assert fg_height(width, height, ratio) == expected


def test_needed_scale():
    assert needed_scale(2160, 3840, 0.5) == 0.5
    assert needed_scale(1080, 1920, 0.5) == 1.0
    assert needed_scale(1920, 1080, 0.5) == pytest.approx(0.8889, abs=1e-4)
    assert needed_scale(1280, 720, 0.5) == pytest.approx(1.3333, abs=1e-4)
    assert needed_scale(1080, 1920, 0.5, zoom=1.08) == pytest.approx(1.08)


def test_tier():
    assert tier(cand("pexels", "a", width=2160, height=3840), 0.5) == 1
    assert tier(cand("pexels", "b", width=1920, height=1080), 0.5) == 2
    assert tier(cand("pexels", "c", width=1280, height=720), 0.5) == 3
    assert tier(cand("pexels", "d", kind="photo", width=3000, height=4500), 0.5) == 1
    assert tier(cand("pixabay", "e", kind="photo", width=1280, height=853), 0.5) == 3


def _video(*sizes):
    return Candidate(
        provider="pexels", id="1", kind="video", duration_s=10.0, page_url="", author="", rank=0,
        renditions=tuple(Rendition(f"https://cdn.test/{w}x{h}.mp4", w, h) for w, h in sizes),
    )


def test_pick_rendition_takes_smallest_sharp_one():
    assert pick_rendition(_video((3840, 2160), (1920, 1080), (1280, 720)), 0.5).width == 1920
    assert pick_rendition(_video((2160, 3840), (1080, 1920), (720, 1280)), 0.5).height == 1920


def test_pick_rendition_falls_back_to_largest():
    assert pick_rendition(_video((640, 360), (960, 540)), 0.5).width == 960


def test_downscale_factor_never_upscales():
    assert downscale_factor(3840, 2160, 0.5) == pytest.approx(0.4444, abs=1e-4)
    assert downscale_factor(720, 1280, 0.5) == 1.0
