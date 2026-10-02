from PIL import Image

from mayzfact.ffmpeg import extract_frame, sample_frames
from mayzfact.scenes import detect_cuts, merge_cuts, segments

# Cut asli dari 10 detik awal i2xag_1OJfM (filter scene 0.25)
I2X_CUTS = [0.0667, 1.15, 1.1833, 1.2333, 1.2667, 1.3167, 1.6833, 1.7333, 1.9, 1.9833,
            2.4333, 2.4833, 3.6667, 6.0667, 6.0833, 6.1, 6.1167, 8.45, 8.5]


def test_merge_cuts_keeps_last_cut_of_each_burst():
    assert merge_cuts(I2X_CUTS) == [0.067, 1.983, 2.483, 3.667, 6.117, 8.5]
    assert merge_cuts([]) == []


def test_segments_drop_short_pieces():
    assert segments([0.067, 1.983, 2.483, 3.667, 6.117, 8.5], 10.0) == [
        (0.067, 1.983), (1.983, 2.483), (2.483, 3.667), (3.667, 6.117), (6.117, 8.5), (8.5, 10.0),
    ]
    assert segments([], 3.0) == [(0.0, 3.0)]
    assert segments([0.2], 0.6) == []
    assert segments([4.0, 12.0], 10.0) == [(0.0, 4.0), (4.0, 10.0)]


def test_detect_cuts_finds_color_change(cut_video):
    cuts = detect_cuts(cut_video, 10.0)
    assert len(cuts) == 1
    assert abs(cuts[0] - 1.0) < 0.05


def _rgb(path):
    with Image.open(path) as img:
        return img.convert("RGB").getpixel((10, 10))


def test_extract_and_sample_frames(cut_video, tmp_path):
    red = _rgb(extract_frame(cut_video, 0.5, tmp_path / "a.jpg"))
    assert red[0] > 200 and red[2] < 60
    frames = sample_frames(cut_video, tmp_path / "s", every_s=0.5, max_s=2.0)
    assert [t for t, _ in frames][:4] == [0.0, 0.5, 1.0, 1.5]
    blue = _rgb(frames[3][1])
    assert blue[2] > 200 and blue[0] < 60
    again = sample_frames(cut_video, tmp_path / "s", every_s=1.0, max_s=2.0)
    assert len(again) == len(list((tmp_path / "s").glob("f_*.jpg")))
