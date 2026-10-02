import httpx
import numpy as np
from PIL import Image

from mayzfact.embed import unit
from mayzfact.scoring import ThumbScorer
from mayzfact.thumbs import fetch_thumbnail
from tests.factories import cand


class FakeEncoder:
    def __init__(self, table):
        self.table = table

    def images(self, paths):
        return unit(np.stack([self.table[p.stem] for p in paths]))

    def texts(self, texts):
        return unit(np.array([[1.0, 0.0]]))


def test_thumb_scorer_scores_text_against_thumbnails(tmp_path):
    good = tmp_path / "good.jpg"
    Image.new("RGB", (8, 8)).save(good)
    other = tmp_path / "other.jpg"
    Image.new("RGB", (8, 8)).save(other)
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"<html>")
    files = {"a": good, "b": other, "c": broken, "d": None}
    scorer = ThumbScorer(FakeEncoder({"good": np.array([1.0, 0.0]), "other": np.array([0.0, 1.0])}), lambda c: files[c.id])
    scores = scorer.score("a horseshoe crab", [cand("pexels", i) for i in "abcd"])
    assert scores[0] > scores[1]
    assert scores[2:] == [-1.0, -1.0]


def test_fetch_thumbnail(tmp_path):
    def handler(request):
        if request.url.path == "/ok.jpg":
            return httpx.Response(200, content=b"jpg-bytes")
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    ok = fetch_thumbnail(client, tmp_path, cand("pexels", "1", thumbnail_url="https://cdn.test/ok.jpg"))
    assert ok == tmp_path / "pexels_1.jpg" and ok.read_bytes() == b"jpg-bytes"
    assert fetch_thumbnail(client, tmp_path, cand("pexels", "2", thumbnail_url="https://cdn.test/missing.jpg")) is None
    assert fetch_thumbnail(client, tmp_path, cand("pexels", "3", thumbnail_url="")) is None


def test_thumb_scorer_encodes_each_thumbnail_once(tmp_path):
    paths = {}
    for name in ("a", "b"):
        paths[name] = tmp_path / f"{name}.jpg"
        Image.new("RGB", (8, 8)).save(paths[name])

    class CountingEncoder(FakeEncoder):
        def __init__(self, table):
            super().__init__(table)
            self.image_calls, self.text_calls = [], 0

        def images(self, items):
            self.image_calls.append([p.stem for p in items])
            return super().images(items)

        def texts(self, texts):
            self.text_calls += 1
            return super().texts(texts)

    encoder = CountingEncoder({"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0])})
    scorer = ThumbScorer(encoder, lambda c: paths[c.id])
    first = scorer.score("crab", [cand("pexels", "a")])
    second = scorer.score("crab", [cand("pexels", "a"), cand("pexels", "b")])
    assert second[0] == first[0]
    assert encoder.image_calls == [["a"], ["b"]]
    assert encoder.text_calls == 1
