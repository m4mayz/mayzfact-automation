"""Step source: ambil transcript English dari YouTube Shorts source."""

from __future__ import annotations

import re
from typing import Callable

from youtube_transcript_api import CouldNotRetrieveTranscript, YouTubeTranscriptApi

from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, write_json_atomic

_ID = r"([A-Za-z0-9_-]{11})"
_RAW_ID = re.compile(rf"^{_ID}$")
_URL_PATTERNS = (
    re.compile(rf"youtube\.com/shorts/{_ID}"),
    re.compile(rf"youtu\.be/{_ID}"),
    re.compile(rf"[?&]v={_ID}"),
)


def parse_video_id(value: str) -> str:
    value = value.strip()
    if match := _RAW_ID.match(value):
        return match.group(1)
    for pattern in _URL_PATTERNS:
        if match := pattern.search(value):
            return match.group(1)
    raise PipelineError("source", f"Nggak bisa baca video ID dari {value!r}")


def youtube_transcript(video_id: str) -> list[dict]:
    try:
        return YouTubeTranscriptApi().fetch(video_id, languages=["en"]).to_raw_data()
    except CouldNotRetrieveTranscript as exc:
        raise PipelineError(
            "source", f"Transcript English buat {video_id} nggak bisa diambil ({type(exc).__name__})."
        ) from exc


def build_source(video_id: str, snippets: list[dict]) -> dict:
    if not snippets:
        raise PipelineError("source", f"Transcript {video_id} kosong.")
    transcript = [
        {"text": " ".join(str(s["text"]).split()), "start": float(s["start"]), "duration": float(s["duration"])}
        for s in snippets
    ]
    last = transcript[-1]
    return {
        "video_id": video_id,
        "duration_s": round(last["start"] + last["duration"], 3),
        "transcript": transcript,
    }


def run_source(
    video_id: str, paths: RunPaths, fetch: Callable[[str], list[dict]] = youtube_transcript
) -> dict:
    data = build_source(video_id, fetch(video_id))
    write_json_atomic(paths.source_json, data)
    return data
