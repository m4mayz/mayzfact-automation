import pytest

from mayzfact.manual.links import (
    lines_of,
    link_kind,
    load_links,
    missing_groups,
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


def test_normalize_links_parses_lines_per_group():
    raw = {"groups": {
        "hook": "复制打开抖音 https://v.douyin.com/x/ 看看\n\n  https://a.b/p.jpg #2  \nfile:manual/hook_1.mp4",
        "nautilus": "   ",
        "platypus": [{"url": "https://a.b/q"}],
    }}
    assert normalize_links(raw, ["hook", "nautilus", "platypus"]) == {"groups": {
        "hook": [{"url": "https://v.douyin.com/x/"}, {"url": "https://a.b/p.jpg", "pick": 2}, {"file": "manual/hook_1.mp4"}],
        "platypus": [{"url": "https://a.b/q"}],
    }}


def test_normalize_links_rejects_bad_input():
    with pytest.raises(ValueError, match="kelompok sturgeon"):
        normalize_links({"groups": {"sturgeon": "https://a.b/c"}}, ["hook"])
    with pytest.raises(ValueError, match="http"):
        normalize_links({"groups": {"hook": "ftp://a/b"}}, ["hook"])
    with pytest.raises(ValueError, match="manual/"):
        normalize_links({"groups": {"hook": "file:../../.env"}}, ["hook"])
    with pytest.raises(ValueError, match="#"):
        normalize_links({"groups": {"hook": "https://a.b/c #0"}}, ["hook"])


def test_lines_round_trip():
    entries = [{"url": "https://a.b/p.jpg", "pick": 2}, {"file": "manual/hook_1.mp4"}]
    assert lines_of(entries) == "https://a.b/p.jpg #2\nfile:manual/hook_1.mp4"
    assert normalize_links({"groups": {"hook": lines_of(entries)}}, ["hook"])["groups"]["hook"] == entries


def test_load_save_and_missing(tmp_path):
    path = tmp_path / "links.json"
    assert load_links(path) == {"groups": {}}
    save_links(path, {"groups": {"crab": [{"url": "https://a.b/c"}]}})
    plan = {"groups": [{"id": "hook"}, {"id": "crab"}, {"id": "fossil"}]}
    assert missing_groups(plan, load_links(path)) == ["hook", "fossil"]
    save_links(path, {"shots": {"1": {"url": "https://a.b/c"}}})
    assert load_links(path) == {"shots": {"1": {"url": "https://a.b/c"}}}


def test_rednote_links_are_rejected_with_upload_hint():
    for url in ("http://xhslink.com/o/44jNwnYztNq", "复制 https://www.xiaohongshu.com/explore/66a1b2c3d4e5f6a7b8c9d0e1 打开"):
        with pytest.raises(ValueError, match="upload"):
            normalize_links({"groups": {"hook": url}}, ["hook"])
    assert normalize_links({"groups": {"hook": "file:manual/hook_1.mp4"}}, ["hook"])["groups"]["hook"] == [{"file": "manual/hook_1.mp4"}]


def test_normalize_links_per_shot():
    from mayzfact.manual.links import missing_shots
    raw = {"shots": {
        "0": "复制 https://v.douyin.com/x/ 打开",
        "1": "https://a.b/p.jpg #2",
        "2": "file:manual/shot_03.mp4",
        "3": "",
    }}
    res = normalize_links(raw, shot_count=4)
    assert res == {"shots": {
        "0": {"url": "https://v.douyin.com/x/"},
        "1": {"url": "https://a.b/p.jpg", "pick": 2},
        "2": {"file": "manual/shot_03.mp4"},
    }}
    plan = {"shots": [{"index": i} for i in range(4)]}
    assert missing_shots(plan, res) == [3]

    with pytest.raises(ValueError, match="shot 10"):
        normalize_links({"shots": {"9": "https://a.b/c"}}, shot_count=4)
