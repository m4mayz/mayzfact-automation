import threading
from pathlib import Path

import httpx
import pytest

from mayzfact.brief.prefetch import Prefetcher
from mayzfact.brief.server import make_server
from mayzfact.store import RunPaths, read_json, write_json_atomic
from tests.test_brief_prefetch import wait_until
from tests.test_brief_server import PLAN


@pytest.fixture
def brief(tmp_path):
    paths = RunPaths(tmp_path / "abc")
    (paths.root / "plan").mkdir(parents=True)
    write_json_atomic(paths.shots_plan_json, PLAN)
    sfx_dir, media_dir = tmp_path / "sfx", tmp_path / "cache"
    sfx_dir.mkdir()
    media_dir.mkdir()
    (sfx_dir / "uy.mp3").write_bytes(b"uy")
    (sfx_dir / "check-mark_oPG7Xo5.mp3").write_bytes(b"ck")
    (sfx_dir / "sfx.json").write_text("{}", encoding="utf-8")
    (media_dir / "k_0.mp4").write_bytes(b"video")
    (tmp_path / "secret.mp3").write_bytes(b"rahasia")
    pf = Prefetcher(paths, lambda entry, root: [media_dir / "k_0.mp4"], log=lambda m: None)
    pf.start()
    srv = make_server(paths, 0, prefetcher=pf, sfx_dir=sfx_dir, media_dir=media_dir)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield paths, f"http://127.0.0.1:{srv.server_address[1]}", pf
    srv.shutdown()
    srv.server_close()
    pf.stop()


def test_page_shows_sfx_pills_and_preview(brief):
    paths, base, _ = brief
    write_json_atomic(paths.links_json, {"shots": {"0": {"url": "https://a.b/v", "sfx": {"file": "uy.mp3", "at_s": 0.8}}}})
    html = httpx.get(base + "/").text
    assert 'name="sfx-0" value="uy.mp3" checked' in html and 'data-sfx-at="0" value="0.8"' in html
    assert 'name="sfx-1" value="" checked' in html  # shot tanpa SFX: pill "Tanpa"
    assert ">check mark<" in html  # label tanpa id acak myinstants
    assert 'data-preview="0"' in html and 'data-preview="1"' not in html  # shot tanpa link: belum ada yang di-preview
    assert "<video" not in html  # video preview baru dibikin pas dibuka


def test_sfx_files_are_served_from_library_only(brief):
    _, base, _ = brief
    assert httpx.get(base + "/sfx/uy.mp3").content == b"uy"
    assert httpx.get(base + "/sfx/sfx.json").status_code == 404
    assert httpx.get(base + "/sfx/..%2Fsecret.mp3").status_code == 404
    assert httpx.get(base + "/sfx/%2E%2E/secret.mp3").status_code == 404


def test_saving_sfx_and_preview_starts(brief):
    paths, base, _ = brief
    write_json_atomic(paths.clips_json, {"shots": [{"index": 0, "start_s": 0.0, "end_s": 2.0, "page_url": "https://a.b/v",
                                                    "source_s": 3.5}]})
    ok = httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "2": "https://a.b/w @1.5"},
                                               "sfx": {"0": {"file": "uy.mp3", "at_s": 1.2}, "1": None}})
    assert ok.status_code == 200
    assert read_json(paths.links_json)["shots"]["0"] == {"url": "https://a.b/v", "sfx": {"file": "uy.mp3", "at_s": 1.2}}
    assert ok.json()["previews"] == {"0": 0.0, "2": 1.5}  # Mulai kosong = detik 0, clips.json lama nggak dipakai
    bad = httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "sfx": {"0": {"file": "nope.mp3", "at_s": 0}}})
    assert bad.status_code == 400 and "nope.mp3" in bad.json()["error"]
    late = httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "sfx": {"0": {"file": "uy.mp3", "at_s": 9}}})
    assert late.status_code == 400


def test_upload_keeps_sfx(brief):
    paths, base, _ = brief
    httpx.post(base + "/api/links", json={"shots": {"1": "https://a.b/v"}, "sfx": {"1": {"file": "uy.mp3", "at_s": 0.5}}})
    httpx.post(base + "/api/upload?shot=1", content=b"jpg", headers={"X-Filename": "a.jpg"})
    assert read_json(paths.links_json)["shots"]["1"] == {"file": "manual/shot_2.jpg", "sfx": {"file": "uy.mp3", "at_s": 0.5}}


def test_media_serves_downloaded_or_uploaded_file(brief):
    paths, base, pf = brief
    assert httpx.get(base + "/media/0").status_code == 404  # belum ada link
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}})
    assert wait_until(lambda: pf.snapshot().get("https://a.b/v", {}).get("state") == "siap")
    got = httpx.get(base + "/media/0")
    assert got.content == b"video" and got.headers["content-type"] == "video/mp4"
    (paths.root / "manual").mkdir()
    (paths.root / "manual" / "shot_3.jpg").write_bytes(b"jpg")
    httpx.post(base + "/api/links", json={"shots": {"2": "file:manual/shot_3.jpg"}})
    assert httpx.get(base + "/media/2").content == b"jpg"
    assert httpx.get(base + "/media/x").status_code == 404


def test_media_refuses_files_outside_cache(brief, tmp_path):
    paths, base, pf = brief
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}})
    assert wait_until(lambda: pf.snapshot().get("https://a.b/v", {}).get("state") == "siap")
    write_json_atomic(paths.prefetch_json, {"https://a.b/v": {"state": "siap", "files": ["../secret.mp3"]}})
    pf._state["https://a.b/v"]["files"] = ["../secret.mp3"]  # prefetch.json dirusak
    assert httpx.get(base + "/media/0").status_code == 404
    assert Path(tmp_path / "secret.mp3").exists()


def test_sfx_label_drops_myinstants_noise():
    from mayzfact.brief.page import sfx_label
    assert sfx_label("punch-gaming-sound-effect-hd_RzlG1GE.mp3") == "punch gaming"
    assert sfx_label("check-mark_oPG7Xo5.mp3") == "check mark"
    assert sfx_label("sound-effect.mp3") == "sound effect"  # isinya cuma kata pengisi: biarin


def test_save_without_sfx_key_keeps_saved_sfx(brief):
    """Upload di brief nyimpen {shots} dulu tanpa sfx: SFX yang udah kesimpen jangan ikut kehapus."""
    paths, base, _ = brief
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "2": "https://a.b/w"},
                                          "sfx": {"0": {"file": "uy.mp3", "at_s": 0.8}}})
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "2": "https://a.b/w"}})
    assert read_json(paths.links_json)["shots"]["0"]["sfx"] == {"file": "uy.mp3", "at_s": 0.8}
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "sfx": {"0": None}})  # pilih "Tanpa"
    assert "sfx" not in read_json(paths.links_json)["shots"]["0"]
