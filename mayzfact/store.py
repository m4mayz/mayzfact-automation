"""Lokasi file hasil tiap step + tulis file secara atomic."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunPaths:
    root: Path

    @property
    def source_json(self) -> Path:
        return self.root / "source.json"

    @property
    def script_json(self) -> Path:
        return self.root / "script.json"

    @property
    def voice_mp3(self) -> Path:
        return self.root / "voice.mp3"

    @property
    def tts_json(self) -> Path:
        return self.root / "tts.json"

    @property
    def clips_dir(self) -> Path:
        return self.root / "clips"

    @property
    def clips_json(self) -> Path:
        return self.root / "clips.json"

    @property
    def timeline_json(self) -> Path:
        return self.root / "timeline.json"

    @property
    def final_mp4(self) -> Path:
        return self.root / "final.mp4"

    @property
    def source_mp4(self) -> Path:
        return self.root / "source.mp4"

    @property
    def hook_dir(self) -> Path:
        return self.root / "hook"

    @property
    def hook_json(self) -> Path:
        return self.root / "hook.json"

    @property
    def shots_plan_json(self) -> Path:
        return self.root / "shots_plan.json"

    @property
    def plan_dir(self) -> Path:
        return self.root / "plan"

    @property
    def links_json(self) -> Path:
        return self.root / "links.json"

    @property
    def links_status_json(self) -> Path:
        return self.root / "links_status.json"

    @property
    def manual_dir(self) -> Path:
        return self.root / "manual"

    @property
    def fetch_progress_json(self) -> Path:
        return self.root / "fetch_progress.json"


def tmp_path_for(path: Path) -> Path:
    """File sementara di folder yang sama. Ekstensinya tetap karena ffmpeg butuh ekstensi."""
    return path.with_name(f"{path.stem}.tmp{path.suffix}")


def write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_path_for(path)
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_json_atomic(path: Path, data: Any) -> None:
    write_bytes_atomic(path, json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
