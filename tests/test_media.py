import pytest

from mayzfact.media import downscale_factor, fg_height, layout_for, needed_scale


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










def test_downscale_factor_never_upscales():
    assert downscale_factor(3840, 2160, 0.5) == pytest.approx(0.4444, abs=1e-4)
    assert downscale_factor(720, 1280, 0.5) == 1.0
