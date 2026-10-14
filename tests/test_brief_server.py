import threading

import httpx
import pytest

from mayzfact.brief.server import make_server
from mayzfact.store import RunPaths, read_json, write_json_atomic

PLAN = {
    "groups": [
        {"id": "hook", "label": "HOOK", "shots": [0], "keywords": {"en": ["crab beach"], "zh": ["鲎"]}},
        {"id": "fossil", "label": "fossil", "shots": [1, 2], "keywords": {"en": ["fossil"], "zh": []},
         "ref_frames": ["plan/fossil_0.jpg"]},
    ],
    "shots": [
        {"index": 0, "beat": 0, "start_s": 0.0, "end_s": 2.0, "media": "video", "text": "Look <b>at</b> this.", "subject": None,
         "hook_segment": 0, "ref_frames": ["plan/seg_01_0.jpg"], "keywords": {"en": ["crab beach"], "zh": ["鲎"]}, "group": "hook"},
        {"index": 1, "beat": 1, "start_s": 2.0, "end_s": 4.0, "media": "photo", "text": "Fossil.", "subject": "fossil",
         "hook_segment": None, "ref_frames": [], "keywords": {"en": ["fossil"], "zh": []}, "group": "fossil", "countdown": 2},
        {"index": 2, "beat": 2, "start_s": 4.0, "end_s": 6.0, "media": "video", "text": "Old rock.", "subject": "fossil",
         "hook_segment": None, "ref_frames": [], "keywords": {"en": ["fossil"], "zh": []}, "group": "fossil"},
    ],
}


@pytest.fixture
def server(tmp_path):
    paths = RunPaths(tmp_path / "abc")
    (paths.root / "plan").mkdir(parents=True)
    (paths.root / "plan" / "seg_01_0.jpg").write_bytes(b"jpg")
    (tmp_path / "secret.txt").write_text("rahasia")
    write_json_atomic(paths.shots_plan_json, PLAN)
    srv = make_server(paths, 0, max_upload=1000)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield paths, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def test_page_lists_groups_and_escapes_text(server):
    paths, base = server
    html = httpx.get(base + "/").text
    assert "Look &lt;b&gt;at&lt;/b&gt; this." in html and "Old rock." in html
    assert "鲎" in html and "HOOK" in html and "/files/plan/seg_01_0.jpg" in html
    assert "0/2 kelompok" in html
    assert "/files/plan/fossil_0.jpg" in html
    assert "CARD #2" in html
    write_json_atomic(paths.links_json, {"groups": {"fossil": [{"url": "https://a.b/c", "pick": 2}, {"file": "manual/fossil_1.mp4"}]}})
    html = httpx.get(base + "/").text
    assert "https://a.b/c #2\nfile:manual/fossil_1.mp4</textarea>" in html and "1/2 kelompok" in html


def test_save_links_validates(server):
    paths, base = server
    ok = httpx.post(base + "/api/links", json={"groups": {"hook": "复制 https://v.douyin.com/x/ 打开\nhttps://a.b/c #3"}})
    assert ok.status_code == 200 and ok.json()["missing"] == ["fossil"]
    assert read_json(paths.links_json) == {"groups": {"hook": [{"url": "https://v.douyin.com/x/"}, {"url": "https://a.b/c", "pick": 3}]}}
    bad = httpx.post(base + "/api/links", json={"groups": {"nautilus": "https://a.b/c"}})
    assert bad.status_code == 400 and "nautilus" in bad.json()["error"]


