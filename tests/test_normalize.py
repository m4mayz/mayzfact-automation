from PIL import Image

from mayzfact.ffmpeg import normalize_video, probe
from mayzfact.media import downscale_factor
from mayzfact.photo import normalize_photo
from tests.factories import stream_types


def test_normalize_video_downscales_trims_and_drops_audio(tmp_path, make_video):
    src = make_video(1440, 2560, 3.0)
    dest = tmp_path / "clips" / "shot_01.mp4"
    normalize_video(src, dest, start_s=0.5, duration_s=2.0, scale=downscale_factor(1440, 2560, 0.5))
    info = probe(dest, "clips")
    assert (info["width"], info["height"]) == (1080, 1920)
    assert abs(info["duration_s"] - 2.0) < 0.1
    assert stream_types(dest) == ["video"]
    assert sorted(p.name for p in dest.parent.iterdir()) == ["shot_01.mp4"]


def test_normalize_photo_applies_exif_rotation(tmp_path):
    src = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: putar 90 derajat searah jarum jam
    Image.new("RGB", (1200, 800), "red").save(src, exif=exif)
    dest = tmp_path / "shot_02.jpg"
    assert normalize_photo(src, dest, fg_min_ratio=0.5) == (800, 1200)
    with Image.open(dest) as img:
        assert img.size == (800, 1200)


def test_normalize_photo_only_downscales(tmp_path):
    big = tmp_path / "big.jpg"
    Image.new("RGB", (3000, 4500), "blue").save(big)
    assert normalize_photo(big, tmp_path / "a.jpg", fg_min_ratio=0.5) == (1382, 2074)
    small = tmp_path / "small.jpg"
    Image.new("RGB", (640, 480), "green").save(small)
    assert normalize_photo(small, tmp_path / "b.jpg", fg_min_ratio=0.5) == (640, 480)
