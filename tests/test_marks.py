import httpx

from mayzfact.emoji import EMOJI, ensure_emoji
from mayzfact.marks import normalize_marks, prepare_marks
from mayzfact.store import RunPaths, write_json_atomic

OLD = {"beats": [{"text": "Check out five ancient beasts!"}, {"text": "Number five, horseshoe crab."},
                 {"text": "Tap like for amazing luck!"}]}
NONE = {"point": False, "emoji": "", "emoji_word": ""}
QUIET = {"log": lambda m: None}



def lottie_client(*available):
    hits = []

    def handler(request):
        hits.append(request.url.path)
        if any(cp in request.url.path for cp in available):
            return httpx.Response(200, json={"v": "5.7.4", "fr": 30, "ip": 0, "op": 30, "w": 512, "h": 512, "layers": []})
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler)), hits


def test_normalize_marks_cleans_emoji_and_countdown():
    raw = [{"point": True, "emoji": "🧐", "emoji_word": "Beasts!"},
           {"point": True, "emoji": "🔥", "emoji_word": "crab"},       # beat countdown: nggak dapat emoji
           {"point": False, "emoji": "🐸", "emoji_word": "luck"}]      # bukan emoji yang diizinin
    assert normalize_marks(OLD["beats"], raw) == [
        {"point": True, "emoji": "🧐", "emoji_word": "beasts"},
        {"point": True, "emoji": "", "emoji_word": ""},
        NONE,
    ]
    # emoji_word yang nggak ada di teks beat → kosong (emoji muncul di awal beat); data kurang → tanpa tanda
    assert normalize_marks(OLD["beats"], [{"point": False, "emoji": "🍀", "emoji_word": "jackpot"}]) == [
        {"point": False, "emoji": "🍀", "emoji_word": ""}, NONE, NONE]






def test_ensure_emoji_stops_after_network_failure(tmp_path):
    hits = []

    def handler(request):
        hits.append(request.url.path)
        raise httpx.ConnectError("offline")

    logs = []
    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert ensure_emoji(tmp_path, client, ["1f9d0", "1f340"], logs.append, sleep=lambda s: None) == {}
    assert set(hits) == {"/s/e/notoemoji/latest/1f9d0/lottie.json"}
    assert len(logs) == 1


def test_ensure_emoji_downloads_once_and_skips_missing(tmp_path):
    client, hits = lottie_client("1f9d0")
    logs = []
    got = ensure_emoji(tmp_path, client, ["1f9d0", "1f340"], logs.append)
    assert list(got) == ["1f9d0"] and got["1f9d0"].name == "1f9d0.json"
    ensure_emoji(tmp_path, client, ["1f9d0"], logs.append)
    assert hits.count("/s/e/notoemoji/latest/1f9d0/lottie.json") == 1
    assert any("1f340" in line for line in logs)


def test_prepare_marks_copies_used_emoji_into_run(tmp_path):
    paths = RunPaths(tmp_path / "run")
    script = {"beats": [{"text": "Look at this shell!", "point": True, "emoji": "👀", "emoji_word": "look"},
                        {"text": "So old.", "point": False, "emoji": "", "emoji_word": ""}]}
    client, _ = lottie_client(EMOJI["👀"])
    out = prepare_marks(paths, script, client=client, emoji_dir=tmp_path / "assets", **QUIET)
    assert out == {"beats": [{"point": True, "emoji": "👀", "emoji_word": "look"}, NONE],
                   "emoji": {"👀": "emoji/1f440.json"}}
    assert (paths.root / "emoji" / "1f440.json").exists()


def test_old_script_without_marks_gets_none(tmp_path):
    paths = RunPaths(tmp_path / "run")
    out = prepare_marks(paths, OLD, client=lottie_client()[0], emoji_dir=tmp_path / "assets", **QUIET)
    assert out == {"beats": [NONE] * 3, "emoji": {}}
    assert not (paths.root / "annotations.json").exists()


def test_old_script_without_mark_keys_reads_annotations(tmp_path):
    paths = RunPaths(tmp_path / "run")
    marks = [{"point": True, "emoji": "", "emoji_word": ""}, NONE, {"point": False, "emoji": "🍀", "emoji_word": "luck"}]
    write_json_atomic(paths.root / "annotations.json", {"key": "whatever", "beats": marks})
    out = prepare_marks(paths, OLD, client=lottie_client(EMOJI["🍀"])[0], emoji_dir=tmp_path / "assets", **QUIET)
    assert out["beats"] == marks and out["emoji"] == {"🍀": "emoji/1f340.json"}