def test_upload_appends_file_to_group(server):
    paths, base = server
    httpx.post(base + "/api/links", json={"groups": {"fossil": "https://a.b/c"}})
    ok = httpx.post(base + "/api/upload?group=fossil", content=b"video-bytes", headers={"X-Filename": "klip.MP4"})
    assert ok.status_code == 200 and ok.json()["file"] == "manual/fossil_1.mp4"
    again = httpx.post(base + "/api/upload?group=fossil", content=b"jpg", headers={"X-Filename": "a.jpg"})
    assert again.json()["file"] == "manual/fossil_2.jpg"
    assert (paths.root / "manual" / "fossil_1.mp4").read_bytes() == b"video-bytes"
    assert read_json(paths.links_json)["groups"]["fossil"] == [
        {"url": "https://a.b/c"}, {"file": "manual/fossil_1.mp4"}, {"file": "manual/fossil_2.jpg"}]
    assert httpx.post(base + "/api/upload?group=fossil", content=b"x", headers={"X-Filename": "a.exe"}).status_code == 400
    assert httpx.post(base + "/api/upload?group=..%2F..", content=b"x", headers={"X-Filename": "a.jpg"}).status_code == 400
    assert httpx.post(base + "/api/upload?group=hook", content=b"x" * 2000, headers={"X-Filename": "a.jpg"}).status_code == 413


def test_files_are_confined_to_run_dir(server):
    _, base = server
    assert httpx.get(base + "/files/plan/seg_01_0.jpg").content == b"jpg"
    assert httpx.get(base + "/files/../secret.txt").status_code == 404
    assert httpx.get(base + "/files/%2E%2E/secret.txt").status_code == 404
    assert httpx.get(base + "/api/state").json()["plan"]["shots"][0]["index"] == 0


def test_source_video_is_shown_and_seekable(server):
    paths, base = server
    assert "<video" not in httpx.get(base + "/").text  # source.mp4 belum ada
    paths.source_mp4.write_bytes(b"0123456789")
    assert '<video src="/files/source.mp4"' in httpx.get(base + "/").text
    full = httpx.get(base + "/files/source.mp4")
    assert full.content == b"0123456789" and full.headers["accept-ranges"] == "bytes"
    # Chrome cuma bisa seek video kalau server ngerti header Range
    part = httpx.get(base + "/files/source.mp4", headers={"Range": "bytes=2-5"})
    assert part.status_code == 206 and part.content == b"2345" and part.headers["content-range"] == "bytes 2-5/10"
    assert httpx.get(base + "/files/source.mp4", headers={"Range": "bytes=7-"}).content == b"789"
    assert httpx.get(base + "/files/source.mp4", headers={"Range": "bytes=-3"}).content == b"789"
    assert httpx.get(base + "/files/source.mp4", headers={"Range": "bytes=20-"}).status_code == 416


def test_cross_site_posts_are_rejected(server):
    paths, base = server
    evil = {"Origin": "https://evil.example"}
    assert httpx.post(base + "/api/links", json={"groups": {}}, headers=evil).status_code == 403
    assert httpx.post(base + "/api/upload?group=hook", content=b"x", headers={**evil, "X-Filename": "a.jpg"}).status_code == 403
    assert not paths.links_json.exists()
    same = {"Origin": base}
    assert httpx.post(base + "/api/links", json={"groups": {}}, headers=same).status_code == 200


def test_foreign_host_header_is_rejected(server):
    paths, base = server
    port = base.rsplit(":", 1)[1]
    rebound = {"Host": f"evil.example:{port}", "Origin": f"http://evil.example:{port}"}
    assert httpx.get(base + "/api/state", headers=rebound).status_code == 403
    assert httpx.post(base + "/api/links", json={"groups": {}}, headers=rebound).status_code == 403
    assert not paths.links_json.exists()
    assert httpx.get(base + "/", headers={"Host": f"localhost:{port}"}).status_code == 200


def test_progress_endpoint_and_panel(server):
    paths, base = server
    assert httpx.get(base + "/api/progress").json() == {}
    write_json_atomic(paths.fetch_progress_json, {"state": "running", "links_done": 1, "links_total": 3})
    assert httpx.get(base + "/api/progress").json()["links_total"] == 3
    assert 'id="progress"' in httpx.get(base + "/").text
