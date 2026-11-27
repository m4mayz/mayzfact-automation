import re
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
    assert 'data-preview="0"' in html and 'data-preview="1"' in html and preview_disabled(html, 1)  # belum ada link: tombolnya disabled
    assert "<video" not in html  # video preview baru dibikin pas dibuka


def preview_disabled(html, idx):
    return bool(re.search(rf'data-preview-btn="{idx}"[^>]*\bdisabled\b', html))


def test_preview_box_always_rendered_and_enabled_when_ready(brief):
    paths, base, pf = brief
    (paths.root / "manual").mkdir()
    (paths.root / "manual" / "shot_3.jpg").write_bytes(b"jpg")
    write_json_atomic(paths.links_json, {"shots": {"0": {"url": "https://a.b/v"}, "2": {"file": "manual/shot_3.jpg"}}})
    html = httpx.get(base + "/").text
    assert all(f'data-preview="{i}"' in html for i in range(3))
    assert preview_disabled(html, 0) and preview_disabled(html, 1) and not preview_disabled(html, 2)
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "2": "file:manual/shot_3.jpg"}})
    assert wait_until(lambda: pf.snapshot().get("https://a.b/v", {}).get("state") == "siap")
    assert not preview_disabled(httpx.get(base + "/").text, 0)


def test_closing_preview_while_loading_never_builds_media(brief):
    _, base, _ = brief
    html = httpx.get(base + "/").text
    # preview ditutup pas Range request masih jalan: jangan bikin video/foto yang muter diam-diam
    assert "btn.getAttribute('aria-expanded') !== 'true'" in html


def test_speed_select_shows_saved_speed_and_is_off_for_photos(brief):
    paths, base, _ = brief
    write_json_atomic(paths.links_json, {"shots": {"0": {"url": "https://a.b/v", "speed": 1.5},
                                                   "2": {"file": "manual/shot_3.jpg", "speed": 2.0}}})
    html = httpx.get(base + "/").text
    assert re.search(r'<select data-speed="0"[^>]*>.*?value="1.5" selected', html, re.S)
    assert re.search(r'<select data-speed="1"[^>]*>.*?value="1" selected', html, re.S)
    assert re.search(r'<select data-speed="2"[^>]*\bdisabled\b', html)
    for name in ("syncPreviewButtons", "playbackRate", "collectSpeed"):
        assert name in html


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


def test_saving_speed(brief):
    paths, base, _ = brief
    ok = httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "1": "https://a.b/w"},
                                               "speed": {"0": 1.25, "1": 1}})
    assert ok.status_code == 200
    shots = read_json(paths.links_json)["shots"]
    assert shots["0"]["speed"] == 1.25 and "speed" not in shots["1"]
    bad = httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "speed": {"0": 3}})
    assert bad.status_code == 400 and "speed" in bad.json()["error"]


def test_save_without_speed_key_keeps_saved_speed(brief):
    paths, base, _ = brief
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "speed": {"0": 2}})
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}})
    assert read_json(paths.links_json)["shots"]["0"]["speed"] == 2


def test_upload_keeps_speed(brief):
    paths, base, _ = brief
    httpx.post(base + "/api/links", json={"shots": {"1": "https://a.b/v"}, "speed": {"1": 0.5}})
    httpx.post(base + "/api/upload?shot=1", content=b"mp4", headers={"X-Filename": "a.mp4"})
    assert read_json(paths.links_json)["shots"]["1"] == {"file": "manual/shot_2.mp4", "speed": 0.5}


def test_save_without_sfx_key_keeps_saved_sfx(brief):
    """Upload di brief nyimpen {shots} dulu tanpa sfx: SFX yang udah kesimpen jangan ikut kehapus."""
    paths, base, _ = brief
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "2": "https://a.b/w"},
                                          "sfx": {"0": {"file": "uy.mp3", "at_s": 0.8}}})
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "2": "https://a.b/w"}})
    assert read_json(paths.links_json)["shots"]["0"]["sfx"] == {"file": "uy.mp3", "at_s": 0.8}
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "sfx": {"0": None}})  # pilih "Tanpa"
    assert "sfx" not in read_json(paths.links_json)["shots"]["0"]


def test_saving_audio_volume(brief):
    paths, base, _ = brief
    ok = httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "1": "https://a.b/w"},
                                               "audio": {"0": 150, "1": None}})
    assert ok.status_code == 200
    shots = read_json(paths.links_json)["shots"]
    assert shots["0"]["volume"] == 1.5 and "volume" not in shots["1"]
    bad = httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "audio": {"0": 250}})
    assert bad.status_code == 400 and "volume" in bad.json()["error"]


