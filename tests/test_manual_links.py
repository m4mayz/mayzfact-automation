import pytest

from mayzfact.manual.links import (
    link_kind,
    load_links,
    missing_shots,
    normalize_links,
    parse_entry,
    save_links,
)


def test_parse_entry_extracts_url_from_share_text_and_pick():
    assert parse_entry("https://www.xiaohongshu.com/explore/abc #3") == ("https://www.xiaohongshu.com/explore/abc", 3)
    assert parse_entry("  https://v.douyin.com/iRNBho6u/  ") == ("https://v.douyin.com/iRNBho6u/", None)
    share = "8.97 复制打开抖音，看看【鲎】躲过五次大灭绝 https://v.douyin.com/iRNBho6u/ x@W.zt 09/12"
    assert parse_entry(share) == ("https://v.douyin.com/iRNBho6u/", None)
    assert parse_entry("https://www.tiktok.com/@a/video/1#ref") == ("https://www.tiktok.com/@a/video/1#ref", None)
    assert parse_entry("bukan link") == ("bukan link", None)


@pytest.mark.parametrize(("url", "kind"), [
    ("https://www.douyin.com/video/7694448955383418155", "douyin"),
    ("https://v.douyin.com/iRNBho6u/", "douyin"),
    ("https://www.xiaohongshu.com/explore/66a1b2c3d4e5f6a7b8c9d0e1", "rednote"),
    ("http://xhslink.com/a/xyz", "rednote"),
    ("https://www.tiktok.com/@a/video/1", "tiktok"),
    ("https://id.pinterest.com/pin/123/", "pinterest"),
    ("https://pin.it/abc", "pinterest"),
    ("https://cdn.example.com/a/b.JPG?x=1", "direct"),
    ("https://example.com/clip.mp4", "direct"),
    ("https://example.com/page", "other"),
])
def test_link_kind(url, kind):
    assert link_kind(url) == kind


def test_normalize_links_validates_and_keeps_pick():
    raw = {"shots": {
        "1": {"url": "https://v.douyin.com/x/ #2"},
        "2": {"file": "manual/shot_02.mp4"},
        "3": {"url": "  "},
        "4": {"url": "https://example.com/a.jpg", "pick": 1},
    }}
    assert normalize_links(raw, 4) == {"shots": {
        "1": {"url": "https://v.douyin.com/x/", "pick": 2},
        "2": {"file": "manual/shot_02.mp4"},
        "4": {"url": "https://example.com/a.jpg", "pick": 1},
    }}
    with pytest.raises(ValueError, match="shot 9"):
        normalize_links({"shots": {"9": {"url": "https://a.b/c"}}}, 4)
    with pytest.raises(ValueError, match="http"):
        normalize_links({"shots": {"1": {"url": "ftp://a/b"}}}, 4)
    with pytest.raises(ValueError, match="manual/"):
        normalize_links({"shots": {"1": {"file": "../../.env"}}}, 4)


def test_load_save_and_missing(tmp_path):
    path = tmp_path / "links.json"
    assert load_links(path) == {"shots": {}}
    save_links(path, {"shots": {"2": {"url": "https://a.b/c"}}})
    plan = {"shots": [{"index": 0}, {"index": 1}, {"index": 2}]}
    assert missing_shots(plan, load_links(path)) == [1, 3]
