import json

import httpx

from mayzfact.audio import (
    SFX_DEFAULTS,
    ensure_sfx,
    list_bgm,
    load_sfx_map,
    pick_bgm,
    prepare_audio,
)
from mayzfact.errors import PipelineError
from mayzfact.models import BgmChoice
from mayzfact.store import RunPaths, read_json, write_json_atomic

SCRIPT = {"beats": [{"text": "Five ancient creatures still alive."}, {"text": "Number five, horseshoe crab."}]}


class FakeWriter:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def generate(self, system, contents, schema, step="script"):
        self.calls.append((contents, schema, step))
        if self.error:
            raise self.error
        return self.result


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


def test_pick_bgm():
    logs = []
    assert pick_bgm([], SCRIPT, FakeWriter(), logs.append) is None
    single = FakeWriter()
    assert pick_bgm(["mystery.mp3"], SCRIPT, single, logs.append) == "mystery.mp3" and single.calls == []
    writer = FakeWriter(BgmChoice(file="epic.mp3"))
    assert pick_bgm(["epic.mp3", "mystery.mp3"], SCRIPT, writer, logs.append) == "epic.mp3"
    assert "horseshoe crab" in writer.calls[0][0] and writer.calls[0][2] == "timeline"
    assert pick_bgm(["epic.mp3", "mystery.mp3"], SCRIPT, FakeWriter(BgmChoice(file="jazz.mp3")), logs.append) is None
    assert pick_bgm(["epic.mp3", "mystery.mp3"], SCRIPT, FakeWriter(error=PipelineError("x", "503")), logs.append) is None
    assert pick_bgm(["epic.mp3", "mystery.mp3"], SCRIPT, None, logs.append) is None


def test_prepare_audio_copies_and_reuses_choice(tmp_path):
    bgm_dir, sfx_dir = tmp_path / "bgm", tmp_path / "sfx"
    bgm_dir.mkdir()
    for name in ("epic.mp3", "mystery.mp3"):
        (bgm_dir / name).write_bytes(name.encode())
    client, _ = serving({name: b"sfx" for name in SFX_DEFAULTS.values()})
    paths = RunPaths(tmp_path / "run")
    writer = FakeWriter(BgmChoice(file="mystery.mp3"))
    audio = prepare_audio(paths, SCRIPT, bgm_dir=bgm_dir, sfx_dir=sfx_dir, client=client, writer=writer, log=lambda m: None)
    assert audio["bgm"] == "audio/bgm/mystery.mp3"
    assert audio["sfx"]["number"] == "audio/sfx/vine-boom.mp3"
    assert (paths.root / "audio/bgm/mystery.mp3").read_bytes() == b"mystery.mp3"
    assert read_json(paths.root / "audio.json") == {"bgm": "mystery.mp3"}

    write_json_atomic(paths.root / "audio.json", {"bgm": "epic.mp3"})
    again = prepare_audio(paths, SCRIPT, bgm_dir=bgm_dir, sfx_dir=sfx_dir, client=client, writer=None, log=lambda m: None)
    assert again["bgm"] == "audio/bgm/epic.mp3" and len(writer.calls) == 1

    write_json_atomic(paths.root / "audio.json", {"bgm": "deleted.mp3"})
    repick = prepare_audio(paths, SCRIPT, bgm_dir=bgm_dir, sfx_dir=sfx_dir, client=client, writer=writer, log=lambda m: None)
    assert repick["bgm"] == "audio/bgm/mystery.mp3"
