"""Step source: transcript English dari YouTube Shorts source, plus video + frame hook buat bahan naskah."""

from __future__ import annotations

import re
from pathlib import Path
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
    video_id: str, paths: RunPaths, fetch: Callable[[str], list[dict]] = youtube_transcript, *,
    download_source: Callable[[str, Path], Path] | None = None, hook_seconds: float = 0.0,
    log: Callable[[str], None] = print,
) -> dict:
    data = build_source(video_id, fetch(video_id))
    data["hook_segments"] = []
    if download_source is not None and hook_seconds > 0:
        from mayzfact.steps.hook import prepare_source_segments

        # Frame hook dibikin di sini biar udah ada pas agent nulis naskah (keyword hook butuh lihat frame-nya).
        try:
            segs = prepare_source_segments(paths, data, download_source, hook_seconds, paths.plan_dir, retry_step="source")
            data["hook_segments"] = [{"index": s["index"], "start_s": s["start_s"], "end_s": s["end_s"],
                                      "frames": [f.relative_to(paths.root).as_posix() for f in s["frames"]]} for s in segs]
        except PipelineError as exc:  # video gagal di-download: naskah tetap bisa ditulis, frame nyusul di --from plan
            log(f"[source] video/frame hook dilewat: {exc.message.splitlines()[0]}")
    write_json_atomic(paths.source_json, data)
    return data
