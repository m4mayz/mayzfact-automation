import json

import httpx

from mayzfact.audio import (
    SFX_DEFAULTS,
    ensure_sfx,
    list_bgm,
    load_sfx_map,
    prepare_audio,
)
from mayzfact.store import RunPaths, read_json, write_json_atomic

SCRIPT = {"beats": [{"text": "Five ancient creatures still alive."}, {"text": "Number five, horseshoe crab."}]}


def serving(files):
    hits = []

    def handler(request):
        hits.append(request.url.path)
        name = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, content=files[name]) if name in files else httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler)), hits


def test_sfx_map_defaults_written_once(tmp_path):
    assert load_sfx_map(tmp_path) == SFX_DEFAULTS
    (tmp_path / "sfx.json").write_text(json.dumps({"hook": "x.mp3"}), encoding="utf-8")
    assert load_sfx_map(tmp_path) == {"hook": "x.mp3"}


def test_ensure_sfx_downloads_missing_and_skips_failures(tmp_path):
    (tmp_path / "vine-boom.mp3").write_bytes(b"old")
    client, hits = serving({"fast-whoosh.mp3": b"whoosh"})
    logs = []
    got = ensure_sfx(tmp_path, client, {"number": "vine-boom.mp3", "cut": "fast-whoosh.mp3", "hook": "nope.mp3"}, logs.append)
    assert got == {"number": tmp_path / "vine-boom.mp3", "cut": tmp_path / "fast-whoosh.mp3"}
    assert hits == ["/media/sounds/fast-whoosh.mp3", "/media/sounds/nope.mp3"]
    assert any("hook" in line for line in logs)


def test_list_bgm(tmp_path):
    assert list_bgm(tmp_path / "missing") == []
    for name in ("mystery.mp3", "epic.wav", "notes.txt"):
        (tmp_path / name).write_bytes(b"x")
    assert list_bgm(tmp_path) == ["epic.wav", "mystery.mp3"]




def test_ensure_sfx_stops_after_network_failure(tmp_path):
    hits = []

    def handler(request):
        hits.append(request.url.path)
        raise httpx.ConnectError("offline")

    logs = []
    client = httpx.Client(transport=httpx.MockTransport(handler))
    got = ensure_sfx(tmp_path, client, {"hook": "a.mp3", "number": "b.mp3", "cut": "c.mp3"}, logs.append, sleep=lambda s: None)
    assert got == {}
    assert set(hits) == {"/media/sounds/a.mp3"}
    assert any("dilewat" in line for line in logs)


def test_ensure_sfx_skips_bad_names(tmp_path):
    client, hits = serving({"ok.mp3": b"x"})
    logs = []
    got = ensure_sfx(tmp_path / "sfx", client, {"cut": None, "hook": "", "number": "../x.mp3", "subject": "ok.mp3"}, logs.append)
    assert list(got) == ["subject"] and hits == ["/media/sounds/ok.mp3"]
    assert len(logs) == 3


def test_broken_json_files_do_not_crash(tmp_path):
    bgm_dir, sfx_dir = tmp_path / "bgm", tmp_path / "sfx"
    bgm_dir.mkdir()
    sfx_dir.mkdir()
    (bgm_dir / "mystery.mp3").write_bytes(b"m")
    (sfx_dir / "sfx.json").write_text("{rusak", encoding="utf-8")
    paths = RunPaths(tmp_path / "run")
    paths.root.mkdir()
    (paths.root / "audio.json").write_text('{"bgm": "mystery.mp3",}', encoding="utf-8")  # sisa lama yang rusak: ketimpa
    client, _ = serving({name: b"s" for name in SFX_DEFAULTS.values()})
    logs = []
    audio = prepare_audio(paths, {**SCRIPT, "bgm": "mystery.mp3"}, bgm_dir=bgm_dir, sfx_dir=sfx_dir, client=client, log=logs.append)
    assert audio["bgm"] == "audio/bgm/mystery.mp3" and set(audio["sfx"]) == set(SFX_DEFAULTS)
    assert read_json(paths.root / "audio.json") == {"bgm": "mystery.mp3"}
    assert any("sfx.json" in line for line in logs)


def test_bgm_comes_from_script(tmp_path):
    bgm_dir, sfx_dir = tmp_path / "bgm", tmp_path / "sfx"
    bgm_dir.mkdir()
    (bgm_dir / "mystery.mp3").write_bytes(b"m")
    client, _ = serving({name: b"sfx" for name in SFX_DEFAULTS.values()})
    paths = RunPaths(tmp_path / "run")
    logs = []
    out = prepare_audio(paths, {"beats": [], "bgm": "mystery.mp3"}, bgm_dir=bgm_dir, sfx_dir=sfx_dir, client=client, log=logs.append)
    assert out["bgm"] == "audio/bgm/mystery.mp3" and out["sfx"]["number"] == "audio/sfx/vine-boom.mp3"
    assert (paths.root / "audio/bgm/mystery.mp3").read_bytes() == b"m"
    assert read_json(paths.root / "audio.json") == {"bgm": "mystery.mp3"}
    out = prepare_audio(paths, {"beats": [], "bgm": "epic.mp3"}, bgm_dir=bgm_dir, sfx_dir=sfx_dir, client=client, log=logs.append)
    assert out["bgm"] is None and any("epic.mp3" in m for m in logs)
    out = prepare_audio(paths, {"beats": []}, bgm_dir=bgm_dir, sfx_dir=sfx_dir, client=client, log=logs.append)
    assert out["bgm"] is None  # naskah lama tanpa field bgm: tanpa BGM, nggak error


def test_old_script_without_bgm_keeps_previous_choice(tmp_path):
    bgm_dir, sfx_dir = tmp_path / "bgm", tmp_path / "sfx"
    bgm_dir.mkdir()
    (bgm_dir / "mystery.mp3").write_bytes(b"m")
    client, _ = serving({name: b"sfx" for name in SFX_DEFAULTS.values()})
    paths = RunPaths(tmp_path / "run")
    write_json_atomic(paths.root / "audio.json", {"bgm": "mystery.mp3"})  # pilihan lama dari run sebelum naskah bawa bgm
    out = prepare_audio(paths, {"beats": []}, bgm_dir=bgm_dir, sfx_dir=sfx_dir, client=client, log=lambda m: None)
    assert out["bgm"] == "audio/bgm/mystery.mp3"
    assert read_json(paths.root / "audio.json") == {"bgm": "mystery.mp3"}
