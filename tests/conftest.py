"""Fixture media kecil buatan ffmpeg (sekali per sesi test)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("media")


@pytest.fixture(scope="session")
def sine_mp3(media_dir) -> Path:
    path = media_dir / "sine_3s.mp3"
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-c:a", "libmp3lame", "-b:a", "128k", str(path))
    return path


@pytest.fixture(scope="session")
def long_mp3(media_dir) -> Path:
    path = media_dir / "silence_31s.mp3"
    _ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "31", "-c:a", "libmp3lame", "-b:a", "64k", str(path))
    return path


@pytest.fixture(scope="session")
def make_video(media_dir):
    def _make(width: int, height: int, seconds: float = 2.0, name: str | None = None) -> Path:
        path = media_dir / (name or f"video_{width}x{height}_{seconds}.mp4")
        if not path.exists():
            _ffmpeg(
                "-f", "lavfi", "-i", f"testsrc2=size={width}x{height}:rate=30:duration={seconds}",
                "-f", "lavfi", "-i", f"sine=duration={seconds}",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(path),
            )
        return path

    return _make


@pytest.fixture(scope="session")
def make_photo(media_dir):
    def _make(width: int, height: int, name: str | None = None) -> Path:
        path = media_dir / (name or f"photo_{width}x{height}.jpg")
        if not path.exists():
            _ffmpeg("-f", "lavfi", "-i", f"testsrc2=size={width}x{height}:rate=1:duration=1", "-frames:v", "1", "-q:v", "3", str(path))
        return path

    return _make
