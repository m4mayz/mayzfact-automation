import shutil

import pytest
from youtube_transcript_api import TranscriptsDisabled

from mayzfact.errors import PipelineError
from mayzfact.steps.source import (
    build_source,
    parse_video_id,
    run_source,
    youtube_transcript,
)
from mayzfact.store import RunPaths, read_json

SNIPPETS = [
    {"text": "Hello and welcome", "start": 0.0, "duration": 2.5},
    {"text": "to this\nvideo", "start": 2.5, "duration": 1.8},
]


@pytest.mark.parametrize(
    "value",
    [
        "i2xag_1OJfM",
        "  i2xag_1OJfM  ",
        "https://www.youtube.com/shorts/i2xag_1OJfM",
        "https://youtube.com/shorts/i2xag_1OJfM?feature=share",
        "https://youtu.be/i2xag_1OJfM",
        "https://www.youtube.com/watch?v=i2xag_1OJfM&t=3s",
    ],
)
def test_parse_video_id(value):
    assert parse_video_id(value) == "i2xag_1OJfM"


def test_parse_video_id_rejects_garbage():
    with pytest.raises(PipelineError, match="video ID"):
        parse_video_id("https://example.com/video")


def test_build_source_computes_duration_and_cleans_text():
    data = build_source("i2xag_1OJfM", SNIPPETS)
    assert data["video_id"] == "i2xag_1OJfM"
    assert data["duration_s"] == 4.3
    assert data["transcript"][1] == {"text": "to this video", "start": 2.5, "duration": 1.8}


def test_build_source_rejects_empty_transcript():
    with pytest.raises(PipelineError, match="kosong"):
        build_source("i2xag_1OJfM", [])


def test_run_source_writes_json(tmp_path):
    paths = RunPaths(tmp_path)
    run_source("i2xag_1OJfM", paths, fetch=lambda video_id: SNIPPETS)
    assert read_json(paths.source_json)["duration_s"] == 4.3


def test_missing_transcript_becomes_pipeline_error(monkeypatch):
    class FakeApi:
        def fetch(self, video_id, languages):
            raise TranscriptsDisabled(video_id)

    monkeypatch.setattr("mayzfact.steps.source.YouTubeTranscriptApi", FakeApi)
    with pytest.raises(PipelineError, match="Transcript English"):
        youtube_transcript("i2xag_1OJfM")


def test_source_downloads_video_and_hook_frames(tmp_path, cut_video):
    paths = RunPaths(tmp_path / "abc")
    transcript = [{"text": "five birds with superpowers", "start": 0.0, "duration": 2.0}]
    data = run_source("abc", paths, fetch=lambda vid: transcript,
                      download_source=lambda vid, dest: shutil.copyfile(cut_video, dest) or dest, hook_seconds=1.5,
                      log=lambda m: None)
    assert paths.source_mp4.exists()
    assert data["hook_segments"] and (paths.root / data["hook_segments"][0]["frames"][0]).exists()
    assert read_json(paths.source_json)["hook_segments"] == data["hook_segments"]


def test_source_keeps_json_when_download_fails(tmp_path):
    paths = RunPaths(tmp_path / "abc")
    transcript = [{"text": "x", "start": 0.0, "duration": 1.0}]

    def offline(vid, dest):
        raise PipelineError("source", "offline")

    logs = []
    data = run_source("abc", paths, fetch=lambda vid: transcript, download_source=offline, hook_seconds=1.5, log=logs.append)
    assert paths.source_json.exists() and data["hook_segments"] == []
    assert any("offline" in m for m in logs)
