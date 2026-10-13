from PIL import Image
from google.genai import types

from mayzfact.errors import PipelineError
from mayzfact.hook_queries import describe_segments, transcript_near
from mayzfact.models import HookQueries, SegmentQueries

TRANSCRIPT = [
    {"text": "These are the top five", "start": 0.0, "duration": 2.0},
    {"text": "horseshoe crab look", "start": 2.0, "duration": 2.0},
    {"text": "later", "start": 9.0, "duration": 1.0},
]


def infos():
    return [
        {"index": 0, "start_s": 0.0, "end_s": 2.0, "transcript": "These are the top five ancient creatures still alive today wow"},
        {"index": 1, "start_s": 2.0, "end_s": 4.0, "transcript": ""},
    ]


def frames(tmp_path):
    out = []
    for i in range(2):
        path = tmp_path / f"seg_{i + 1:02d}_1.jpg"
        Image.new("RGB", (16, 16), "red").save(path)
        out.append(path)
    return out


class FakeWriter:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def generate(self, system, contents, schema, step="script"):
        self.calls.append((system, contents, schema, step))
        if self.error:
            raise self.error
        return self.result


def test_transcript_near():
    assert transcript_near(TRANSCRIPT, 1.5, 3.0) == "These are the top five horseshoe crab look"
    assert transcript_near(TRANSCRIPT, 4.5, 8.0) == ""


def test_describe_uses_gemini_and_sends_one_image_per_segment(tmp_path):
    result = HookQueries(segments=[
        SegmentQueries(index=0, en=[" crab beach ", "crab hand", "extra"], zh=["鲎"]),
        SegmentQueries(index=1, en=[], zh=["鹦鹉螺", "x", "y"]),
        SegmentQueries(index=7, en=["ignored"], zh=[]),
    ])
    writer = FakeWriter(result)
    out = describe_segments(writer, infos(), frames(tmp_path), log=lambda m: None)
    assert out == {0: {"en": ["crab beach", "crab hand"], "zh": ["鲎"]}, 1: {"en": [], "zh": ["鹦鹉螺", "x"]}}
    system, contents, schema, step = writer.calls[0]
    assert schema is HookQueries and step == "hook"
    assert "ignore those overlays" in system
    assert sum(isinstance(part, types.Part) for part in contents) == 2


def test_describe_falls_back_to_transcript_on_error(tmp_path):
    logs = []
    out = describe_segments(FakeWriter(error=PipelineError("hook", "503")), infos(), frames(tmp_path), log=logs.append)
    assert out[0] == {"en": ["these are the top five ancient creatures still"], "zh": []}
    assert out[1] == {"en": [], "zh": []}
    assert "pakai transcript" in logs[0]


def test_describe_without_writer_uses_fallback(tmp_path):
    assert describe_segments(None, infos(), frames(tmp_path))[0]["zh"] == []


def test_translate_queries_maps_en_to_zh_and_falls_back():
    from mayzfact.hook_queries import translate_queries
    from mayzfact.models import Translation, Translations

    writer = FakeWriter(Translations(items=[Translation(en="horseshoe crab", zh=" 鲎 "), Translation(en="unknown", zh="x")]))
    assert translate_queries(writer, ["horseshoe crab", "fossil"], log=lambda m: None) == {"horseshoe crab": "鲎"}
    assert writer.calls[0][3] == "plan"
    assert translate_queries(FakeWriter(error=PipelineError("plan", "503")), ["a"], log=lambda m: None) == {}
    assert translate_queries(None, ["a"]) == {}
