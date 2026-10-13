import threading

import httpx
import pytest

from mayzfact.brief.server import make_server
from mayzfact.store import RunPaths, read_json, write_json_atomic

PLAN = {"shots": [
    {"index": 0, "beat": 0, "start_s": 0.0, "end_s": 2.0, "media": "video", "text": "Look <b>at</b> this.", "subject": None,
     "hook_segment": 0, "ref_frames": ["plan/seg_01_0.jpg"], "keywords": {"en": ["crab beach"], "zh": ["鲎"]}},
    {"index": 1, "beat": 1, "start_s": 2.0, "end_s": 4.0, "media": "photo", "text": "Fossil.", "subject": "fossil",
     "hook_segment": None, "ref_frames": [], "keywords": {"en": ["fossil"], "zh": []}},
]}


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


def test_page_lists_shots_and_escapes_text(server):
    _, base = server
    html = httpx.get(base + "/").text
    assert "Look &lt;b&gt;at&lt;/b&gt; this." in html
    assert "鲎" in html and "HOOK" in html and "/files/plan/seg_01_0.jpg" in html
    assert "0/2" in html


def test_save_links_validates(server):
    paths, base = server
    ok = httpx.post(base + "/api/links", json={"shots": {"1": {"url": "复制 https://v.douyin.com/x/ 打开"}}})
    assert ok.status_code == 200 and ok.json()["missing"] == [2]
    assert read_json(paths.links_json) == {"shots": {"1": {"url": "https://v.douyin.com/x/"}}}
    bad = httpx.post(base + "/api/links", json={"shots": {"7": {"url": "https://a.b/c"}}})
    assert bad.status_code == 400 and "shot 7" in bad.json()["error"]


def test_upload_saves_file_and_links_it(server):
    paths, base = server
    ok = httpx.post(base + "/api/upload?shot=2", content=b"video-bytes", headers={"X-Filename": "klip.MP4"})
    assert ok.status_code == 200 and ok.json()["file"] == "manual/shot_02.mp4"
    assert (paths.root / "manual" / "shot_02.mp4").read_bytes() == b"video-bytes"
    assert read_json(paths.links_json)["shots"]["2"] == {"file": "manual/shot_02.mp4"}
    assert httpx.post(base + "/api/upload?shot=2", content=b"x", headers={"X-Filename": "a.exe"}).status_code == 400
    assert httpx.post(base + "/api/upload?shot=9", content=b"x", headers={"X-Filename": "a.jpg"}).status_code == 400
    assert httpx.post(base + "/api/upload?shot=1", content=b"x" * 2000, headers={"X-Filename": "a.jpg"}).status_code == 413


def test_files_are_confined_to_run_dir(server):
    _, base = server
    assert httpx.get(base + "/files/plan/seg_01_0.jpg").content == b"jpg"
    assert httpx.get(base + "/files/../secret.txt").status_code == 404
    assert httpx.get(base + "/files/%2E%2E/secret.txt").status_code == 404
    assert httpx.get(base + "/api/state").json()["plan"]["shots"][0]["index"] == 0


def test_cross_site_posts_are_rejected(server):
    paths, base = server
    evil = {"Origin": "https://evil.example"}
    assert httpx.post(base + "/api/links", json={"shots": {}}, headers=evil).status_code == 403
    assert httpx.post(base + "/api/upload?shot=1", content=b"x", headers={**evil, "X-Filename": "a.jpg"}).status_code == 403
    assert not paths.links_json.exists()
    same = {"Origin": base}
    assert httpx.post(base + "/api/links", json={"shots": {}}, headers=same).status_code == 200