def test_save_without_audio_key_keeps_volume(brief):
    paths, base, _ = brief
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "audio": {"0": 80}})
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}})
    assert read_json(paths.links_json)["shots"]["0"]["volume"] == 0.8


def test_upload_keeps_volume(brief):
    paths, base, _ = brief
    httpx.post(base + "/api/links", json={"shots": {"1": "https://a.b/v"}, "audio": {"1": 200}})
    httpx.post(base + "/api/upload?shot=1", content=b"mp4", headers={"X-Filename": "a.mp4"})
    assert read_json(paths.links_json)["shots"]["1"] == {"file": "manual/shot_2.mp4", "volume": 2.0}


def test_saving_transition_sfx(brief):
    paths, base, _ = brief
    assert httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "transition_sfx": "click"}).status_code == 200
    assert read_json(paths.links_json)["transition_sfx"] == "click"
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "transition_sfx": "click_random"})
    assert "transition_sfx" not in read_json(paths.links_json)  # default nggak ditulis
    bad = httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "transition_sfx": "bogus"})
    assert bad.status_code == 400 and "SFX transisi" in bad.json()["error"]


def test_save_without_transition_key_keeps_it(brief):
    paths, base, _ = brief
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}, "transition_sfx": "none"})
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v"}})
    assert read_json(paths.links_json)["transition_sfx"] == "none"


def test_audio_controls_render_and_photo_disabled(brief):
    paths, base, _ = brief
    write_json_atomic(paths.links_json, {"shots": {"0": {"url": "https://a.b/v", "volume": 1.5},
                                                   "2": {"file": "manual/shot_3.jpg"}}})
    html = httpx.get(base + "/").text
    assert re.search(r'<input type="checkbox" data-mute="0"(?![^>]*checked)[^>]*>', html)
    assert re.search(r'data-volume="0"[^>]*value="150"', html)
    assert re.search(r'<input type="checkbox" data-mute="1"[^>]*\bchecked\b', html)
    assert re.search(r'<input type="checkbox" data-mute="2"[^>]*\bdisabled\b', html)
    for name in ("collectAudio", "collectTransition", "/api/bgm-volume"):
        assert name in html


def test_transition_radio_shows_saved_choice(brief):
    paths, base, _ = brief
    html = httpx.get(base + "/").text
    assert re.search(r'name="transition-sfx" value="click_random"[^>]*\bchecked\b', html)
    write_json_atomic(paths.links_json, {"shots": {}, "transition_sfx": "click"})
    html = httpx.get(base + "/").text
    assert re.search(r'name="transition-sfx" value="click"[^>]*\bchecked\b', html)
    assert not re.search(r'name="transition-sfx" value="click_random"[^>]*\bchecked\b', html)


def test_bgm_volume_endpoint_top3(brief):
    _, base, _ = brief
    assert httpx.get(base + "/api/bgm-volume").json() == {"percent": 12.0}


def test_faktacuil_bgm_preview_volume_uses_default_song(tmp_path):
    from mayzfact.audio import FAKTACUIL_BGM_REFERENCE, faktacuil_bgm_preview_volume
    paths = RunPaths(tmp_path / "abc")
    paths.root.mkdir(parents=True)
    songs = tmp_path / "fc"
    songs.mkdir()
    (songs / FAKTACUIL_BGM_REFERENCE).write_bytes(b"x")  # lagu = referensi: volume dasar tanpa analisis loudness
    assert faktacuil_bgm_preview_volume(paths, bgm_dir=tmp_path / "none", faktacuil_bgm_dir=songs) == 0.06
    assert faktacuil_bgm_preview_volume(paths, bgm_dir=tmp_path / "none", faktacuil_bgm_dir=tmp_path / "kosong") == 0.0


def test_zero_volume_stays_unmuted_and_unsent_shot_is_muted(brief):
    paths, base, _ = brief
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "1": "https://a.b/w"},
                                          "audio": {"0": 150, "1": 150}})
    httpx.post(base + "/api/links", json={"shots": {"0": "https://a.b/v", "1": "https://a.b/w"}, "audio": {"0": 0}})
    shots = read_json(paths.links_json)["shots"]
    assert shots["0"]["volume"] == 0.0  # 0% tetap di-unmute (hening), bukan dibuang
    assert "volume" not in shots["1"]  # body bawa key audio tapi shot ini nggak ada (foto/disabled): volume lama hilang
