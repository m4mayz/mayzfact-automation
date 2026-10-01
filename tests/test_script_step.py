import pytest

from mayzfact.errors import PipelineError
from mayzfact.steps.script import generate_script, run_script
from mayzfact.store import RunPaths, read_json
from tests.factories import make_script

SOURCE = {
    "video_id": "i2xag_1OJfM",
    "duration_s": 70.8,
    "transcript": [{"text": "These are the top five ancient creatures that still exist today.", "start": 0.0, "duration": 3.0}],
}
PARAMS = {"ratio": 0.6, "minimum_s": 32, "photo_ratio": 0.3}


class FakeWriter:
    def __init__(self, scripts):
        self.scripts = list(scripts)
        self.prompts = []

    def write(self, system, user):
        self.prompts.append((system, user))
        return self.scripts.pop(0)


def test_generate_script_passes_on_first_try():
    writer = FakeWriter([make_script()])
    data = generate_script(SOURCE, writer, **PARAMS)
    assert (data["target_seconds"], data["target_words"], data["word_count"]) == (42.48, 110, 110)
    assert data["ngram_overlap"] == 0.0
    assert data["fallback_query"] == "ocean animals"
    assert data["beats"][0] == {"text": make_script().beats[0].text, "media": "video", "queries": ["query 0", "animal close up"]}
    assert len(writer.prompts) == 1
    assert "Split the narration into beats" in writer.prompts[0][0]


def test_generate_script_retries_once_with_feedback():
    writer = FakeWriter([make_script(words_per_beat=4), make_script()])
    data = generate_script(SOURCE, writer, **PARAMS)
    assert data["word_count"] == 110
    assert len(writer.prompts) == 2
    assert "Your previous answer was rejected:" in writer.prompts[1][1]
    assert "words" in writer.prompts[1][1]


def test_generate_script_gives_up_after_second_failure():
    writer = FakeWriter([make_script(words_per_beat=4), make_script(words_per_beat=4)])
    with pytest.raises(PipelineError, match="gagal dicek"):
        generate_script(SOURCE, writer, **PARAMS)


def test_run_script_writes_json(tmp_path):
    paths = RunPaths(tmp_path)
    data = run_script(paths, SOURCE, FakeWriter([make_script()]), **PARAMS)
    assert read_json(paths.script_json) == data
