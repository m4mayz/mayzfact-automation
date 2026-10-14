import httpx

from mayzfact.emoji import EMOJI, ensure_emoji
from mayzfact.errors import PipelineError
from mayzfact.marks import beat_marks, normalize_marks, prepare_marks
from mayzfact.models import BeatMark, BeatMarks
from mayzfact.store import RunPaths, read_json

OLD = {"beats": [{"text": "Check out five ancient beasts!"}, {"text": "Number five, horseshoe crab."},
                 {"text": "Tap like for amazing luck!"}]}
NONE = {"point": False, "emoji": "", "emoji_word": ""}
QUIET = {"log": lambda m: None}


class FakeWriter:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def generate(self, system, contents, schema, step="script"):
        self.calls.append((system, contents, schema, step))
        if self.error:
            raise self.error
        return self.result


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


def test_new_script_marks_need_no_gemini(tmp_path):
    script = {"beats": [{"text": "Look at this shell!", "point": True, "emoji": "👀", "emoji_word": "look"}]}
    writer = FakeWriter()
    assert beat_marks(RunPaths(tmp_path), script, writer, **QUIET) == [{"point": True, "emoji": "👀", "emoji_word": "look"}]
    assert writer.calls == []


def test_old_script_marks_come_from_gemini_and_are_cached(tmp_path):
    paths = RunPaths(tmp_path)
    writer = FakeWriter(BeatMarks(items=[BeatMark(index=0, point=True, emoji="🧐", emoji_word="beasts"),
                                         BeatMark(index=2, point=False, emoji="🍀", emoji_word="luck!")]))
    marks = beat_marks(paths, OLD, writer, **QUIET)
    assert marks == [{"point": True, "emoji": "🧐", "emoji_word": "beasts"}, NONE,
                     {"point": False, "emoji": "🍀", "emoji_word": "luck"}]
    assert writer.calls[0][3] == "timeline" and "🧐" in writer.calls[0][0] and "horseshoe crab" in writer.calls[0][1]
    assert read_json(paths.root / "annotations.json")["beats"] == marks
    assert beat_marks(paths, OLD, FakeWriter(error=PipelineError("timeline", "boom")), **QUIET) == marks  # cache


def test_old_script_without_working_gemini_has_no_marks(tmp_path):
    paths = RunPaths(tmp_path)
    logs = []
    assert beat_marks(paths, OLD, None, log=logs.append) == [NONE] * 3
    assert beat_marks(paths, OLD, FakeWriter(error=PipelineError("timeline", "503")), log=logs.append) == [NONE] * 3
    assert len(logs) == 2 and not (paths.root / "annotations.json").exists()  # gagal nggak di-cache, run berikutnya coba lagi


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
    out = prepare_marks(paths, script, writer=None, client=client, emoji_dir=tmp_path / "assets", **QUIET)
    assert out == {"beats": [{"point": True, "emoji": "👀", "emoji_word": "look"}, NONE],
                   "emoji": {"👀": "emoji/1f440.json"}}
    assert (paths.root / "emoji" / "1f440.json").exists()
