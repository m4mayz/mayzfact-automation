import numpy as np
import pytest
from PIL import Image, ImageDraw

from mayzfact.embed import SiglipEncoder, can_open_image, mean_unit, unit


def test_unit_and_mean_unit():
    vectors = unit(np.array([[3.0, 4.0], [0.0, 0.0]]))
    assert np.allclose(vectors[0], [0.6, 0.8])
    assert np.allclose(vectors[1], [0.0, 0.0])
    assert np.allclose(mean_unit(np.array([[1.0, 0.0], [0.0, 1.0]])), [0.7071, 0.7071], atol=1e-4)


def test_can_open_image(tmp_path):
    good = tmp_path / "a.jpg"
    Image.new("RGB", (8, 8)).save(good)
    html = tmp_path / "b.jpg"
    html.write_bytes(b"<html>403 Forbidden</html>")
    assert can_open_image(good)
    assert not can_open_image(html)
    assert not can_open_image(tmp_path / "missing.jpg")


@pytest.mark.clip
def test_siglip_prefers_similar_image_and_matching_text(tmp_path):
    def circle(name, dx):
        img = Image.new("RGB", (224, 224), "white")
        ImageDraw.Draw(img).ellipse((40 + dx, 40, 180 + dx, 180), fill="red")
        img.save(tmp_path / name)
        return tmp_path / name

    def stripes(name):
        img = Image.new("RGB", (224, 224), "white")
        draw = ImageDraw.Draw(img)
        for x in range(0, 224, 28):
            draw.rectangle((x, 0, x + 14, 224), fill="blue")
        img.save(tmp_path / name)
        return tmp_path / name

    encoder = SiglipEncoder()
    a, a2, b = encoder.images([circle("a.jpg", 0), circle("a2.jpg", 12), stripes("b.jpg")])
    assert a @ a2 > a @ b
    texts = encoder.texts(["a red circle", "blue vertical stripes"])
    assert a @ texts[0] > a @ texts[1]
    assert b @ texts[1] > b @ texts[0]
