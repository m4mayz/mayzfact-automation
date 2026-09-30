# Fase 1 Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bikin CLI `uv run mayzfact run <video>` yang ngubah 1 YouTube Shorts source jadi `runs/<id>/final.mp4`: naskah ditulis ulang pakai Gemini, suaranya dari ElevenLabs, visualnya klip video + foto dari Pexels/Pixabay, lalu di-render pakai Remotion.

**Architecture:**

- Package Python `mayzfact` (dijalanin pakai uv) ngejalanin 6 step berurutan: `source → script → tts → clips → timeline → render`.
- Tiap step nulis file hasil ke `runs/<id>/`. Kalau file-nya udah ada, step itu di-skip.
- Naskah + suara dikunci begitu `voice.mp3` ada.
- Project Remotion di `remotion/` cuma baca `timeline.json` sebagai props, terus render MP4.
- Semua API eksternal lewat client tipis yang bisa diganti fake waktu test.

**Tech Stack:**

- Python 3.14 via uv: httpx, pydantic, google-genai, youtube-transcript-api, Pillow, python-dotenv, pytest
- ffmpeg/ffprobe 9
- Node 22.23.1 + Remotion 4 (React 19, TypeScript)
- ElevenLabs REST API, Pexels API, Pixabay API

**Spec:** [`docs/superpowers/specs/2026-09-30-fase1-pipeline-design.md`](../specs/2026-09-30-fase1-pipeline-design.md). Keputusan pendukungnya ada di [`docs/DECISIONS.md`](../../DECISIONS.md). Baca dua-duanya sebelum mulai.

## Global Constraints

### Output & layout

- Output `runs/<id>/final.mp4`: 1080x1920, 30fps, H.264 + AAC. Audio cuma TTS, dan semua klip di-mute.
- Satu-satunya efek: zoom-in linear foto dari 1.00 ke 1.08 (`PHOTO_ZOOM`). Di layout blur, cuma isi kotak foreground yang di-zoom.
- Layout: kalau `lebar / tinggi ≤ 0.75` pakai `full`, selain itu `blur`.
- `fgHeight` = tinggi natural media kalau selebar 1080, minimal `FG_MIN_HEIGHT_RATIO × 1920` (default 960), maksimal 1920.

### Angka default

- Config (`.env`): `TARGET_DURATION_RATIO=0.6`, `MIN_DURATION_SECONDS=32`, `MAX_SHOT_SECONDS=2.5`, `PHOTO_RATIO=0.3`, `FG_MIN_HEIGHT_RATIO=0.5`.
- Default model: `GEMINI_MODEL=gemini-3.8-flash`, `ELEVENLABS_MODEL=eleven_v3`.
- Konstanta di code:
  - 2.6 kata/detik
  - toleransi jumlah kata ±15%
  - porsi beat foto 15%–45%
  - overlap word 4-gram maksimal 15%
  - batas rasio 0.75
  - TTS minimal 30 detik
  - retry HTTP 3x dengan backoff 1s, 2s, 4s
  - cache search 24 jam

### Kunci naskah + suara (spec 3.4)

- Begitu `voice.mp3` ada, `script.json`, `voice.mp3`, dan `tts.json` nggak di-generate ulang.
- `--from source|script|tts` ditolak kalau `voice.mp3` udah ada.
- Suara baru cuma lewat `--new-voice`, dan flag ini nggak bisa digabung sama `--from`.
- Hash naskah di `tts.json` dicek tiap run sebelum `clips`.

### Aturan kerja

- Test otomatis **nggak boleh** manggil API beneran (Gemini, ElevenLabs, Pexels, Pixabay, YouTube). Test yang jalanin Remotion beneran dikasih marker `render`.
- API key nggak pernah di-print, di-log, atau ditulis ke file cache.
- Tooling: uv (`requires-python >=3.12`, pakai 3.14 yang udah ada), Node 22.23.1 via nvm, npm, ffmpeg/ffprobe dari PATH. Semua command Python lewat `uv run`.
- Jangan ubah atau hapus `transcript.py`, `flow.svg`, dan `sources/`.
- Pesan buat user (error/log CLI) pakai bahasa Indonesia santai. Prompt dan feedback ke Gemini pakai English.
- **Commit** udah diizinin Akmal (chat 2026-10-01: "kalo mau commit, commit aja"). Aturannya:
  - Kerjain di branch `fase1-pipeline`, jangan di `master`.
  - Pesan commit dibikin pakai skill `caveman-commit`, 1 baris aja.
  - Tanpa `Co-Authored-By` atau atribusi AI apa pun.
  - Push tetap tanya Akmal dulu.

## Review Focus

Ini 5 input/kondisi yang nggak disebut eksplisit di spec tapi paling mungkin bikin masalah. Tiap poin udah ada test-nya di task yang megang code-nya:

1. **Tanda baca "fancy" dari Gemini** (`’ “ ” — …`, spasi dobel). Teks yang dikirim ke ElevenLabs harus sama persis dengan karakter di alignment, jadi teks dibersihin sebelum disimpan. Test: Task 3 (`clean_text`) dan Task 6 (timing beat dengan tanda baca).
2. **Response stock API yang nggak lengkap**: file HLS Pexels tanpa width/height, rendition `large` Pixabay yang URL-nya kosong, foto tanpa `src`. Item kayak gini harus di-skip, bukan bikin crash. Test: Task 9.
3. **Foto dengan orientasi EXIF** (foto HP yang disimpan miring). Hasil normalisasi harus tegak. Test: Task 11.
4. **Query lebih dari 100 karakter.** Pixabay nolak `q` yang lebih panjang dari itu, jadi harus dipotong. Test: Task 9.
5. **Path Windows (`\`) di `clips.json`.** `src` di timeline harus pakai `/` karena dipakai `staticFile()` Remotion. Test: Task 12.

---

## File Structure

```text
pyproject.toml                  # project uv + entry point `mayzfact`
.gitignore / .env.example
README.md                       # setup + cara pakai (Task 14)
mayzfact/
  __init__.py
  errors.py                     # PipelineError(step, message)
  config.py                     # Settings, load_settings, missing_env, PROJECT_ROOT/RUNS_DIR/CACHE_DIR
  store.py                      # RunPaths + tulis file atomic
  models.py                     # pydantic Beat/Script (schema Gemini)
  text.py                       # clean_text, words, ngram_overlap, script_text, text_hash
  net.py                        # retry_call, request_json, download, make_client
  cache.py                      # SearchCache (24 jam)
  timing.py                     # beat_timings dari alignment
  ffmpeg.py                     # probe, audio_duration, normalize_video
  photo.py                      # normalize_photo (Pillow, EXIF)
  media.py                      # layout_for, fg_height, needed_scale, tier, pick_rendition, downscale_factor
  pipeline.py                   # STEPS, plan_steps, check_voice, Deps, run_pipeline
  cli.py                        # argparse: run, voices
  prompts/rewrite.md            # system prompt Gemini (English)
  providers/
    __init__.py
    types.py                    # Rendition, Candidate
    gemini.py                   # GeminiScriptWriter
    elevenlabs.py               # ElevenLabsTTS, list_voices
    pexels.py / pixabay.py      # search → Candidate
    stock.py                    # merge_candidates, StockSearch
  steps/
    __init__.py
    source.py script.py tts.py clips.py timeline.py render.py
remotion/
  package.json tsconfig.json
  src/index.ts src/Root.tsx src/ShortVideo.tsx src/ShotView.tsx src/types.ts
tests/
  __init__.py conftest.py factories.py test_*.py
docs/HANDOFF.md                 # Task 15
```

---

### Task 1: Scaffold project Python + config + store

**Files:**

- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `mayzfact/__init__.py`, `mayzfact/errors.py`, `mayzfact/config.py`, `mayzfact/store.py`, `tests/__init__.py`
- Test: `tests/test_config.py`, `tests/test_store.py`

**Interfaces:**

- Consumes: —
- Produces:
  - `PipelineError(step: str, message: str)`. Atributnya `.step` dan `.message`, dan `str()`-nya `"[step] message"`.
  - `Settings`: frozen dataclass dengan field `gemini_api_key`, `gemini_model`, `elevenlabs_api_key`, `elevenlabs_voice_id`, `elevenlabs_model`, `pexels_api_key`, `pixabay_api_key`, `target_duration_ratio`, `min_duration_seconds`, `max_shot_seconds`, `photo_ratio`, `fg_min_height_ratio`.
  - Fungsi config: `settings_from_env(env: Mapping[str, str | None]) -> Settings`, `load_settings(env_file: Path = PROJECT_ROOT / ".env") -> Settings`, `missing_env(settings: Settings, names: list[str]) -> list[str]`.
  - Konstanta path: `PROJECT_ROOT`, `RUNS_DIR`, `CACHE_DIR`.
  - `RunPaths(root: Path)` dengan property `source_json`, `script_json`, `voice_mp3`, `tts_json`, `clips_dir`, `clips_json`, `timeline_json`, `final_mp4`.
  - Fungsi file: `tmp_path_for(path) -> Path`, `write_bytes_atomic(path, data: bytes)`, `write_json_atomic(path, data)`, `read_json(path)`.

- [ ] **Step 1: Bikin file project**

`pyproject.toml`:

```toml
[project]
name = "mayzfact"
version = "0.1.0"
description = "Pipeline shorts: naskah ulang + TTS + klip stock"
requires-python = ">=3.12"
dependencies = [
  "google-genai>=1.33",
  "httpx>=0.28",
  "pillow>=11",
  "pydantic>=2.9",
  "python-dotenv>=1.0",
  "youtube-transcript-api>=1.2",
]

[project.scripts]
mayzfact = "mayzfact.cli:main"

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["mayzfact"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not render'"
markers = ["render: jalanin Remotion beneran (lambat, butuh Node 22)"]
```

`.gitignore`:

```gitignore
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
runs/
cache/
sources/
remotion/node_modules/
```

`.env.example`:

```dotenv
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ELEVENLABS_MODEL=eleven_v3
PEXELS_API_KEY=
PIXABAY_API_KEY=
TARGET_DURATION_RATIO=0.6
MIN_DURATION_SECONDS=32
MAX_SHOT_SECONDS=2.5
PHOTO_RATIO=0.3
FG_MIN_HEIGHT_RATIO=0.5
```

`mayzfact/__init__.py`:

```python
"""Pipeline YouTube Shorts: naskah ulang + TTS + klip stock."""
```

`tests/__init__.py`: file kosong.

- [ ] **Step 2: Install environment**

Run: `uv sync`
Expected: folder `.venv/` kebentuk, dependency + pytest ke-install, dan nggak ada error.

- [ ] **Step 3: Tulis test yang gagal**

`tests/test_config.py`:

```python
import pytest

from mayzfact.config import Settings, load_settings, missing_env, settings_from_env
from mayzfact.errors import PipelineError


def test_defaults_when_env_empty():
    settings = settings_from_env({})
    assert settings == Settings()
    assert settings.max_shot_seconds == 2.5
    assert settings.fg_min_height_ratio == 0.5
    assert settings.gemini_model == "gemini-3.8-flash"


def test_reads_and_casts_values():
    settings = settings_from_env({"GEMINI_API_KEY": " abc ", "MAX_SHOT_SECONDS": "2.0", "PHOTO_RATIO": "0.25"})
    assert settings.gemini_api_key == "abc"
    assert settings.max_shot_seconds == 2.0
    assert settings.photo_ratio == 0.25


def test_blank_value_keeps_default():
    settings = settings_from_env({"GEMINI_MODEL": "   ", "PEXELS_API_KEY": None})
    assert settings.gemini_model == "gemini-3.8-flash"
    assert settings.pexels_api_key == ""


def test_invalid_number_names_the_variable():
    with pytest.raises(PipelineError, match="MAX_SHOT_SECONDS"):
        settings_from_env({"MAX_SHOT_SECONDS": "dua"})


def test_missing_env_lists_empty_keys_once():
    settings = settings_from_env({"GEMINI_API_KEY": "x"})
    assert missing_env(settings, ["GEMINI_API_KEY", "PEXELS_API_KEY", "PEXELS_API_KEY"]) == ["PEXELS_API_KEY"]


def test_environment_overrides_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=from-file\nPEXELS_API_KEY=file-key\n", encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("PEXELS_API_KEY", "")
    settings = load_settings(env_file)
    assert settings.gemini_api_key == "from-file"
    assert settings.pexels_api_key == ""
```

`tests/test_store.py`:

```python
from mayzfact.store import RunPaths, read_json, tmp_path_for, write_json_atomic


def test_write_json_atomic_roundtrip_without_leftover(tmp_path):
    target = tmp_path / "nested" / "data.json"
    write_json_atomic(target, {"judul": "Kepiting", "angka": [1, 2]})
    assert read_json(target) == {"judul": "Kepiting", "angka": [1, 2]}
    assert sorted(p.name for p in target.parent.iterdir()) == ["data.json"]


def test_tmp_path_keeps_extension(tmp_path):
    assert tmp_path_for(tmp_path / "shot_01.mp4").name == "shot_01.tmp.mp4"
    assert tmp_path_for(tmp_path / "voice.incoming.mp3").name == "voice.incoming.tmp.mp3"


def test_run_paths_layout(tmp_path):
    paths = RunPaths(tmp_path / "abc")
    assert paths.source_json == tmp_path / "abc" / "source.json"
    assert paths.voice_mp3 == tmp_path / "abc" / "voice.mp3"
    assert paths.clips_dir == tmp_path / "abc" / "clips"
    assert paths.final_mp4.name == "final.mp4"
```

- [ ] **Step 4: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_config.py tests/test_store.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.config'`.

- [ ] **Step 5: Implementasi**

`mayzfact/errors.py`:

```python
"""Error pipeline yang pesannya aman ditampilin langsung ke user."""


class PipelineError(Exception):
    def __init__(self, step: str, message: str) -> None:
        super().__init__(f"[{step}] {message}")
        self.step = step
        self.message = message
```

`mayzfact/config.py`:

```python
"""Config dari .env + environment variable."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from dotenv import dotenv_values

from mayzfact.errors import PipelineError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"
CACHE_DIR = PROJECT_ROOT / "cache"


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model: str = "eleven_v3"
    pexels_api_key: str = ""
    pixabay_api_key: str = ""
    target_duration_ratio: float = 0.6
    min_duration_seconds: float = 32.0
    max_shot_seconds: float = 2.5
    photo_ratio: float = 0.3
    fg_min_height_ratio: float = 0.5


ENV_FIELDS: dict[str, tuple[str, Callable[[str], object]]] = {
    "GEMINI_API_KEY": ("gemini_api_key", str),
    "GEMINI_MODEL": ("gemini_model", str),
    "ELEVENLABS_API_KEY": ("elevenlabs_api_key", str),
    "ELEVENLABS_VOICE_ID": ("elevenlabs_voice_id", str),
    "ELEVENLABS_MODEL": ("elevenlabs_model", str),
    "PEXELS_API_KEY": ("pexels_api_key", str),
    "PIXABAY_API_KEY": ("pixabay_api_key", str),
    "TARGET_DURATION_RATIO": ("target_duration_ratio", float),
    "MIN_DURATION_SECONDS": ("min_duration_seconds", float),
    "MAX_SHOT_SECONDS": ("max_shot_seconds", float),
    "PHOTO_RATIO": ("photo_ratio", float),
    "FG_MIN_HEIGHT_RATIO": ("fg_min_height_ratio", float),
}


def settings_from_env(env: Mapping[str, str | None]) -> Settings:
    values: dict[str, object] = {}
    for env_name, (field_name, cast) in ENV_FIELDS.items():
        raw = (env.get(env_name) or "").strip()
        if not raw:
            continue
        try:
            values[field_name] = cast(raw)
        except ValueError as exc:
            raise PipelineError("config", f"{env_name} harus angka, isinya sekarang {raw!r}") from exc
    return Settings(**values)


def load_settings(env_file: Path = PROJECT_ROOT / ".env") -> Settings:
    """Isi .env jadi default. Environment variable beneran (termasuk yang kosong) menang."""
    merged: dict[str, str | None] = dict(dotenv_values(env_file)) if env_file.exists() else {}
    merged.update({name: os.environ[name] for name in ENV_FIELDS if name in os.environ})
    return settings_from_env(merged)


def missing_env(settings: Settings, names: list[str]) -> list[str]:
    missing: list[str] = []
    for name in names:
        field_name, _ = ENV_FIELDS[name]
        if not getattr(settings, field_name) and name not in missing:
            missing.append(name)
    return missing
```

`mayzfact/store.py`:

```python
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
```

- [ ] **Step 6: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_config.py tests/test_store.py -v`
Expected: 9 test PASS.

- [ ] **Step 7: Commit (kalau udah diizinin)**

```bash
git switch -c fase1-pipeline
git add pyproject.toml uv.lock .gitignore .env.example mayzfact/__init__.py mayzfact/errors.py mayzfact/config.py mayzfact/store.py tests/__init__.py tests/test_config.py tests/test_store.py
git commit -m "feat: scaffold python project, config, run store"
```

---

### Task 2: Step source (video ID + transcript)

**Files:**

- Create: `mayzfact/steps/__init__.py`, `mayzfact/steps/source.py`
- Test: `tests/test_source.py`

**Interfaces:**

- Consumes: `PipelineError`, `RunPaths`, `write_json_atomic` (Task 1)
- Produces:
  - `parse_video_id(value: str) -> str`
  - `youtube_transcript(video_id: str) -> list[dict]`
  - `build_source(video_id: str, snippets: list[dict]) -> dict`
  - `run_source(video_id: str, paths: RunPaths, fetch: Callable[[str], list[dict]] = youtube_transcript) -> dict`

  Format `source.json`: `{"video_id", "duration_s", "transcript": [{"text", "start", "duration"}]}`.

- [ ] **Step 1: Tulis test yang gagal**

`mayzfact/steps/__init__.py`: file kosong.

`tests/test_source.py`:

```python
import pytest
from youtube_transcript_api import TranscriptsDisabled

from mayzfact.errors import PipelineError
from mayzfact.steps.source import build_source, parse_video_id, run_source, youtube_transcript
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
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_source.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.steps.source'`.

- [ ] **Step 3: Implementasi**

`mayzfact/steps/source.py`:

```python
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
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_source.py -v`
Expected: 11 test PASS.

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/steps/__init__.py mayzfact/steps/source.py tests/test_source.py
git commit -m "feat: add source step with transcript fetch"
```

---

### Task 3: Aturan teks + naskah (tanpa API)

**Files:**

- Create: `mayzfact/models.py`, `mayzfact/text.py`, `mayzfact/steps/script.py`, `mayzfact/prompts/rewrite.md`, `tests/factories.py`
- Test: `tests/test_text.py`, `tests/test_script_rules.py`

**Interfaces:**

- Consumes: `PipelineError` (Task 1)
- Produces:
  - Model: `Beat(text: str, media: Literal["video","photo"], queries: list[str])` dan `Script(beats: list[Beat], fallback_query: str)`.
  - Di `text.py`:
    - `clean_text(text) -> str`
    - `words(text) -> list[str]`
    - `ngrams(tokens, n) -> set[tuple]`
    - `ngram_overlap(new_text, source_text, n=4) -> float`
    - `beat_texts(beats: list[dict]) -> list[str]`
    - `script_text(beats: list[dict]) -> str`, yaitu teks utuh yang dikirim ke TTS
    - `text_hash(text) -> str`
  - Di `steps/script.py`:
    - Konstanta `WORDS_PER_SECOND`, `WORD_TOLERANCE`, `PHOTO_SHARE_RANGE`, `MAX_NGRAM_OVERLAP`, `PROMPT_PATH`.
    - `target_duration(source_duration_s, ratio, minimum_s) -> float`
    - `word_range(duration_s) -> tuple[int, int, int]` (target, low, high)
    - `normalize_script(script) -> Script`
    - `check_script(script, source_text, duration_s) -> tuple[list[str], float]`
    - `build_user_prompt(source, duration_s, photo_ratio, feedback=None, previous=None) -> str`
  - Di `tests/factories.py`: `make_script(n_beats=10, photo_every=3, words_per_beat=11) -> Script`.

- [ ] **Step 1: Tulis test yang gagal**

`tests/factories.py`:

```python
"""Pembuat data palsu buat test."""

from __future__ import annotations

from mayzfact.models import Beat, Script


def make_script(n_beats: int = 10, photo_every: int = 3, words_per_beat: int = 11) -> Script:
    """Naskah dengan kata unik (w0x0, w0x1, ...) biar overlap ke source selalu 0."""
    beats = [
        Beat(
            text=" ".join(f"w{i}x{j}" for j in range(words_per_beat)) + ".",
            media="photo" if i % photo_every == 1 else "video",
            queries=[f"query {i}", "animal close up"],
        )
        for i in range(n_beats)
    ]
    return Script(beats=beats, fallback_query="ocean animals")
```

`tests/test_text.py`:

```python
from mayzfact.text import clean_text, ngram_overlap, script_text, text_hash, words


def test_clean_text_turns_fancy_punctuation_into_ascii():
    assert clean_text("It\u2019s  \u201chuge\u201d \u2014 really\u2026 wow\u00a0now") == 'It\'s "huge", really... wow now'
    assert clean_text("1\u20132 eggs") == "1-2 eggs"


def test_words_lowercases_and_keeps_apostrophes():
    assert words("They\u2019re HERE, 100 times!") == ["they're", "here", "100", "times"]


def test_ngram_overlap():
    source = "these animals have been around for millions of years"
    assert ngram_overlap(source, source) == 1.0
    assert ngram_overlap("a totally different sentence about crabs", source) == 0.0
    assert ngram_overlap("too short", source) == 0.0
    # 4-gram baru: (have been around for) ada di source, (been around for ages) nggak
    assert ngram_overlap("have been around for ages", source) == 0.5


def test_script_text_joins_cleaned_beats_with_single_space():
    beats = [{"text": " Look  at this. "}, {"text": "It\u2019s old."}]
    assert script_text(beats) == "Look at this. It's old."


def test_text_hash_is_sha256():
    assert text_hash("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
```

`tests/test_script_rules.py`:

```python
from mayzfact.models import Beat, Script
from mayzfact.steps.script import (
    build_user_prompt,
    check_script,
    normalize_script,
    target_duration,
    word_range,
)
from tests.factories import make_script

SOURCE = {
    "video_id": "i2xag_1OJfM",
    "duration_s": 70.8,
    "transcript": [
        {"text": "These are the top five ancient creatures that still exist today.", "start": 0.0, "duration": 2.5},
        {"text": "to this video", "start": 2.5, "duration": 1.8},
    ],
}
SOURCE_TEXT = " ".join(s["text"] for s in SOURCE["transcript"])
DURATION = target_duration(70.8, 0.6, 32)


def test_target_duration_and_word_range():
    assert round(DURATION, 2) == 42.48
    assert target_duration(40, 0.6, 32) == 32
    assert word_range(DURATION) == (110, 94, 126)


def test_good_script_has_no_problems():
    problems, overlap = check_script(make_script(), SOURCE_TEXT, DURATION)
    assert problems == []
    assert overlap == 0.0


def test_word_count_outside_range_is_reported():
    problems, _ = check_script(make_script(words_per_beat=5), SOURCE_TEXT, DURATION)
    assert any("words" in p for p in problems)


def test_photo_share_outside_range_is_reported():
    problems, _ = check_script(make_script(photo_every=1), SOURCE_TEXT, DURATION)
    assert any("photo" in p for p in problems)


def test_copied_phrases_are_reported():
    copied = Script(
        beats=[Beat(text=SOURCE_TEXT, media="video", queries=["crab"])] * 10,
        fallback_query="animals",
    )
    problems, overlap = check_script(copied, SOURCE_TEXT, DURATION)
    # Nggak persis 1.0: kalimat yang diulang bikin 4-gram lintas kalimat yang nggak ada di source.
    assert overlap > 0.5
    assert any("copied" in p for p in problems)


def test_empty_queries_and_fallback_are_reported():
    script = make_script()
    script = script.model_copy(
        update={
            "beats": [script.beats[0].model_copy(update={"queries": []}), *script.beats[1:]],
            "fallback_query": "",
        }
    )
    problems, _ = check_script(script, SOURCE_TEXT, DURATION)
    assert "Beat 1 has no search queries." in problems
    assert "fallback_query is empty." in problems


def test_normalize_script_cleans_text_and_forces_first_video():
    raw = Script(
        beats=[
            Beat(text="It\u2019s  here \u2014now", media="photo", queries=[" crab ", " "]),
            Beat(text="Second", media="photo", queries=["fossil"]),
        ],
        fallback_query="  ocean  ",
    )
    script = normalize_script(raw)
    assert script.beats[0].text == "It's here, now"
    assert script.beats[0].media == "video"
    assert script.beats[0].queries == ["crab"]
    assert script.beats[1].media == "photo"
    assert script.fallback_query == "ocean"


def test_user_prompt_has_targets_transcript_and_feedback():
    prompt = build_user_prompt(SOURCE, DURATION, 0.3)
    assert "about 110 words in total (allowed: 94-126)" in prompt
    assert "[2.5s] to this video" in prompt
    assert "30%" in prompt
    assert "rejected" not in prompt
    retry = build_user_prompt(SOURCE, DURATION, 0.3, feedback=["Too short."], previous=make_script(n_beats=1))
    assert "Your previous answer was rejected:" in retry
    assert "- Too short." in retry
    assert '"fallback_query":"ocean animals"' in retry
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_text.py tests/test_script_rules.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.models'`.

- [ ] **Step 3: Implementasi**

`mayzfact/models.py`:

```python
"""Schema naskah yang dipakai Gemini dan step-step setelahnya."""

from typing import Literal

from pydantic import BaseModel


class Beat(BaseModel):
    text: str
    media: Literal["video", "photo"]
    queries: list[str]


class Script(BaseModel):
    beats: list[Beat]
    fallback_query: str
```

`mayzfact/text.py`:

```python
"""Utilitas teks: bersihin naskah, hitung kata, overlap n-gram, hash."""

from __future__ import annotations

import hashlib
import re

_SIMPLE = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u00a0": " "})
_EM_DASH = re.compile(r"\s*\u2014\s*")
_WORD = re.compile(r"[a-z0-9']+")


def clean_text(text: str) -> str:
    """Tanda baca 'fancy' jadi ASCII + spasi dirapihin, biar teks ke TTS = karakter di alignment."""
    text = text.translate(_SIMPLE).replace("\u2026", "...")
    text = _EM_DASH.sub(", ", text)
    return " ".join(text.split())


def words(text: str) -> list[str]:
    return _WORD.findall(clean_text(text).lower())


def ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def ngram_overlap(new_text: str, source_text: str, n: int = 4) -> float:
    """Porsi n-gram unik di naskah baru yang juga muncul di source (0.0 - 1.0)."""
    new_grams = ngrams(words(new_text), n)
    if not new_grams:
        return 0.0
    return len(new_grams & ngrams(words(source_text), n)) / len(new_grams)


def beat_texts(beats: list[dict]) -> list[str]:
    return [clean_text(beat["text"]) for beat in beats]


def script_text(beats: list[dict]) -> str:
    """Teks utuh yang dikirim ke TTS: teks beat yang udah bersih, digabung pakai 1 spasi."""
    return " ".join(beat_texts(beats))


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

`mayzfact/steps/script.py`:

```python
"""Step script: rewrite transcript jadi naskah baru (aturan + prompt)."""

from __future__ import annotations

import math
from pathlib import Path

from mayzfact.models import Beat, Script
from mayzfact.text import clean_text, ngram_overlap, words

WORDS_PER_SECOND = 2.6
WORD_TOLERANCE = 0.15
PHOTO_SHARE_RANGE = (0.15, 0.45)
MAX_NGRAM_OVERLAP = 0.15
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "rewrite.md"


def target_duration(source_duration_s: float, ratio: float, minimum_s: float) -> float:
    return max(minimum_s, ratio * source_duration_s)


def word_range(duration_s: float) -> tuple[int, int, int]:
    target = round(duration_s * WORDS_PER_SECOND)
    return target, math.ceil(target * (1 - WORD_TOLERANCE)), math.floor(target * (1 + WORD_TOLERANCE))


def normalize_script(script: Script) -> Script:
    """Bersihin teks & keyword, lalu paksa beat pertama jadi video."""
    beats = [
        Beat(text=clean_text(b.text), media=b.media, queries=[q.strip() for q in b.queries if q.strip()])
        for b in script.beats
    ]
    if beats:
        beats[0] = beats[0].model_copy(update={"media": "video"})
    return Script(beats=beats, fallback_query=" ".join(script.fallback_query.split()))


def check_script(script: Script, source_text: str, duration_s: float) -> tuple[list[str], float]:
    """Balikin (daftar masalah, overlap). Pesan masalah pakai English karena dikirim balik ke Gemini."""
    if not script.beats:
        return ["The script has no beats."], 0.0
    problems: list[str] = []
    full_text = " ".join(b.text for b in script.beats)
    count = len(words(full_text))
    _, low, high = word_range(duration_s)
    if not low <= count <= high:
        problems.append(f"The narration has {count} words; it must have between {low} and {high}.")
    share = sum(b.media == "photo" for b in script.beats) / len(script.beats)
    share_low, share_high = PHOTO_SHARE_RANGE
    if not share_low <= share <= share_high:
        problems.append(
            f"{share:.0%} of the beats use a photo; it must be between {share_low:.0%} and {share_high:.0%}."
        )
    for number, beat in enumerate(script.beats, start=1):
        if not beat.text:
            problems.append(f"Beat {number} has empty text.")
        if not beat.queries:
            problems.append(f"Beat {number} has no search queries.")
    if not script.fallback_query:
        problems.append("fallback_query is empty.")
    overlap = ngram_overlap(full_text, source_text)
    if overlap > MAX_NGRAM_OVERLAP:
        problems.append(
            f"{overlap:.0%} of the 4-word phrases are copied from the source; "
            f"keep it at or below {MAX_NGRAM_OVERLAP:.0%}. Rephrase more."
        )
    return problems, overlap


def build_user_prompt(
    source: dict,
    duration_s: float,
    photo_ratio: float,
    feedback: list[str] | None = None,
    previous: Script | None = None,
) -> str:
    target, low, high = word_range(duration_s)
    lines = [
        f"Source duration: {source['duration_s']:.1f} seconds.",
        f"Target narration: about {duration_s:.0f} seconds, about {target} words in total (allowed: {low}-{high}).",
        f'About {photo_ratio:.0%} of the beats should use media "photo". The first beat must use "video".',
        "",
        "Source transcript with timestamps:",
        *(f"[{s['start']:.1f}s] {s['text']}" for s in source["transcript"]),
    ]
    if feedback:
        lines += ["", "Your previous answer was rejected:", *(f"- {p}" for p in feedback)]
        if previous is not None:
            lines += ["Previous answer:", previous.model_dump_json()]
        lines.append("Write a corrected answer.")
    return "\n".join(lines)
```

`mayzfact/prompts/rewrite.md`:

```markdown
You rewrite narration scripts for vertical short videos (YouTube Shorts, TikTok, Reels).

You receive the transcript of an existing short, with timestamps. Write a NEW English narration for a new video on the same topic.

Rules:
- Keep the same flow and the same main message, in the same order: hook, development, ending.
- Keep a similar tempo and rhythm. The hook lands as fast as in the source, and the ending closes the same way.
- Write every sentence from scratch. Do not trim or lightly edit the original sentences.
- Use different word choices, sentence structures and transitions, so it never reads like a copy.
- Drop the less important points and keep the core facts.
- Only use facts that are in the source transcript.
- It must sound natural read aloud by an energetic, friendly male voice, like a teacher talking to curious kids.
- Keep the source's call to action (like, subscribe, comment), but say it in new words.
- You may make the hook stronger, as long as the core message stays the same.
- No emojis, hashtags, stage directions, sound effects or text in brackets.

Split the narration into beats. One beat is one short sentence or clause that carries one visual idea, usually 1.5 to 3.5 seconds when spoken.

For every beat return:
- "text": the narration of the beat.
- "media": "video" when the visual needs motion or action, "photo" when a still image of the subject works (a close-up of a specific animal, a fossil, an object). The first beat is always "video".
- "queries": 2 or 3 English search terms for stock footage sites like Pexels and Pixabay, most specific first. Describe what is visible ("horseshoe crab on sandy beach"), not abstract ideas ("ancient"). No numbers, logos or on-screen text.

Also return "fallback_query": one broad search term for the topic of the whole video (for example "ocean animals").
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_text.py tests/test_script_rules.py -v`
Expected: 13 test PASS.

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/models.py mayzfact/text.py mayzfact/steps/script.py mayzfact/prompts/rewrite.md tests/factories.py tests/test_text.py tests/test_script_rules.py
git commit -m "feat: add script rules, text utils, rewrite prompt"
```

---

### Task 4: HTTP retry, download, dan cache search

**Files:**

- Create: `mayzfact/net.py`, `mayzfact/cache.py`
- Test: `tests/test_net.py`, `tests/test_cache.py`

**Interfaces:**

- Consumes: `PipelineError`, `read_json`, `write_json_atomic` (Task 1)
- Produces:
  - Konstanta `RETRYABLE_STATUS = {429, 500, 502, 503, 504}` dan `RETRIES = 3`.
  - `retry_call(fn, *, is_retryable, step, what, retries=3, backoff_s=1.0, sleep=time.sleep)`
  - `RetryableHttpError(status, body)`
  - `request_json(client, method, url, *, step, sleep=time.sleep, **kwargs) -> dict`
  - `download(client, url, dest, *, step, sleep=time.sleep) -> Path`. Kalau `dest` udah ada, file itu dianggap cache.
  - `make_client(timeout_s=60.0) -> httpx.Client`
  - `SearchCache(root: Path, ttl_s: float = 86400, now=time.time)` dengan method `.get(provider, params) -> dict | None` dan `.put(provider, params, response)`.

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_net.py`:

```python
import httpx
import pytest

from mayzfact.errors import PipelineError
from mayzfact.net import download, request_json, retry_call


def client_with(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_request_json_retries_on_429_then_succeeds():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, json={"ok": True})

    sleeps = []
    result = request_json(client_with(handler), "GET", "https://api.test/x", step="clips", sleep=sleeps.append)
    assert result == {"ok": True}
    assert len(calls) == 3
    assert sleeps == [1.0, 2.0]


def test_request_json_gives_up_after_three_retries():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503, text="down")

    with pytest.raises(PipelineError, match="503"):
        request_json(client_with(handler), "GET", "https://api.test/x", step="clips", sleep=lambda s: None)
    assert len(calls) == 4


def test_request_json_does_not_retry_client_errors():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(401, text="bad key")

    with pytest.raises(PipelineError, match=r"\[clips\].*401"):
        request_json(client_with(handler), "GET", "https://api.test/x", step="clips", sleep=lambda s: None)
    assert len(calls) == 1


def test_download_writes_file_and_skips_when_cached(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=b"video-bytes")

    client = client_with(handler)
    dest = tmp_path / "media" / "pexels_video_1.mp4"
    download(client, "https://cdn.test/a.mp4", dest, step="clips")
    download(client, "https://cdn.test/a.mp4", dest, step="clips")
    assert dest.read_bytes() == b"video-bytes"
    assert len(calls) == 1
    assert sorted(p.name for p in dest.parent.iterdir()) == ["pexels_video_1.mp4"]


def test_download_retries_server_errors(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(502) if len(calls) == 1 else httpx.Response(200, content=b"ok")

    dest = tmp_path / "file.jpg"
    download(client_with(handler), "https://cdn.test/f.jpg", dest, step="clips", sleep=lambda s: None)
    assert dest.read_bytes() == b"ok"


def test_retry_call_wraps_non_retryable_errors():
    def boom():
        raise ValueError("nope")

    with pytest.raises(PipelineError, match=r"\[script\] Gemini gagal: nope"):
        retry_call(boom, is_retryable=lambda e: False, step="script", what="Gemini", sleep=lambda s: None)
```

`tests/test_cache.py`:

```python
from mayzfact.cache import SearchCache


def test_cache_hit_within_ttl_and_miss_after(tmp_path):
    clock = [1000.0]
    cache = SearchCache(tmp_path, ttl_s=24 * 3600, now=lambda: clock[0])
    params = {"url": "https://api.test/search", "query": "crab"}
    assert cache.get("pexels", params) is None
    cache.put("pexels", params, {"videos": [1]})
    clock[0] += 3600
    assert cache.get("pexels", params) == {"videos": [1]}
    clock[0] += 24 * 3600
    assert cache.get("pexels", params) is None


def test_cache_key_ignores_param_order(tmp_path):
    cache = SearchCache(tmp_path)
    cache.put("pixabay", {"q": "crab", "per_page": 30}, {"hits": []})
    assert cache.get("pixabay", {"per_page": 30, "q": "crab"}) == {"hits": []}
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_net.py tests/test_cache.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.net'`.

- [ ] **Step 3: Implementasi**

`mayzfact/net.py`:

```python
"""HTTP helper: retry buat 429/5xx/network error, dan download file."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable, TypeVar

import httpx

from mayzfact.errors import PipelineError

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
RETRIES = 3
T = TypeVar("T")


def retry_call(
    fn: Callable[[], T],
    *,
    is_retryable: Callable[[Exception], bool],
    step: str,
    what: str,
    retries: int = RETRIES,
    backoff_s: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Jalanin fn. Error yang retryable diulang max `retries` kali (jeda 1s, 2s, 4s)."""
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == retries or not is_retryable(exc):
                if isinstance(exc, PipelineError):
                    raise
                raise PipelineError(step, f"{what} gagal: {exc}") from exc
            sleep(backoff_s * 2**attempt)
    raise AssertionError("unreachable")


class RetryableHttpError(Exception):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status


def _http_retryable(exc: Exception) -> bool:
    return isinstance(exc, (RetryableHttpError, httpx.TransportError))


def request_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    step: str,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs,
) -> dict:
    """Request yang ngarepin JSON. Error 4xx selain 429 langsung stop tanpa retry."""

    def call() -> dict:
        response = client.request(method, url, **kwargs)
        if response.status_code in RETRYABLE_STATUS:
            raise RetryableHttpError(response.status_code, response.text)
        if response.status_code >= 400:
            raise PipelineError(step, f"{method} {url} -> HTTP {response.status_code}: {response.text[:300]}")
        return response.json()

    return retry_call(call, is_retryable=_http_retryable, step=step, what=f"{method} {url}", sleep=sleep)


def download(
    client: httpx.Client,
    url: str,
    dest: Path,
    *,
    step: str,
    sleep: Callable[[float], None] = time.sleep,
) -> Path:
    """Download ke dest. Kalau dest udah ada, dianggap cache dan nggak di-download ulang."""
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")

    def call() -> Path:
        with client.stream("GET", url, follow_redirects=True) as response:
            if response.status_code in RETRYABLE_STATUS:
                raise RetryableHttpError(response.status_code, "")
            if response.status_code >= 400:
                raise PipelineError(step, f"Download {url} -> HTTP {response.status_code}")
            with part.open("wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)
        os.replace(part, dest)
        return dest

    return retry_call(call, is_retryable=_http_retryable, step=step, what=f"Download {url}", sleep=sleep)


def make_client(timeout_s: float = 60.0) -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(timeout_s, connect=15.0),
        headers={"User-Agent": "mayzfact-automation/0.1"},
    )
```

`mayzfact/cache.py`:

```python
"""Cache response search API di disk (Pixabay minta di-cache 24 jam)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Callable

from mayzfact.store import read_json, write_json_atomic


class SearchCache:
    def __init__(self, root: Path, ttl_s: float = 24 * 3600, now: Callable[[], float] = time.time) -> None:
        self.root = root
        self.ttl_s = ttl_s
        self._now = now

    def _path(self, provider: str, params: dict) -> Path:
        digest = hashlib.sha256(json.dumps(params, sort_keys=True).encode("utf-8")).hexdigest()[:24]
        return self.root / provider / f"{digest}.json"

    def get(self, provider: str, params: dict) -> dict | None:
        path = self._path(provider, params)
        if not path.exists():
            return None
        entry = read_json(path)
        if self._now() - entry["saved_at"] > self.ttl_s:
            return None
        return entry["response"]

    def put(self, provider: str, params: dict, response: dict) -> None:
        write_json_atomic(self._path(provider, params), {"saved_at": self._now(), "response": response})
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_net.py tests/test_cache.py -v`
Expected: 8 test PASS.

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/net.py mayzfact/cache.py tests/test_net.py tests/test_cache.py
git commit -m "feat: add http retry, download, search cache"
```

---

### Task 5: Gemini writer + step script

**Files:**

- Create: `mayzfact/providers/__init__.py`, `mayzfact/providers/gemini.py`
- Modify: `mayzfact/steps/script.py`. Tambahin `ScriptWriter`, `generate_script`, `run_script` di bawah file.
- Test: `tests/test_gemini.py`, `tests/test_script_step.py`

**Interfaces:**

- Consumes:
  - `Script` (Task 3)
  - `normalize_script`, `check_script`, `build_user_prompt`, `target_duration`, `word_range`, `PROMPT_PATH` (Task 3)
  - `retry_call`, `RETRYABLE_STATUS` (Task 4)
  - `RunPaths`, `write_json_atomic` (Task 1)
- Produces:
  - `GeminiScriptWriter(api_key: str, model: str, client=None).write(system: str, user: str) -> Script`
  - Protocol `ScriptWriter` dengan method `write(system, user) -> Script`
  - `generate_script(source: dict, writer: ScriptWriter, *, ratio: float, minimum_s: float, photo_ratio: float) -> dict`
  - `run_script(paths, source, writer, *, ratio, minimum_s, photo_ratio) -> dict`

  Format `script.json`: `{"target_seconds", "target_words", "word_count", "ngram_overlap", "fallback_query", "beats": [{"text", "media", "queries"}]}`.

- [ ] **Step 1: Tulis test yang gagal**

`mayzfact/providers/__init__.py`: file kosong.

`tests/test_gemini.py`:

```python
from types import SimpleNamespace

import pytest
from google.genai import errors

from mayzfact.errors import PipelineError
from mayzfact.providers.gemini import GeminiScriptWriter, _gemini_retryable
from tests.factories import make_script

VALID_JSON = make_script(n_beats=2).model_dump_json()


class FakeModels:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return SimpleNamespace(text=self.outputs.pop(0))


class FakeClient:
    def __init__(self, outputs):
        self.models = FakeModels(outputs)


def test_writer_parses_structured_output_and_sends_config():
    client = FakeClient([VALID_JSON])
    script = GeminiScriptWriter("key", "gemini-test", client=client).write("system rules", "user prompt")
    assert len(script.beats) == 2
    call = client.models.calls[0]
    assert call["model"] == "gemini-test"
    assert call["contents"] == "user prompt"
    assert call["config"].system_instruction == "system rules"
    assert call["config"].response_mime_type == "application/json"


def test_writer_rejects_output_outside_schema():
    writer = GeminiScriptWriter("key", "gemini-test", client=FakeClient(['{"beats": "nope"}']))
    with pytest.raises(PipelineError, match="schema"):
        writer.write("s", "u")


def test_only_rate_limit_and_server_errors_are_retried():
    class FakeApiError(errors.APIError):
        def __init__(self, code):
            self.code = code

    assert _gemini_retryable(FakeApiError(429))
    assert _gemini_retryable(FakeApiError(503))
    assert not _gemini_retryable(FakeApiError(400))
    assert not _gemini_retryable(ValueError("x"))
```

`tests/test_script_step.py`:

```python
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
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_gemini.py tests/test_script_step.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.providers.gemini'` dan `ImportError: cannot import name 'generate_script'`.

- [ ] **Step 3: Implementasi**

`mayzfact/providers/gemini.py`:

```python
"""Client Gemini buat nulis naskah (structured output ke schema Script)."""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from mayzfact.errors import PipelineError
from mayzfact.models import Script
from mayzfact.net import RETRYABLE_STATUS, retry_call


def _gemini_retryable(exc: Exception) -> bool:
    return isinstance(exc, errors.APIError) and exc.code in RETRYABLE_STATUS


class GeminiScriptWriter:
    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        self._client = client or genai.Client(api_key=api_key)
        self._model = model

    def write(self, system: str, user: str) -> Script:
        def call():
            return self._client.models.generate_content(
                model=self._model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=Script,
                ),
            )

        response = retry_call(call, is_retryable=_gemini_retryable, step="script", what="Gemini")
        try:
            return Script.model_validate_json(response.text or "")
        except ValidationError as exc:
            raise PipelineError("script", f"Output Gemini nggak sesuai schema: {exc}") from exc
```

Tambahin ke **atas** `mayzfact/steps/script.py`, gabung sama blok import yang udah ada:

```python
from typing import Protocol

from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, write_json_atomic
```

Tambahin ke **bawah** `mayzfact/steps/script.py`:

```python
class ScriptWriter(Protocol):
    def write(self, system: str, user: str) -> Script: ...


def generate_script(
    source: dict, writer: ScriptWriter, *, ratio: float, minimum_s: float, photo_ratio: float
) -> dict:
    duration_s = target_duration(source["duration_s"], ratio, minimum_s)
    source_text = " ".join(s["text"] for s in source["transcript"])
    system = PROMPT_PATH.read_text(encoding="utf-8")
    feedback: list[str] | None = None
    previous: Script | None = None
    problems: list[str] = []
    for _ in range(2):
        prompt = build_user_prompt(source, duration_s, photo_ratio, feedback, previous)
        script = normalize_script(writer.write(system, prompt))
        problems, overlap = check_script(script, source_text, duration_s)
        if not problems:
            target, _, _ = word_range(duration_s)
            return {
                "target_seconds": round(duration_s, 2),
                "target_words": target,
                "word_count": len(words(" ".join(b.text for b in script.beats))),
                "ngram_overlap": round(overlap, 3),
                "fallback_query": script.fallback_query,
                "beats": [b.model_dump() for b in script.beats],
            }
        feedback, previous = problems, script
    raise PipelineError("script", "Naskah dari Gemini masih gagal dicek setelah retry: " + " ".join(problems))


def run_script(
    paths: RunPaths, source: dict, writer: ScriptWriter, *, ratio: float, minimum_s: float, photo_ratio: float
) -> dict:
    data = generate_script(source, writer, ratio=ratio, minimum_s=minimum_s, photo_ratio=photo_ratio)
    write_json_atomic(paths.script_json, data)
    return data
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_gemini.py tests/test_script_step.py tests/test_script_rules.py -v`
Expected: semua PASS (7 test baru + 8 test lama).

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/providers/__init__.py mayzfact/providers/gemini.py mayzfact/steps/script.py tests/test_gemini.py tests/test_script_step.py
git commit -m "feat: add gemini writer and script step with one retry"
```

---

### Task 6: Timing beat dari alignment

**Files:**

- Create: `mayzfact/timing.py`
- Modify: `tests/factories.py`. Tambahin `fake_alignment`.
- Test: `tests/test_timing.py`

**Interfaces:**

- Consumes: `PipelineError` (Task 1)
- Produces:
  - `beat_offsets(texts: list[str]) -> list[int]`
  - `beat_timings(texts: list[str], alignment: dict, audio_duration_s: float) -> list[{"start_s": float, "end_s": float}]`
  - Di factories: `fake_alignment(text: str, total_s: float) -> dict`, yang ngikutin format alignment ElevenLabs.

- [ ] **Step 1: Tulis test yang gagal**

Tambahin ke `tests/factories.py`:

```python
def fake_alignment(text: str, total_s: float) -> dict:
    """Alignment ala ElevenLabs: tiap karakter dapat jatah waktu yang sama."""
    step = total_s / max(1, len(text))
    return {
        "characters": list(text),
        "character_start_times_seconds": [round(i * step, 4) for i in range(len(text))],
        "character_end_times_seconds": [round((i + 1) * step, 4) for i in range(len(text))],
    }
```

`tests/test_timing.py`:

```python
import pytest

from mayzfact.errors import PipelineError
from mayzfact.timing import beat_offsets, beat_timings
from tests.factories import fake_alignment


def test_beat_offsets():
    assert beat_offsets(["ab", "cde", "f"]) == [0, 3, 7]


def test_beat_timings_are_contiguous_and_end_at_audio():
    texts = ["Look at this.", "It is old.", "Wow."]
    alignment = fake_alignment(" ".join(texts), 1.45)
    assert beat_timings(texts, alignment, 2.0) == [
        {"start_s": 0.0, "end_s": 0.7},
        {"start_s": 0.7, "end_s": 1.25},
        {"start_s": 1.25, "end_s": 2.0},
    ]


def test_beat_timings_with_punctuation_and_apostrophes():
    texts = ["It's huge, right?", 'He said "wait" - then ran...']
    timings = beat_timings(texts, fake_alignment(" ".join(texts), 4.0), 4.5)
    assert timings[0]["start_s"] == 0.0
    assert timings[0]["end_s"] == timings[1]["start_s"]
    assert timings[1]["end_s"] == 4.5


def test_alignment_mismatch_is_an_error_that_keeps_voice():
    alignment = fake_alignment("Look at this! It is old.", 2.4)
    with pytest.raises(PipelineError, match="jangan generate ulang"):
        beat_timings(["Look at this.", "It is old."], alignment, 3.0)


def test_audio_shorter_than_last_beat_is_an_error():
    texts = ["Look at this.", "It is old."]
    with pytest.raises(PipelineError, match="Timing beat 2"):
        beat_timings(texts, fake_alignment(" ".join(texts), 2.4), 1.0)
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_timing.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.timing'`.

- [ ] **Step 3: Implementasi**

`mayzfact/timing.py`:

```python
"""Timing beat dari alignment per karakter ElevenLabs."""

from __future__ import annotations

from mayzfact.errors import PipelineError


def beat_offsets(texts: list[str]) -> list[int]:
    """Posisi karakter awal tiap beat di dalam ' '.join(texts)."""
    offsets: list[int] = []
    position = 0
    for text in texts:
        offsets.append(position)
        position += len(text) + 1
    return offsets


def beat_timings(texts: list[str], alignment: dict, audio_duration_s: float) -> list[dict]:
    """Beat pertama mulai 0.0, beat i selesai pas beat i+1 mulai, beat terakhir selesai di akhir audio."""
    full_text = " ".join(texts)
    chars = alignment["characters"]
    starts = alignment["character_start_times_seconds"]
    if len(chars) != len(full_text) or "".join(chars) != full_text or len(starts) != len(chars):
        raise PipelineError(
            "clips",
            "Alignment ElevenLabs nggak cocok sama teks naskah. voice.mp3 aman; "
            "benerin cara mapping-nya, jangan generate ulang suara.",
        )
    begins = [0.0] + [float(starts[offset]) for offset in beat_offsets(texts)[1:]]
    timings: list[dict] = []
    for index, start in enumerate(begins):
        end = begins[index + 1] if index + 1 < len(begins) else float(audio_duration_s)
        if end <= start:
            raise PipelineError("clips", f"Timing beat {index + 1} nggak valid ({start:.2f}s - {end:.2f}s).")
        timings.append({"start_s": round(start, 3), "end_s": round(end, 3)})
    return timings
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_timing.py -v`
Expected: 5 test PASS.

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/timing.py tests/factories.py tests/test_timing.py
git commit -m "feat: compute beat timings from tts alignment"
```

---

### Task 7: ffprobe + ElevenLabs + step tts

**Files:**

- Create: `mayzfact/ffmpeg.py` (baru `probe` dan `audio_duration`), `mayzfact/providers/elevenlabs.py`, `mayzfact/steps/tts.py`, `tests/conftest.py`
- Modify: `tests/factories.py`. Tambahin `stream_types`.
- Test: `tests/test_elevenlabs.py`, `tests/test_tts_step.py`

**Interfaces:**

- Consumes:
  - `request_json` (Task 4)
  - `script_text`, `text_hash` (Task 3)
  - `RunPaths`, `write_bytes_atomic`, `write_json_atomic` (Task 1)
- Produces:
  - `probe(path: Path, step: str) -> {"width": int|None, "height": int|None, "duration_s": float|None}`
  - `audio_duration(path: Path) -> float`
  - `ElevenLabsTTS(api_key, voice_id, model_id, client)`: atribut `.voice_id` dan `.model_id`, method `.synthesize(text) -> tuple[bytes, dict]`
  - `list_voices(api_key, client) -> list[{"voice_id", "name", "labels"}]`
  - Protocol `TTSProvider`
  - `run_tts(paths, script: dict, tts: TTSProvider, *, log=print, measure=audio_duration) -> dict`. Isi `tts.json`: `{"text_sha256", "voice_id", "model_id", "characters", "duration_s", "alignment"}`. `tts.json` ditulis duluan, `voice.mp3` paling akhir.
  - Fixture pytest: `sine_mp3` (3 detik), `long_mp3` (31 detik, hening), `make_video(w, h, seconds, name=None)`, `make_photo(w, h, name=None)`
  - Di factories: `stream_types(path) -> list[str]`

- [ ] **Step 1: Tulis fixture + test yang gagal**

`tests/conftest.py`:

```python
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
```

Tambahin ke `tests/factories.py`. Import `subprocess` dan `Path` taruh di blok import paling atas file:

```python
import subprocess
from pathlib import Path


def stream_types(path: Path) -> list[str]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]
```

`tests/test_elevenlabs.py`:

```python
import base64
import json

import httpx

from mayzfact.providers.elevenlabs import ElevenLabsTTS, list_voices

ALIGNMENT = {"characters": ["H", "i"], "character_start_times_seconds": [0.0, 0.1], "character_end_times_seconds": [0.1, 0.2]}


def test_synthesize_calls_with_timestamps_endpoint():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"audio_base64": base64.b64encode(b"ID3audio").decode(), "alignment": ALIGNMENT})

    tts = ElevenLabsTTS("secret", "voice123", "eleven_v3", httpx.Client(transport=httpx.MockTransport(handler)))
    audio, alignment = tts.synthesize("Hi")
    assert audio == b"ID3audio"
    assert alignment == ALIGNMENT
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/text-to-speech/voice123/with-timestamps"
    assert request.url.params["output_format"] == "mp3_44100_128"
    assert request.headers["xi-api-key"] == "secret"
    assert json.loads(request.content) == {"text": "Hi", "model_id": "eleven_v3"}


def test_list_voices_normalizes_labels():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"voices": [
            {"voice_id": "abc", "name": "Mark", "labels": {"gender": "male", "accent": "american"}},
            {"voice_id": "def", "name": "Ria", "labels": None},
        ]})

    voices = list_voices("secret", httpx.Client(transport=httpx.MockTransport(handler)))
    assert voices == [
        {"voice_id": "abc", "name": "Mark", "labels": {"gender": "male", "accent": "american"}},
        {"voice_id": "def", "name": "Ria", "labels": {}},
    ]
    assert seen[0].url.path == "/v1/voices"
    assert seen[0].headers["xi-api-key"] == "secret"
```

`tests/test_tts_step.py`:

```python
from mayzfact.steps.tts import run_tts
from mayzfact.store import RunPaths, read_json
from mayzfact.text import text_hash
from tests.factories import fake_alignment

SCRIPT = {
    "beats": [
        {"text": "Look at this.", "media": "video", "queries": ["crab"]},
        {"text": "It is old.", "media": "photo", "queries": ["fossil"]},
    ],
    "fallback_query": "animals",
}


class FakeTTS:
    voice_id = "voice123"
    model_id = "eleven_v3"

    def __init__(self, audio: bytes):
        self.audio = audio
        self.texts: list[str] = []

    def synthesize(self, text: str):
        self.texts.append(text)
        return self.audio, fake_alignment(text, 2.4)


def test_run_tts_writes_voice_and_metadata(tmp_path, sine_mp3):
    paths = RunPaths(tmp_path)
    tts = FakeTTS(sine_mp3.read_bytes())
    logs: list[str] = []
    data = run_tts(paths, SCRIPT, tts, log=logs.append)

    assert tts.texts == ["Look at this. It is old."]
    assert paths.voice_mp3.read_bytes() == sine_mp3.read_bytes()
    saved = read_json(paths.tts_json)
    assert saved == data
    assert saved["text_sha256"] == text_hash("Look at this. It is old.")
    assert saved["characters"] == 24
    assert (saved["voice_id"], saved["model_id"]) == ("voice123", "eleven_v3")
    assert abs(saved["duration_s"] - 3.0) < 0.15
    assert saved["alignment"]["characters"][0] == "L"
    assert "24 karakter" in logs[0]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["tts.json", "voice.mp3"]
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_elevenlabs.py tests/test_tts_step.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.providers.elevenlabs'`.

- [ ] **Step 3: Implementasi**

`mayzfact/ffmpeg.py`:

```python
"""Wrapper tipis ffmpeg/ffprobe."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from mayzfact.errors import PipelineError


def _run(cmd: list[str], step: str) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise PipelineError(step, f"{cmd[0]} gagal:\n{result.stderr[-1500:]}")
    return result.stdout


def probe(path: Path, step: str) -> dict:
    """Ukuran stream video pertama (kalau ada) + durasi file."""
    out = _run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(path)],
        step,
    )
    data = json.loads(out)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    duration = data.get("format", {}).get("duration")
    return {
        "width": video.get("width"),
        "height": video.get("height"),
        "duration_s": float(duration) if duration not in (None, "N/A") else None,
    }


def audio_duration(path: Path) -> float:
    duration = probe(path, "tts")["duration_s"]
    if not duration:
        raise PipelineError("tts", f"Durasi {path.name} nggak kebaca.")
    return duration
```

`mayzfact/providers/elevenlabs.py`:

```python
"""Client ElevenLabs: TTS dengan timestamp per karakter + list voice di akun."""

from __future__ import annotations

import base64

import httpx

from mayzfact.net import request_json

TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
VOICES_URL = "https://api.elevenlabs.io/v1/voices"
OUTPUT_FORMAT = "mp3_44100_128"


class ElevenLabsTTS:
    def __init__(self, api_key: str, voice_id: str, model_id: str, client: httpx.Client) -> None:
        self._api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self._client = client

    def synthesize(self, text: str) -> tuple[bytes, dict]:
        body = request_json(
            self._client,
            "POST",
            TTS_URL.format(voice_id=self.voice_id),
            step="tts",
            params={"output_format": OUTPUT_FORMAT},
            headers={"xi-api-key": self._api_key},
            json={"text": text, "model_id": self.model_id},
            timeout=180.0,
        )
        return base64.b64decode(body["audio_base64"]), body["alignment"]


def list_voices(api_key: str, client: httpx.Client) -> list[dict]:
    body = request_json(client, "GET", VOICES_URL, step="voices", headers={"xi-api-key": api_key})
    return [
        {"voice_id": v["voice_id"], "name": v.get("name", ""), "labels": v.get("labels") or {}}
        for v in body.get("voices", [])
    ]
```

`mayzfact/steps/tts.py`:

```python
"""Step tts: bikin voice.mp3 + tts.json. Cuma jalan kalau suara belum ada (aturan kunci, spec 3.4)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Protocol

from mayzfact.ffmpeg import audio_duration
from mayzfact.store import RunPaths, write_bytes_atomic, write_json_atomic
from mayzfact.text import script_text, text_hash


class TTSProvider(Protocol):
    voice_id: str
    model_id: str

    def synthesize(self, text: str) -> tuple[bytes, dict]: ...


def run_tts(
    paths: RunPaths,
    script: dict,
    tts: TTSProvider,
    *,
    log: Callable[[str], None] = print,
    measure: Callable[[Path], float] = audio_duration,
) -> dict:
    text = script_text(script["beats"])
    log(f"[tts] Kirim {len(text)} karakter ke ElevenLabs (voice {tts.voice_id}, model {tts.model_id})")
    audio, alignment = tts.synthesize(text)
    incoming = paths.root / "voice.incoming.mp3"
    write_bytes_atomic(incoming, audio)
    data = {
        "text_sha256": text_hash(text),
        "voice_id": tts.voice_id,
        "model_id": tts.model_id,
        "characters": len(text),
        "duration_s": round(measure(incoming), 3),
        "alignment": alignment,
    }
    # tts.json duluan, voice.mp3 terakhir. Keberadaan voice.mp3 = step selesai + naskah dikunci.
    write_json_atomic(paths.tts_json, data)
    os.replace(incoming, paths.voice_mp3)
    return data
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_elevenlabs.py tests/test_tts_step.py -v`
Expected: 3 test PASS.

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/ffmpeg.py mayzfact/providers/elevenlabs.py mayzfact/steps/tts.py tests/conftest.py tests/factories.py tests/test_elevenlabs.py tests/test_tts_step.py
git commit -m "feat: add elevenlabs client and tts step"
```

---

### Task 8: Aturan media (layout, ukuran, tier, rendition)

**Files:**

- Create: `mayzfact/providers/types.py`, `mayzfact/media.py`
- Modify: `tests/factories.py`. Tambahin `cand`.
- Test: `tests/test_media.py`

**Interfaces:**

- Consumes: —
- Produces:
  - `Rendition(url: str, width: int, height: int)`
  - `Candidate(provider: str, id: str, kind: str, duration_s: float | None, page_url: str, author: str, renditions: tuple[Rendition, ...], rank: int)`
  - Konstanta: `FRAME_W=1080`, `FRAME_H=1920`, `FULL_MAX_ASPECT=0.75`, `PHOTO_ZOOM=1.08`.
  - Fungsi di `media.py`:
    - `layout_for(width, height) -> "full" | "blur"`
    - `fg_height(width, height, fg_min_ratio) -> int`
    - `needed_scale(width, height, fg_min_ratio, zoom=1.0) -> float`
    - `zoom_for(kind) -> float`
    - `best_rendition(candidate) -> Rendition`
    - `tier(candidate, fg_min_ratio) -> 1 | 2 | 3`
    - `pick_rendition(candidate, fg_min_ratio) -> Rendition`
    - `downscale_factor(width, height, fg_min_ratio, zoom=1.0) -> float`
  - Di factories: `cand(provider, id, kind="video", width=1080, height=1920, duration_s=20.0, rank=0, url=None) -> Candidate`

- [ ] **Step 1: Tulis test yang gagal**

Tambahin ke `tests/factories.py`. Import-nya taruh di blok import paling atas file:

```python
from mayzfact.providers.types import Candidate, Rendition


def cand(
    provider: str,
    id: str,
    kind: str = "video",
    width: int = 1080,
    height: int = 1920,
    duration_s: float | None = 20.0,
    rank: int = 0,
    url: str | None = None,
) -> Candidate:
    ext = "mp4" if kind == "video" else "jpg"
    return Candidate(
        provider=provider,
        id=id,
        kind=kind,
        duration_s=duration_s if kind == "video" else None,
        page_url=f"https://{provider}.test/{id}",
        author="tester",
        renditions=(Rendition(url or f"https://cdn.test/{provider}_{id}.{ext}", width, height),),
        rank=rank,
    )
```

`tests/test_media.py`:

```python
import pytest

from mayzfact.media import downscale_factor, fg_height, layout_for, needed_scale, pick_rendition, tier
from mayzfact.providers.types import Candidate, Rendition
from tests.factories import cand


@pytest.mark.parametrize(
    ("width", "height", "layout"),
    [(1080, 1920, "full"), (1440, 1920, "full"), (1080, 1350, "blur"), (1920, 1080, "blur"), (1000, 1000, "blur")],
)
def test_layout_for(width, height, layout):
    assert layout_for(width, height) == layout


@pytest.mark.parametrize(
    ("width", "height", "ratio", "expected"),
    [(1920, 1080, 0.5, 960), (1080, 1080, 0.5, 1080), (1440, 1080, 0.5, 960), (1920, 1080, 0.4, 768), (1080, 1350, 0.5, 1350)],
)
def test_fg_height(width, height, ratio, expected):
    assert fg_height(width, height, ratio) == expected


def test_needed_scale():
    assert needed_scale(2160, 3840, 0.5) == 0.5
    assert needed_scale(1080, 1920, 0.5) == 1.0
    assert needed_scale(1920, 1080, 0.5) == pytest.approx(0.8889, abs=1e-4)
    assert needed_scale(1280, 720, 0.5) == pytest.approx(1.3333, abs=1e-4)
    assert needed_scale(1080, 1920, 0.5, zoom=1.08) == pytest.approx(1.08)


def test_tier():
    assert tier(cand("pexels", "a", width=2160, height=3840), 0.5) == 1
    assert tier(cand("pexels", "b", width=1920, height=1080), 0.5) == 2
    assert tier(cand("pexels", "c", width=1280, height=720), 0.5) == 3
    assert tier(cand("pexels", "d", kind="photo", width=3000, height=4500), 0.5) == 1
    assert tier(cand("pixabay", "e", kind="photo", width=1280, height=853), 0.5) == 3


def _video(*sizes):
    return Candidate(
        provider="pexels", id="1", kind="video", duration_s=10.0, page_url="", author="", rank=0,
        renditions=tuple(Rendition(f"https://cdn.test/{w}x{h}.mp4", w, h) for w, h in sizes),
    )


def test_pick_rendition_takes_smallest_sharp_one():
    assert pick_rendition(_video((3840, 2160), (1920, 1080), (1280, 720)), 0.5).width == 1920
    assert pick_rendition(_video((2160, 3840), (1080, 1920), (720, 1280)), 0.5).height == 1920


def test_pick_rendition_falls_back_to_largest():
    assert pick_rendition(_video((640, 360), (960, 540)), 0.5).width == 960


def test_downscale_factor_never_upscales():
    assert downscale_factor(3840, 2160, 0.5) == pytest.approx(0.4444, abs=1e-4)
    assert downscale_factor(720, 1280, 0.5) == 1.0
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_media.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.providers.types'`.

- [ ] **Step 3: Implementasi**

`mayzfact/providers/types.py`:

```python
"""Tipe hasil search stock yang sama buat semua provider."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rendition:
    url: str
    width: int
    height: int


@dataclass(frozen=True)
class Candidate:
    provider: str  # "pexels" | "pixabay"
    id: str
    kind: str  # "video" | "photo"
    duration_s: float | None  # None buat foto
    page_url: str
    author: str
    renditions: tuple[Rendition, ...]
    rank: int  # posisi di hasil search provider (0 = paling relevan)
```

`mayzfact/media.py`:

```python
"""Aturan layout (full/blur), ukuran yang dibutuhin, tier kualitas, dan pilihan rendition."""

from __future__ import annotations

from mayzfact.providers.types import Candidate, Rendition

FRAME_W = 1080
FRAME_H = 1920
FULL_MAX_ASPECT = 0.75
PHOTO_ZOOM = 1.08


def layout_for(width: int, height: int) -> str:
    return "full" if width / height <= FULL_MAX_ASPECT else "blur"


def fg_height(width: int, height: int, fg_min_ratio: float) -> int:
    """Tinggi kotak foreground layout blur: tinggi natural selebar 1080, min fg_min_ratio × 1920, max 1920."""
    natural = round(FRAME_W * height / width)
    return min(FRAME_H, max(natural, round(fg_min_ratio * FRAME_H)))


def needed_scale(width: int, height: int, fg_min_ratio: float, zoom: float = 1.0) -> float:
    """Skala media waktu tampil. Kalau > 1, media bakal di-upscale (kurang tajam)."""
    if layout_for(width, height) == "full":
        scale = max(FRAME_W / width, FRAME_H / height)
    else:
        scale = max(FRAME_W / width, fg_min_ratio * FRAME_H / height)
    return scale * zoom


def zoom_for(kind: str) -> float:
    return PHOTO_ZOOM if kind == "photo" else 1.0


def best_rendition(candidate: Candidate) -> Rendition:
    return max(candidate.renditions, key=lambda r: r.width * r.height)


def tier(candidate: Candidate, fg_min_ratio: float) -> int:
    best = best_rendition(candidate)
    if needed_scale(best.width, best.height, fg_min_ratio, zoom_for(candidate.kind)) > 1.0:
        return 3
    return 1 if layout_for(best.width, best.height) == "full" else 2


def pick_rendition(candidate: Candidate, fg_min_ratio: float) -> Rendition:
    """Rendition terkecil yang masih tajam. Kalau nggak ada yang tajam, ambil yang terbesar."""
    zoom = zoom_for(candidate.kind)
    sharp = [r for r in candidate.renditions if needed_scale(r.width, r.height, fg_min_ratio, zoom) <= 1.0]
    if sharp:
        return min(sharp, key=lambda r: r.width * r.height)
    return best_rendition(candidate)


def downscale_factor(width: int, height: int, fg_min_ratio: float, zoom: float = 1.0) -> float:
    """Faktor resize buat normalisasi. Cuma ngecilin, nggak pernah ngegedein."""
    return min(1.0, needed_scale(width, height, fg_min_ratio, zoom))
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_media.py -v`
Expected: 15 test PASS.

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/providers/types.py mayzfact/media.py tests/factories.py tests/test_media.py
git commit -m "feat: add layout, tier and rendition rules"
```

---

### Task 9: Provider Pexels + Pixabay + gabungan search

**Files:**

- Create: `mayzfact/providers/pexels.py`, `mayzfact/providers/pixabay.py`, `mayzfact/providers/stock.py`
- Test: `tests/test_stock_providers.py`

**Interfaces:**

- Consumes:
  - `request_json` (Task 4)
  - `SearchCache` (Task 4)
  - `Candidate`, `Rendition` (Task 8)
- Produces:
  - `Pexels(api_key, client, cache)` dengan `.videos(query, orientation=None) -> list[Candidate]` dan `.photos(query, orientation=None) -> list[Candidate]`. Parser-nya `parse_video(item, rank)` dan `parse_photo(item, rank)`.
  - `Pixabay(api_key, client, cache)` dengan `.videos(query)` dan `.photos(query)`. Parser-nya `parse_video(hit, rank)` dan `parse_photo(hit, rank)`.
  - `merge_candidates(lists) -> list[Candidate]`, yang buang duplikat provider+id dan nyimpen kemunculan pertama.
  - `StockSearch(pexels, pixabay).candidates(kind, query) -> list[Candidate]`. Urutannya:
    - video: Pexels portrait → Pexels semua orientasi → Pixabay
    - foto: Pexels portrait → Pexels semua orientasi → Pixabay

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_stock_providers.py`:

```python
import httpx

from mayzfact.cache import SearchCache
from mayzfact.providers import pexels as pexels_mod
from mayzfact.providers import pixabay as pixabay_mod
from mayzfact.providers.pexels import Pexels
from mayzfact.providers.pixabay import Pixabay
from mayzfact.providers.stock import StockSearch, merge_candidates
from tests.factories import cand

PEXELS_VIDEO = {
    "id": 101, "width": 2160, "height": 3840, "url": "https://www.pexels.com/video/crab-101/", "duration": 12,
    "user": {"id": 5, "name": "Ana", "url": "https://www.pexels.com/@ana"},
    "video_files": [
        {"id": 1, "quality": "hd", "file_type": "video/mp4", "width": 1080, "height": 1920, "fps": 30, "link": "https://videos.pexels.com/101-hd.mp4"},
        {"id": 2, "quality": "uhd", "file_type": "video/mp4", "width": 2160, "height": 3840, "fps": 30, "link": "https://videos.pexels.com/101-uhd.mp4"},
        {"id": 3, "quality": None, "file_type": "application/x-mpegURL", "width": None, "height": None, "fps": None, "link": "https://videos.pexels.com/101.m3u8"},
    ],
}
PEXELS_PHOTO = {
    "id": 202, "width": 3000, "height": 4500, "url": "https://www.pexels.com/photo/fossil-202/",
    "photographer": "Budi", "src": {"original": "https://images.pexels.com/photos/202/pexels-photo-202.jpeg"},
}
PIXABAY_VIDEO = {
    "id": 303, "pageURL": "https://pixabay.com/videos/id-303/", "duration": 15, "user": "citra",
    "videos": {
        "large": {"url": "", "width": 0, "height": 0, "size": 0},
        "medium": {"url": "https://cdn.pixabay.com/303-medium.mp4", "width": 1920, "height": 1080, "size": 100},
        "small": {"url": "https://cdn.pixabay.com/303-small.mp4", "width": 1280, "height": 720, "size": 50},
    },
}
PIXABAY_PHOTO = {"id": 404, "pageURL": "https://pixabay.com/photos/id-404/", "user": "dewi", "largeImageURL": "https://pixabay.com/get/404_1280.jpg", "imageWidth": 6000, "imageHeight": 4000}


def recording_client(body):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler)), requests


def cache_text(root):
    return "".join(p.read_text(encoding="utf-8") for p in root.rglob("*.json"))


def test_pexels_parse_video_skips_non_mp4_files():
    c = pexels_mod.parse_video(PEXELS_VIDEO, 3)
    assert (c.provider, c.id, c.kind, c.duration_s, c.author, c.rank) == ("pexels", "101", "video", 12.0, "Ana", 3)
    assert [(r.width, r.height) for r in c.renditions] == [(1080, 1920), (2160, 3840)]
    assert pexels_mod.parse_video({**PEXELS_VIDEO, "video_files": [PEXELS_VIDEO["video_files"][2]]}, 0) is None


def test_pexels_parse_photo_needs_original_src():
    c = pexels_mod.parse_photo(PEXELS_PHOTO, 0)
    assert (c.kind, c.author, c.renditions[0].width, c.renditions[0].height) == ("photo", "Budi", 3000, 4500)
    assert pexels_mod.parse_photo({**PEXELS_PHOTO, "src": {}}, 0) is None


def test_pexels_search_sends_key_and_uses_cache(tmp_path):
    client, requests = recording_client({"videos": [PEXELS_VIDEO]})
    pexels = Pexels("pexels-key", client, SearchCache(tmp_path))
    first = pexels.videos("horseshoe crab", "portrait")
    second = pexels.videos("horseshoe crab", "portrait")
    assert [c.id for c in first] == [c.id for c in second] == ["101"]
    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == "/v1/videos/search"
    assert request.headers["Authorization"] == "pexels-key"
    assert dict(request.url.params) == {"query": "horseshoe crab", "per_page": "30", "orientation": "portrait"}
    assert "pexels-key" not in cache_text(tmp_path)


def test_pixabay_parse_video_skips_empty_renditions():
    c = pixabay_mod.parse_video(PIXABAY_VIDEO, 0)
    assert [(r.width, r.height) for r in c.renditions] == [(1920, 1080), (1280, 720)]
    assert pixabay_mod.parse_video({**PIXABAY_VIDEO, "videos": {"large": {"url": "", "width": 0, "height": 0}}}, 0) is None


def test_pixabay_parse_photo_uses_large_image_size():
    c = pixabay_mod.parse_photo(PIXABAY_PHOTO, 0)
    assert (c.renditions[0].width, c.renditions[0].height) == (1280, 853)
    assert pixabay_mod.parse_photo({**PIXABAY_PHOTO, "largeImageURL": ""}, 0) is None


def test_pixabay_search_truncates_query_and_hides_key_from_cache(tmp_path):
    client, requests = recording_client({"hits": [PIXABAY_PHOTO]})
    pixabay = Pixabay("pixabay-key", client, SearchCache(tmp_path))
    long_query = "horseshoe crab " * 10
    photos = pixabay.photos(long_query)
    assert [c.id for c in photos] == ["404"]
    params = requests[0].url.params
    assert requests[0].url.path == "/api/"
    assert params["key"] == "pixabay-key"
    assert params["q"] == long_query[:100]
    assert params["image_type"] == "photo"
    assert "pixabay-key" not in cache_text(tmp_path)


def test_pixabay_videos_use_film_type(tmp_path):
    client, requests = recording_client({"hits": [PIXABAY_VIDEO]})
    Pixabay("k", client, SearchCache(tmp_path)).videos("crab")
    assert requests[0].url.path == "/api/videos/"
    assert requests[0].url.params["video_type"] == "film"


def test_merge_candidates_keeps_first_occurrence():
    a = cand("pexels", "1", rank=0)
    a_again = cand("pexels", "1", rank=7)
    b = cand("pixabay", "1", rank=0)
    assert merge_candidates([[a], [a_again, b]]) == [a, b]


def test_stock_search_order_for_videos_and_photos():
    calls = []

    class FakePexels:
        def videos(self, query, orientation=None):
            calls.append(("pexels-videos", query, orientation))
            return [cand("pexels", "p" if orientation else "any")]

        def photos(self, query, orientation=None):
            calls.append(("pexels-photos", query, orientation))
            return [cand("pexels", "pp" if orientation else "pany", kind="photo")]

    class FakePixabay:
        def videos(self, query):
            calls.append(("pixabay-videos", query, None))
            return [cand("pixabay", "x")]

        def photos(self, query):
            calls.append(("pixabay-photos", query, None))
            return [cand("pixabay", "xp", kind="photo")]

    search = StockSearch(FakePexels(), FakePixabay())
    assert [c.id for c in search.candidates("video", "crab")] == ["p", "any", "x"]
    assert [c.id for c in search.candidates("photo", "crab")] == ["pp", "pany", "xp"]
    assert calls == [
        ("pexels-videos", "crab", "portrait"), ("pexels-videos", "crab", None), ("pixabay-videos", "crab", None),
        ("pexels-photos", "crab", "portrait"), ("pexels-photos", "crab", None), ("pixabay-photos", "crab", None),
    ]
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_stock_providers.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.providers.pexels'`.

- [ ] **Step 3: Implementasi**

`mayzfact/providers/pexels.py`:

```python
"""Search Pexels (video + foto) → Candidate."""

from __future__ import annotations

import httpx

from mayzfact.cache import SearchCache
from mayzfact.net import request_json
from mayzfact.providers.types import Candidate, Rendition

VIDEO_URL = "https://api.pexels.com/v1/videos/search"
PHOTO_URL = "https://api.pexels.com/v1/search"
PER_PAGE = 30


def parse_video(item: dict, rank: int) -> Candidate | None:
    renditions = tuple(
        Rendition(f["link"], int(f["width"]), int(f["height"]))
        for f in item.get("video_files") or []
        if f.get("link") and f.get("width") and f.get("height") and f.get("file_type") == "video/mp4"
    )
    if not renditions:
        return None
    return Candidate(
        provider="pexels",
        id=str(item["id"]),
        kind="video",
        duration_s=float(item.get("duration") or 0),
        page_url=item.get("url", ""),
        author=(item.get("user") or {}).get("name", ""),
        renditions=renditions,
        rank=rank,
    )


def parse_photo(item: dict, rank: int) -> Candidate | None:
    src = (item.get("src") or {}).get("original")
    width, height = int(item.get("width") or 0), int(item.get("height") or 0)
    if not src or not width or not height:
        return None
    return Candidate(
        provider="pexels",
        id=str(item["id"]),
        kind="photo",
        duration_s=None,
        page_url=item.get("url", ""),
        author=item.get("photographer", ""),
        renditions=(Rendition(src, width, height),),
        rank=rank,
    )


class Pexels:
    def __init__(self, api_key: str, client: httpx.Client, cache: SearchCache) -> None:
        self._api_key = api_key
        self._client = client
        self._cache = cache

    def _search(self, url: str, query: str, orientation: str | None) -> dict:
        params: dict[str, object] = {"query": query, "per_page": PER_PAGE}
        if orientation:
            params["orientation"] = orientation
        cache_key = {"url": url, **params}
        cached = self._cache.get("pexels", cache_key)
        if cached is not None:
            return cached
        body = request_json(self._client, "GET", url, step="clips", params=params, headers={"Authorization": self._api_key})
        self._cache.put("pexels", cache_key, body)
        return body

    def videos(self, query: str, orientation: str | None = None) -> list[Candidate]:
        items = self._search(VIDEO_URL, query, orientation).get("videos") or []
        return [c for rank, item in enumerate(items) if (c := parse_video(item, rank)) is not None]

    def photos(self, query: str, orientation: str | None = None) -> list[Candidate]:
        items = self._search(PHOTO_URL, query, orientation).get("photos") or []
        return [c for rank, item in enumerate(items) if (c := parse_photo(item, rank)) is not None]
```

`mayzfact/providers/pixabay.py`:

```python
"""Search Pixabay (video + foto) → Candidate."""

from __future__ import annotations

import httpx

from mayzfact.cache import SearchCache
from mayzfact.net import request_json
from mayzfact.providers.types import Candidate, Rendition

VIDEO_URL = "https://pixabay.com/api/videos/"
PHOTO_URL = "https://pixabay.com/api/"
PER_PAGE = 30
MAX_QUERY_CHARS = 100
LARGE_IMAGE_MAX = 1280  # largeImageURL maksimal 1280px tanpa full API access


def parse_video(hit: dict, rank: int) -> Candidate | None:
    renditions = tuple(
        Rendition(r["url"], int(r["width"]), int(r["height"]))
        for r in (hit.get("videos") or {}).values()
        if r.get("url") and r.get("width") and r.get("height")
    )
    if not renditions:
        return None
    return Candidate(
        provider="pixabay",
        id=str(hit["id"]),
        kind="video",
        duration_s=float(hit.get("duration") or 0),
        page_url=hit.get("pageURL", ""),
        author=hit.get("user", ""),
        renditions=renditions,
        rank=rank,
    )


def parse_photo(hit: dict, rank: int) -> Candidate | None:
    url = hit.get("largeImageURL")
    width, height = int(hit.get("imageWidth") or 0), int(hit.get("imageHeight") or 0)
    if not url or not width or not height:
        return None
    scale = min(1.0, LARGE_IMAGE_MAX / max(width, height))
    return Candidate(
        provider="pixabay",
        id=str(hit["id"]),
        kind="photo",
        duration_s=None,
        page_url=hit.get("pageURL", ""),
        author=hit.get("user", ""),
        renditions=(Rendition(url, round(width * scale), round(height * scale)),),
        rank=rank,
    )


class Pixabay:
    def __init__(self, api_key: str, client: httpx.Client, cache: SearchCache) -> None:
        self._api_key = api_key
        self._client = client
        self._cache = cache

    def _search(self, url: str, query: str, extra: dict) -> dict:
        params = {"q": query[:MAX_QUERY_CHARS], "per_page": PER_PAGE, "safesearch": "true", **extra}
        cache_key = {"url": url, **params}
        cached = self._cache.get("pixabay", cache_key)
        if cached is not None:
            return cached
        body = request_json(self._client, "GET", url, step="clips", params={"key": self._api_key, **params})
        self._cache.put("pixabay", cache_key, body)
        return body

    def videos(self, query: str) -> list[Candidate]:
        hits = self._search(VIDEO_URL, query, {"video_type": "film"}).get("hits") or []
        return [c for rank, hit in enumerate(hits) if (c := parse_video(hit, rank)) is not None]

    def photos(self, query: str) -> list[Candidate]:
        hits = self._search(PHOTO_URL, query, {"image_type": "photo"}).get("hits") or []
        return [c for rank, hit in enumerate(hits) if (c := parse_photo(hit, rank)) is not None]
```

`mayzfact/providers/stock.py`:

```python
"""Gabungin hasil Pexels + Pixabay buat 1 query."""

from __future__ import annotations

from mayzfact.providers.pexels import Pexels
from mayzfact.providers.pixabay import Pixabay
from mayzfact.providers.types import Candidate


def merge_candidates(lists: list[list[Candidate]]) -> list[Candidate]:
    seen: set[tuple[str, str]] = set()
    merged: list[Candidate] = []
    for items in lists:
        for candidate in items:
            key = (candidate.provider, candidate.id)
            if key not in seen:
                seen.add(key)
                merged.append(candidate)
    return merged


class StockSearch:
    def __init__(self, pexels: Pexels, pixabay: Pixabay) -> None:
        self.pexels = pexels
        self.pixabay = pixabay

    def candidates(self, kind: str, query: str) -> list[Candidate]:
        if kind == "video":
            lists = [self.pexels.videos(query, "portrait"), self.pexels.videos(query), self.pixabay.videos(query)]
        else:
            lists = [self.pexels.photos(query, "portrait"), self.pexels.photos(query), self.pixabay.photos(query)]
        return merge_candidates(lists)
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_stock_providers.py -v`
Expected: 9 test PASS.

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/providers/pexels.py mayzfact/providers/pixabay.py mayzfact/providers/stock.py tests/test_stock_providers.py
git commit -m "feat: add pexels and pixabay search with cache"
```

---

### Task 10: Milih klip per shot

**Files:**

- Create: `mayzfact/steps/clips.py`. Isinya bagian seleksi dulu, bagian download menyusul di Task 11.
- Test: `tests/test_clip_selection.py`

**Interfaces:**

- Consumes:
  - `Candidate` (Task 8)
  - `tier` (Task 8)
  - `PipelineError` (Task 1)
- Produces:
  - `ShotSlot(index: int, beat: int, start_s: float, end_s: float, media: str)`, dengan property `.duration_s`.
  - `split_shots(timings: list[dict], beats: list[dict], max_shot_s: float) -> list[ShotSlot]`
  - Protocol `MediaSearch` dengan method `candidates(kind, query) -> list[Candidate]`.
  - Konstanta `PROVIDER_ORDER` dan `MIN_EXTRA_S = 0.5`.
  - `choose_candidate(candidates, used, min_duration_s, fg_min_ratio) -> Candidate | None`
  - `pick_for_slot(slot, beat, fallback_query, search, used, fg_min_ratio) -> tuple[Candidate, str]`
  - `select_clips(slots, beats, fallback_query, search, fg_min_ratio) -> list[tuple[ShotSlot, Candidate, str]]`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_clip_selection.py`:

```python
import pytest

from mayzfact.errors import PipelineError
from mayzfact.steps.clips import ShotSlot, choose_candidate, pick_for_slot, select_clips, split_shots
from tests.factories import cand


class FakeSearch:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def candidates(self, kind, query):
        self.calls.append((kind, query))
        return list(self.results.get((kind, query), []))


def test_split_shots_respects_max_duration_and_media():
    timings = [{"start_s": 0.0, "end_s": 2.4}, {"start_s": 2.4, "end_s": 6.4}, {"start_s": 6.4, "end_s": 7.0}]
    beats = [{"media": "video"}, {"media": "photo"}, {"media": "video"}]
    slots = split_shots(timings, beats, 2.5)
    assert [(s.index, s.beat, s.start_s, s.end_s, s.media) for s in slots] == [
        (0, 0, 0.0, 2.4, "video"),
        (1, 1, 2.4, 4.4, "photo"),
        (2, 1, 4.4, 6.4, "photo"),
        (3, 2, 6.4, 7.0, "video"),
    ]


def test_split_shots_exact_multiple_is_not_split_further():
    slots = split_shots([{"start_s": 0.0, "end_s": 5.0}], [{"media": "video"}], 2.5)
    assert [(s.start_s, s.end_s) for s in slots] == [(0.0, 2.5), (2.5, 5.0)]


def test_choose_prefers_tier_then_rank_then_pexels():
    landscape_top = cand("pexels", "a", width=1920, height=1080, rank=0)
    portrait_lower = cand("pexels", "b", width=1080, height=1920, rank=5)
    assert choose_candidate([landscape_top, portrait_lower], set(), 2.0, 0.5) is portrait_lower
    pixabay_first = cand("pixabay", "x", rank=0)
    pexels_same_rank = cand("pexels", "y", rank=0)
    assert choose_candidate([pixabay_first, pexels_same_rank], set(), 2.0, 0.5) is pexels_same_rank


def test_choose_skips_used_and_short_videos_but_not_photos():
    used = cand("pexels", "used")
    short = cand("pexels", "short", duration_s=2.0)
    photo = cand("pexels", "photo", kind="photo")
    assert choose_candidate([used, short], {("pexels", "used")}, 2.9, 0.5) is None
    assert choose_candidate([short, photo], set(), 2.9, 0.5) is photo


def slot(media="video", start=0.0, end=2.0, beat=0):
    return ShotSlot(index=0, beat=beat, start_s=start, end_s=end, media=media)


BEAT = {"text": "Look at this crab.", "media": "video", "queries": ["horseshoe crab", "crab beach"]}


def test_pick_uses_next_query_when_first_is_empty():
    second = cand("pexels", "2")
    search = FakeSearch({("video", "crab beach"): [second]})
    assert pick_for_slot(slot(), BEAT, "animals", search, set(), 0.5) == (second, "crab beach")
    assert search.calls == [("video", "horseshoe crab"), ("video", "crab beach")]


def test_pick_falls_back_to_other_media_then_fallback_query():
    photo = cand("pexels", "p", kind="photo")
    assert pick_for_slot(slot(), BEAT, "animals", FakeSearch({("photo", "horseshoe crab"): [photo]}), set(), 0.5) == (photo, "horseshoe crab")
    generic = cand("pexels", "g")
    assert pick_for_slot(slot(), BEAT, "animals", FakeSearch({("video", "animals"): [generic]}), set(), 0.5) == (generic, "animals")


def test_pick_raises_when_nothing_found():
    with pytest.raises(PipelineError, match="Beat 1"):
        pick_for_slot(slot(), BEAT, "animals", FakeSearch({}), set(), 0.5)


def test_select_clips_never_reuses_a_clip():
    a, b = cand("pexels", "a", rank=0), cand("pexels", "b", rank=1)
    search = FakeSearch({("video", "horseshoe crab"): [a, b]})
    slots = [slot(start=0.0, end=2.0), ShotSlot(index=1, beat=0, start_s=2.0, end_s=4.0, media="video")]
    picks = select_clips(slots, [BEAT], "animals", search, 0.5)
    assert [(s.index, c.id) for s, c, _ in picks] == [(0, "a"), (1, "b")]
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_clip_selection.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.steps.clips'`.

- [ ] **Step 3: Implementasi**

`mayzfact/steps/clips.py`:

```python
"""Step clips: pecah beat jadi shot, pilih klip stock per shot, download + normalisasi."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from mayzfact.errors import PipelineError
from mayzfact.media import tier
from mayzfact.providers.types import Candidate

PROVIDER_ORDER = {"pexels": 0, "pixabay": 1}
MIN_EXTRA_S = 0.5


@dataclass(frozen=True)
class ShotSlot:
    index: int
    beat: int
    start_s: float
    end_s: float
    media: str

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


class MediaSearch(Protocol):
    def candidates(self, kind: str, query: str) -> list[Candidate]: ...


def split_shots(timings: list[dict], beats: list[dict], max_shot_s: float) -> list[ShotSlot]:
    slots: list[ShotSlot] = []
    for beat_index, (timing, beat) in enumerate(zip(timings, beats, strict=True)):
        start, end = timing["start_s"], timing["end_s"]
        count = max(1, math.ceil((end - start) / max_shot_s - 1e-9))
        step = (end - start) / count
        for k in range(count):
            shot_start = start + k * step
            shot_end = end if k == count - 1 else start + (k + 1) * step
            slots.append(ShotSlot(len(slots), beat_index, round(shot_start, 3), round(shot_end, 3), beat["media"]))
    return slots


def choose_candidate(
    candidates: list[Candidate], used: set[tuple[str, str]], min_duration_s: float, fg_min_ratio: float
) -> Candidate | None:
    usable = [
        c
        for c in candidates
        if (c.provider, c.id) not in used
        and c.renditions
        and (c.kind == "photo" or (c.duration_s or 0) >= min_duration_s)
    ]
    if not usable:
        return None
    return min(usable, key=lambda c: (tier(c, fg_min_ratio), c.rank, PROVIDER_ORDER.get(c.provider, 9)))


def pick_for_slot(
    slot: ShotSlot,
    beat: dict,
    fallback_query: str,
    search: MediaSearch,
    used: set[tuple[str, str]],
    fg_min_ratio: float,
) -> tuple[Candidate, str]:
    other = "photo" if slot.media == "video" else "video"
    attempts = (
        [(slot.media, q) for q in beat["queries"]]
        + [(other, q) for q in beat["queries"]]
        + [(slot.media, fallback_query), (other, fallback_query)]
    )
    min_duration = slot.duration_s + MIN_EXTRA_S
    for kind, query in attempts:
        found = choose_candidate(search.candidates(kind, query), used, min_duration, fg_min_ratio)
        if found is not None:
            return found, query
    raise PipelineError(
        "clips",
        f'Beat {slot.beat + 1} ("{beat["text"][:50]}") nggak dapet klip video/foto sama sekali, termasuk pakai fallback_query.',
    )


def select_clips(
    slots: list[ShotSlot], beats: list[dict], fallback_query: str, search: MediaSearch, fg_min_ratio: float
) -> list[tuple[ShotSlot, Candidate, str]]:
    used: set[tuple[str, str]] = set()
    picks: list[tuple[ShotSlot, Candidate, str]] = []
    for slot in slots:
        candidate, query = pick_for_slot(slot, beats[slot.beat], fallback_query, search, used, fg_min_ratio)
        used.add((candidate.provider, candidate.id))
        picks.append((slot, candidate, query))
    return picks
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_clip_selection.py -v`
Expected: 8 test PASS.

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/steps/clips.py tests/test_clip_selection.py
git commit -m "feat: add shot splitting and clip selection"
```

---

### Task 11: Normalisasi media + step clips lengkap

**Files:**

- Modify: `mayzfact/ffmpeg.py`. Tambahin `normalize_video`.
- Create: `mayzfact/photo.py`
- Modify: `mayzfact/steps/clips.py`. Tambahin `materialize` dan `run_clips`.
- Test: `tests/test_normalize.py`, `tests/test_clips_step.py`

**Interfaces:**

- Consumes:
  - `download` (Task 4)
  - `beat_timings` (Task 6)
  - `beat_texts` (Task 3)
  - `pick_rendition`, `downscale_factor`, `PHOTO_ZOOM` (Task 8)
  - `probe` (Task 7)
  - seleksi klip (Task 10)
  - `RunPaths`, `write_json_atomic`, `tmp_path_for` (Task 1)
- Produces:
  - `normalize_video(src, dest, *, start_s, duration_s, scale) -> None`
  - `normalize_photo(src, dest, *, fg_min_ratio) -> tuple[int, int]`
  - `materialize(slot, candidate, query, paths, client, media_cache, fg_min_ratio) -> dict`
  - `run_clips(paths, script, tts, search, client, *, max_shot_s, fg_min_ratio, media_cache, log=print) -> dict`

  Format `clips.json`: `{"shots": [{"index", "beat", "start_s", "end_s", "kind", "file", "width", "height", "provider", "provider_id", "page_url", "author", "query"}]}`. Nilai `file` relatif ke folder run dan pakai `/`.

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_normalize.py`:

```python
from PIL import Image

from mayzfact.ffmpeg import normalize_video, probe
from mayzfact.media import downscale_factor
from mayzfact.photo import normalize_photo
from tests.factories import stream_types


def test_normalize_video_downscales_trims_and_drops_audio(tmp_path, make_video):
    src = make_video(1440, 2560, 3.0)
    dest = tmp_path / "clips" / "shot_01.mp4"
    normalize_video(src, dest, start_s=0.5, duration_s=2.0, scale=downscale_factor(1440, 2560, 0.5))
    info = probe(dest, "clips")
    assert (info["width"], info["height"]) == (1080, 1920)
    assert abs(info["duration_s"] - 2.0) < 0.1
    assert stream_types(dest) == ["video"]
    assert sorted(p.name for p in dest.parent.iterdir()) == ["shot_01.mp4"]


def test_normalize_photo_applies_exif_rotation(tmp_path):
    src = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: putar 90 derajat searah jarum jam
    Image.new("RGB", (1200, 800), "red").save(src, exif=exif)
    dest = tmp_path / "shot_02.jpg"
    assert normalize_photo(src, dest, fg_min_ratio=0.5) == (800, 1200)
    with Image.open(dest) as img:
        assert img.size == (800, 1200)


def test_normalize_photo_only_downscales(tmp_path):
    big = tmp_path / "big.jpg"
    Image.new("RGB", (3000, 4500), "blue").save(big)
    assert normalize_photo(big, tmp_path / "a.jpg", fg_min_ratio=0.5) == (1382, 2074)
    small = tmp_path / "small.jpg"
    Image.new("RGB", (640, 480), "green").save(small)
    assert normalize_photo(small, tmp_path / "b.jpg", fg_min_ratio=0.5) == (640, 480)
```

`tests/test_clips_step.py`:

```python
import httpx

from mayzfact.ffmpeg import probe
from mayzfact.steps.clips import run_clips
from mayzfact.store import RunPaths, read_json
from tests.factories import cand, fake_alignment

SCRIPT = {
    "beats": [
        {"text": "Look at this.", "media": "video", "queries": ["crab"]},
        {"text": "It is old.", "media": "photo", "queries": ["fossil"]},
    ],
    "fallback_query": "animals",
}
TTS = {"duration_s": 3.0, "alignment": fake_alignment("Look at this. It is old.", 2.4)}


class FakeSearch:
    def candidates(self, kind, query):
        if (kind, query) == ("video", "crab"):
            return [cand("pexels", "v1", "video", 1080, 1920, duration_s=10.0, url="https://cdn.test/v1.mp4")]
        if (kind, query) == ("photo", "fossil"):
            return [cand("pixabay", "p1", "photo", 1600, 1000, url="https://cdn.test/p1.jpg")]
        return []


def test_run_clips_downloads_normalizes_and_writes_credits(tmp_path, make_video, make_photo):
    files = {"/v1.mp4": make_video(1080, 1920, 5.0).read_bytes(), "/p1.jpg": make_photo(1600, 1000).read_bytes()}
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=files[request.url.path])))
    paths = RunPaths(tmp_path / "run")
    paths.clips_dir.mkdir(parents=True)
    (paths.clips_dir / "shot_09.mp4").write_bytes(b"sisa run lama")

    data = run_clips(
        paths, SCRIPT, TTS, FakeSearch(), client,
        max_shot_s=2.5, fg_min_ratio=0.5, media_cache=tmp_path / "media", log=lambda message: None,
    )

    assert read_json(paths.clips_json) == data
    first, second = data["shots"]
    assert first == {
        "index": 0, "beat": 0, "start_s": 0.0, "end_s": 1.4, "kind": "video", "file": "clips/shot_01.mp4",
        "width": 1080, "height": 1920, "provider": "pexels", "provider_id": "v1",
        "page_url": "https://pexels.test/v1", "author": "tester", "query": "crab",
    }
    assert (second["file"], second["kind"], second["width"], second["height"]) == ("clips/shot_02.jpg", "photo", 1600, 1000)
    assert (second["start_s"], second["end_s"], second["provider"]) == (1.4, 3.0, "pixabay")
    assert abs(probe(paths.clips_dir / "shot_01.mp4", "clips")["duration_s"] - 1.6) < 0.1
    assert sorted(p.name for p in paths.clips_dir.iterdir()) == ["shot_01.mp4", "shot_02.jpg"]
    assert len(list((tmp_path / "media").iterdir())) == 2
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_normalize.py tests/test_clips_step.py -v`
Expected: FAIL dengan `ImportError: cannot import name 'normalize_video'`.

- [ ] **Step 3: Implementasi**

Tambahin ke `mayzfact/ffmpeg.py`. Import `os` dan `tmp_path_for` taruh di blok import paling atas:

```python
import os

from mayzfact.store import tmp_path_for


def normalize_video(src: Path, dest: Path, *, start_s: float, duration_s: float, scale: float) -> None:
    """Potong, ubah ke 30fps H.264 yuv420p tanpa audio, resize pakai faktor `scale` (dimensi dibikin genap)."""
    vf = f"scale=trunc(iw*{scale:.6f}/2)*2:trunc(ih*{scale:.6f}/2)*2:flags=lanczos,fps=30,format=yuv420p"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_path_for(dest)
    _run(
        [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{start_s:.3f}", "-i", str(src), "-t", f"{duration_s:.3f}",
            "-an", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-movflags", "+faststart", str(tmp),
        ],
        "clips",
    )
    os.replace(tmp, dest)
```

`mayzfact/photo.py`:

```python
"""Normalisasi foto: ikutin orientasi EXIF, jadi RGB, resize (cuma ngecilin), simpan JPG."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageOps

from mayzfact.media import PHOTO_ZOOM, downscale_factor
from mayzfact.store import tmp_path_for


def normalize_photo(src: Path, dest: Path, *, fg_min_ratio: float) -> tuple[int, int]:
    with Image.open(src) as opened:
        img = ImageOps.exif_transpose(opened).convert("RGB")
    factor = downscale_factor(img.width, img.height, fg_min_ratio, PHOTO_ZOOM)
    if factor < 1.0:
        img = img.resize((round(img.width * factor), round(img.height * factor)), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_path_for(dest)
    img.save(tmp, "JPEG", quality=92)
    os.replace(tmp, dest)
    return img.size
```

Tambahin ke **atas** `mayzfact/steps/clips.py`, gabung sama import yang udah ada:

```python
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import httpx

from mayzfact.ffmpeg import normalize_video, probe
from mayzfact.media import downscale_factor, pick_rendition
from mayzfact.net import download
from mayzfact.photo import normalize_photo
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import beat_texts
from mayzfact.timing import beat_timings
```

Tambahin ke **bawah** `mayzfact/steps/clips.py`:

```python
def materialize(
    slot: ShotSlot,
    candidate: Candidate,
    query: str,
    paths: RunPaths,
    client: httpx.Client,
    media_cache: Path,
    fg_min_ratio: float,
) -> dict:
    rendition = pick_rendition(candidate, fg_min_ratio)
    default_ext = ".mp4" if candidate.kind == "video" else ".jpg"
    suffix = Path(urlparse(rendition.url).path).suffix.lower() or default_ext
    raw_name = f"{candidate.provider}_{candidate.kind}_{candidate.id}_{rendition.width}x{rendition.height}{suffix}"
    raw = download(client, rendition.url, media_cache / raw_name, step="clips")
    if candidate.kind == "video":
        dest = paths.clips_dir / f"shot_{slot.index + 1:02d}.mp4"
        start = 0.5 if (candidate.duration_s or 0) >= slot.duration_s + 1.0 else 0.0
        scale = downscale_factor(rendition.width, rendition.height, fg_min_ratio)
        normalize_video(raw, dest, start_s=start, duration_s=slot.duration_s + 0.2, scale=scale)
        info = probe(dest, "clips")
        width, height = info["width"], info["height"]
    else:
        dest = paths.clips_dir / f"shot_{slot.index + 1:02d}.jpg"
        width, height = normalize_photo(raw, dest, fg_min_ratio=fg_min_ratio)
    return {
        "index": slot.index,
        "beat": slot.beat,
        "start_s": slot.start_s,
        "end_s": slot.end_s,
        "kind": candidate.kind,
        "file": f"clips/{dest.name}",
        "width": width,
        "height": height,
        "provider": candidate.provider,
        "provider_id": candidate.id,
        "page_url": candidate.page_url,
        "author": candidate.author,
        "query": query,
    }


def run_clips(
    paths: RunPaths,
    script: dict,
    tts: dict,
    search: MediaSearch,
    client: httpx.Client,
    *,
    max_shot_s: float,
    fg_min_ratio: float,
    media_cache: Path,
    log: Callable[[str], None] = print,
) -> dict:
    timings = beat_timings(beat_texts(script["beats"]), tts["alignment"], tts["duration_s"])
    slots = split_shots(timings, script["beats"], max_shot_s)
    picks = select_clips(slots, script["beats"], script["fallback_query"], search, fg_min_ratio)
    paths.clips_dir.mkdir(parents=True, exist_ok=True)
    for old in paths.clips_dir.glob("shot_*"):
        old.unlink()
    shots = []
    for slot, candidate, query in picks:
        log(f"[clips] shot {slot.index + 1}/{len(picks)}: {candidate.provider} {candidate.kind} {candidate.id} ({query})")
        shots.append(materialize(slot, candidate, query, paths, client, media_cache, fg_min_ratio))
    data = {"shots": shots}
    write_json_atomic(paths.clips_json, data)
    return data
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_normalize.py tests/test_clips_step.py tests/test_clip_selection.py -v`
Expected: semua PASS (4 test baru + 8 test lama).

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/ffmpeg.py mayzfact/photo.py mayzfact/steps/clips.py tests/test_normalize.py tests/test_clips_step.py
git commit -m "feat: download and normalize clips into clips.json"
```

---

### Task 12: Step timeline

**Files:**

- Create: `mayzfact/steps/timeline.py`
- Test: `tests/test_timeline.py`

**Interfaces:**

- Consumes:
  - `layout_for`, `fg_height`, `FRAME_W`, `FRAME_H`, `PHOTO_ZOOM` (Task 8)
  - `PipelineError`, `RunPaths`, `write_json_atomic` (Task 1)
- Produces:
  - `FPS = 30`
  - `to_frame(seconds, fps=FPS) -> int`
  - `build_timeline(clips: dict, audio_duration_s: float, fg_min_ratio: float) -> dict`
  - `run_timeline(paths, clips, tts, *, fg_min_ratio) -> dict`

  Format `timeline.json`: `{"fps", "width", "height", "durationInFrames", "audio", "photoZoom", "shots": [{"src", "kind", "layout", "from", "durationInFrames", "fgHeight"?}]}`. Field `fgHeight` cuma ada di shot `blur`.

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_timeline.py`:

```python
import pytest

from mayzfact.errors import PipelineError
from mayzfact.steps.timeline import build_timeline, run_timeline, to_frame
from mayzfact.store import RunPaths, read_json


def shot(file, kind, start_s, width, height):
    return {"file": file, "kind": kind, "start_s": start_s, "width": width, "height": height}


CLIPS = {
    "shots": [
        shot("clips/shot_01.mp4", "video", 0.0, 1080, 1920),
        shot("clips/shot_02.jpg", "photo", 2.4, 1600, 1000),
        shot("clips/shot_03.mp4", "video", 4.4, 1920, 1080),
    ]
}


def test_to_frame_rounds_half_up():
    assert to_frame(0.0) == 0
    assert to_frame(2.4) == 72
    assert to_frame(0.0167) == 1
    assert to_frame(0.0166) == 0


def test_build_timeline_frames_layouts_and_total():
    timeline = build_timeline(CLIPS, audio_duration_s=6.5, fg_min_ratio=0.5)
    assert (timeline["fps"], timeline["width"], timeline["height"], timeline["durationInFrames"]) == (30, 1080, 1920, 195)
    assert (timeline["audio"], timeline["photoZoom"]) == ("voice.mp3", 1.08)
    assert timeline["shots"] == [
        {"src": "clips/shot_01.mp4", "kind": "video", "layout": "full", "from": 0, "durationInFrames": 72},
        {"src": "clips/shot_02.jpg", "kind": "photo", "layout": "blur", "from": 72, "durationInFrames": 60, "fgHeight": 960},
        {"src": "clips/shot_03.mp4", "kind": "video", "layout": "blur", "from": 132, "durationInFrames": 63, "fgHeight": 960},
    ]
    assert sum(s["durationInFrames"] for s in timeline["shots"]) == timeline["durationInFrames"]


def test_backslash_paths_become_forward_slashes():
    timeline = build_timeline({"shots": [shot("clips\\shot_01.mp4", "video", 0.0, 1080, 1920)]}, 2.0, 0.5)
    assert timeline["shots"][0]["src"] == "clips/shot_01.mp4"


def test_zero_frame_shot_is_an_error():
    clips = {"shots": [shot("clips/a.mp4", "video", 0.0, 1080, 1920), shot("clips/b.mp4", "video", 0.01, 1080, 1920)]}
    with pytest.raises(PipelineError, match="0 frame"):
        build_timeline(clips, 2.0, 0.5)


def test_run_timeline_writes_json(tmp_path):
    paths = RunPaths(tmp_path)
    data = run_timeline(paths, CLIPS, {"duration_s": 6.5}, fg_min_ratio=0.5)
    assert read_json(paths.timeline_json) == data
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_timeline.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.steps.timeline'`.

- [ ] **Step 3: Implementasi**

`mayzfact/steps/timeline.py`:

```python
"""Step timeline: detik → frame, tentuin layout tiap shot, tulis props buat Remotion."""

from __future__ import annotations

import math

from mayzfact.errors import PipelineError
from mayzfact.media import FRAME_H, FRAME_W, PHOTO_ZOOM, fg_height, layout_for
from mayzfact.store import RunPaths, write_json_atomic

FPS = 30


def to_frame(seconds: float, fps: int = FPS) -> int:
    return int(math.floor(seconds * fps + 0.5))


def build_timeline(clips: dict, audio_duration_s: float, fg_min_ratio: float) -> dict:
    shots = clips["shots"]
    if not shots:
        raise PipelineError("timeline", "clips.json kosong.")
    total = math.ceil(audio_duration_s * FPS - 1e-6)
    starts = [0] + [to_frame(s["start_s"]) for s in shots[1:]]
    entries = []
    for index, shot in enumerate(shots):
        end = starts[index + 1] if index + 1 < len(shots) else total
        if end <= starts[index]:
            raise PipelineError("timeline", f"Shot {index + 1} jadi 0 frame setelah dibulatin.")
        layout = layout_for(shot["width"], shot["height"])
        entry = {
            "src": shot["file"].replace("\\", "/"),
            "kind": shot["kind"],
            "layout": layout,
            "from": starts[index],
            "durationInFrames": end - starts[index],
        }
        if layout == "blur":
            entry["fgHeight"] = fg_height(shot["width"], shot["height"], fg_min_ratio)
        entries.append(entry)
    return {
        "fps": FPS,
        "width": FRAME_W,
        "height": FRAME_H,
        "durationInFrames": total,
        "audio": "voice.mp3",
        "photoZoom": PHOTO_ZOOM,
        "shots": entries,
    }


def run_timeline(paths: RunPaths, clips: dict, tts: dict, *, fg_min_ratio: float) -> dict:
    data = build_timeline(clips, tts["duration_s"], fg_min_ratio)
    write_json_atomic(paths.timeline_json, data)
    return data
```

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_timeline.py -v`
Expected: 5 test PASS.

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/steps/timeline.py tests/test_timeline.py
git commit -m "feat: build remotion timeline from clips"
```

---

### Task 13: Project Remotion + step render

**Files:**

- Create: `remotion/package.json`, `remotion/tsconfig.json`, `remotion/src/index.ts`, `remotion/src/Root.tsx`, `remotion/src/ShortVideo.tsx`, `remotion/src/ShotView.tsx`, `remotion/src/types.ts`, `mayzfact/steps/render.py`
- Test: `tests/test_render.py`

**Interfaces:**

- Consumes:
  - Format `timeline.json` dan `build_timeline` (Task 12)
  - `RunPaths`, `tmp_path_for`, `write_json_atomic` (Task 1)
  - `PROJECT_ROOT` (Task 1)
- Produces:
  - Composition Remotion `ShortVideo`, yang props-nya persis `timeline.json`.
  - Konstanta `REMOTION_DIR` dan `COMPOSITION_ID`.
  - `render_command(npx: str, paths: RunPaths, output: Path) -> list[str]`
  - `run_render(paths: RunPaths, remotion_dir: Path = REMOTION_DIR) -> Path`

- [ ] **Step 1: Aktifin Node 22**

Run: `nvm use 22.23.1` lalu `node -v`
Expected: `v22.23.1`. nvm-windows bisa minta admin. Kalau `nvm use` gagal karena permission, minta Akmal jalanin `nvm use 22.23.1` di terminal admin, terus lanjut.

- [ ] **Step 2: Bikin project Remotion**

`remotion/package.json`:

```json
{
  "name": "mayzfact-remotion",
  "private": true,
  "scripts": {
    "typecheck": "tsc --noEmit",
    "studio": "remotion studio src/index.ts"
  }
}
```

`remotion/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "lib": ["DOM", "ES2022"],
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"]
}
```

Run (dari folder `remotion/`):

```bash
npm install --save-exact remotion@latest @remotion/cli@latest @remotion/media@latest react@19 react-dom@19
npm install --save-dev --save-exact typescript@latest @types/react@19 @types/react-dom@19
npm ls remotion @remotion/cli @remotion/media
```

Expected: `npm ls` nunjukin versi yang **sama persis** buat `remotion`, `@remotion/cli`, dan `@remotion/media`. Kalau beda, install ulang ketiganya pakai versi `remotion` yang ke-install.

- [ ] **Step 3: Tulis komponen**

`remotion/src/types.ts`:

```ts
export type Shot = {
  src: string;
  kind: 'video' | 'photo';
  layout: 'full' | 'blur';
  from: number;
  durationInFrames: number;
  fgHeight?: number;
};

// Pakai `type`, bukan `interface`: props Remotion harus cocok sama Record<string, unknown>.
export type TimelineProps = {
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  audio: string;
  photoZoom: number;
  shots: Shot[];
};
```

`remotion/src/index.ts`:

```ts
import {registerRoot} from 'remotion';
import {RemotionRoot} from './Root';

registerRoot(RemotionRoot);
```

`remotion/src/Root.tsx`:

```tsx
import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {ShortVideo} from './ShortVideo';
import type {TimelineProps} from './types';

const defaultProps: TimelineProps = {
  fps: 30,
  width: 1080,
  height: 1920,
  durationInFrames: 30,
  audio: '',
  photoZoom: 1.08,
  shots: [],
};

const calculateMetadata: CalculateMetadataFunction<TimelineProps> = async ({props}) => ({
  durationInFrames: props.durationInFrames,
  fps: props.fps,
  width: props.width,
  height: props.height,
});

export const RemotionRoot: React.FC = () => (
  <Composition
    id="ShortVideo"
    component={ShortVideo}
    durationInFrames={defaultProps.durationInFrames}
    fps={defaultProps.fps}
    width={defaultProps.width}
    height={defaultProps.height}
    defaultProps={defaultProps}
    calculateMetadata={calculateMetadata}
  />
);
```

`remotion/src/ShortVideo.tsx`:

```tsx
import React from 'react';
import {AbsoluteFill, Sequence, staticFile} from 'remotion';
import {Audio} from '@remotion/media';
import {ShotView} from './ShotView';
import type {TimelineProps} from './types';

export const ShortVideo: React.FC<TimelineProps> = ({audio, shots, photoZoom}) => (
  <AbsoluteFill style={{backgroundColor: 'black'}}>
    {shots.map((shot) => (
      <Sequence key={shot.src} from={shot.from} durationInFrames={shot.durationInFrames}>
        <ShotView shot={shot} photoZoom={photoZoom} />
      </Sequence>
    ))}
    {audio ? <Audio src={staticFile(audio)} /> : null}
  </AbsoluteFill>
);
```

`remotion/src/ShotView.tsx`:

```tsx
import React from 'react';
import {AbsoluteFill, Img, interpolate, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import type {Shot} from './types';

const cover: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover'};

const Media: React.FC<{shot: Shot; style?: React.CSSProperties}> = ({shot, style}) => {
  const src = staticFile(shot.src);
  return shot.kind === 'video' ? (
    <OffthreadVideo src={src} muted style={{...cover, ...style}} />
  ) : (
    <Img src={src} style={{...cover, ...style}} />
  );
};

export const ShotView: React.FC<{shot: Shot; photoZoom: number}> = ({shot, photoZoom}) => {
  const frame = useCurrentFrame();
  const zoom =
    shot.kind === 'photo'
      ? interpolate(frame, [0, Math.max(1, shot.durationInFrames - 1)], [1, photoZoom], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
      : 1;
  const zoomStyle: React.CSSProperties = {transform: `scale(${zoom})`};

  if (shot.layout === 'full') {
    return (
      <AbsoluteFill style={{overflow: 'hidden'}}>
        <Media shot={shot} style={zoomStyle} />
      </AbsoluteFill>
    );
  }

  // Layout blur: background media yang sama di-blur (diam), foreground kotak setinggi fgHeight di tengah.
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <AbsoluteFill>
        <Media shot={shot} style={{filter: 'blur(40px) brightness(0.7)', transform: 'scale(1.15)'}} />
      </AbsoluteFill>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{width: '100%', height: shot.fgHeight ?? 960, overflow: 'hidden'}}>
          <Media shot={shot} style={zoomStyle} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 4: Typecheck + siapin browser Remotion**

Run (dari folder `remotion/`): `npx tsc --noEmit`
Expected: tanpa output, exit code 0.

Run (dari folder `remotion/`): `npx remotion browser ensure`
Expected: Chrome Headless Shell ke-download, atau muncul pesan bahwa browser-nya udah ada.

- [ ] **Step 5: Tulis test render yang gagal**

`tests/test_render.py`:

```python
import json
import shutil
import subprocess

import pytest

from mayzfact.steps.render import render_command, run_render
from mayzfact.steps.timeline import build_timeline
from mayzfact.store import RunPaths, write_json_atomic


def test_render_command_uses_absolute_props_and_public_dir(tmp_path):
    paths = RunPaths(tmp_path / "runs" / "abc")
    cmd = render_command("npx", paths, paths.root / "final.tmp.mp4")
    assert cmd[:5] == ["npx", "remotion", "render", "src/index.ts", "ShortVideo"]
    assert cmd[5] == str(paths.root / "final.tmp.mp4")
    assert f"--props={paths.timeline_json}" in cmd
    assert f"--public-dir={paths.root}" in cmd
    assert "--codec=h264" in cmd


@pytest.mark.render
def test_render_fixture_timeline(tmp_path, make_video, make_photo, sine_mp3):
    paths = RunPaths(tmp_path / "run")
    paths.clips_dir.mkdir(parents=True)
    shutil.copy(make_video(1080, 1920, 2.0), paths.clips_dir / "shot_01.mp4")
    shutil.copy(make_video(1920, 1080, 2.0), paths.clips_dir / "shot_02.mp4")
    shutil.copy(make_photo(1600, 1000), paths.clips_dir / "shot_03.jpg")
    shutil.copy(sine_mp3, paths.voice_mp3)
    clips = {"shots": [
        {"file": "clips/shot_01.mp4", "kind": "video", "start_s": 0.0, "width": 1080, "height": 1920},
        {"file": "clips/shot_02.mp4", "kind": "video", "start_s": 1.0, "width": 1920, "height": 1080},
        {"file": "clips/shot_03.jpg", "kind": "photo", "start_s": 2.0, "width": 1600, "height": 1000},
    ]}
    write_json_atomic(paths.timeline_json, build_timeline(clips, audio_duration_s=3.0, fg_min_ratio=0.5))

    run_render(paths)

    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration",
         "-of", "json", str(paths.final_mp4)],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(out.stdout)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
    assert (video["codec_name"], video["width"], video["height"], video["r_frame_rate"]) == ("h264", 1080, 1920, "30/1")
    assert audio["codec_name"] == "aac"
    assert abs(float(info["format"]["duration"]) - 3.0) < 0.1
    for t in ("0.5", "1.5", "2.1", "2.9"):
        frame = tmp_path / f"frame_{t}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", t, "-i", str(paths.final_mp4), "-frames:v", "1", str(frame)], check=True)
        assert frame.exists()
```

Run: `uv run pytest tests/test_render.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.steps.render'`.

- [ ] **Step 6: Implementasi `mayzfact/steps/render.py`**

```python
"""Step render: panggil Remotion CLI buat bikin final.mp4 dari timeline.json."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from mayzfact.config import PROJECT_ROOT
from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths, tmp_path_for

REMOTION_DIR = PROJECT_ROOT / "remotion"
COMPOSITION_ID = "ShortVideo"


def render_command(npx: str, paths: RunPaths, output: Path) -> list[str]:
    return [
        npx, "remotion", "render", "src/index.ts", COMPOSITION_ID, str(output),
        f"--props={paths.timeline_json}", f"--public-dir={paths.root}", "--codec=h264",
    ]


def run_render(paths: RunPaths, remotion_dir: Path = REMOTION_DIR) -> Path:
    npx = shutil.which("npx")
    if npx is None:
        raise PipelineError("render", "npx nggak ketemu. Aktifin Node dulu: nvm use 22.23.1")
    if not (remotion_dir / "node_modules").exists():
        raise PipelineError("render", "Dependency Remotion belum ke-install. Jalanin: cd remotion && npm install")
    output = tmp_path_for(paths.final_mp4)
    result = subprocess.run(
        render_command(npx, paths, output),
        cwd=remotion_dir, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise PipelineError("render", "Remotion gagal:\n" + (result.stderr or result.stdout)[-2000:])
    os.replace(output, paths.final_mp4)
    return paths.final_mp4
```

- [ ] **Step 7: Jalanin test render (cepat + beneran)**

Run: `uv run pytest tests/test_render.py -v`
Expected: 1 PASS (`test_render_command...`), 1 deselected (marker `render`).

Run: `uv run pytest -m render --basetemp=runs/_render_test -v`
Expected: `test_render_fixture_timeline` PASS. Render pertama bisa makan 1–2 menit karena bundling.

- [ ] **Step 8: Cek visual frame hasil render**

Buka PNG di `runs/_render_test/test_render_fixture_timeline0/` pakai tool Read, terus cek:

- `frame_0.5.png`: testsrc portrait menuhin satu frame, tanpa bar hitam.
- `frame_1.5.png`: background blur gelap full frame, plus kotak testsrc landscape yang tajam di tengah setinggi ±960px (setengah frame), kiri-kanannya kepotong.
- `frame_2.1.png` vs `frame_2.9.png`: foto landscape di kotak tengah, dan di 2.9 kelihatan sedikit lebih zoom daripada di 2.1. Background blur-nya diam.

Kalau ada yang nggak sesuai, benerin `ShotView.tsx`, lalu ulang Step 4 dan Step 7.

- [ ] **Step 9: Commit (kalau udah diizinin)**

```bash
git add remotion/package.json remotion/package-lock.json remotion/tsconfig.json remotion/src mayzfact/steps/render.py tests/test_render.py
git commit -m "feat: add remotion composition and render step"
```

---

### Task 14: Pipeline, aturan kunci, CLI, README

**Files:**

- Create: `mayzfact/pipeline.py`, `mayzfact/cli.py`, `README.md`
- Test: `tests/test_pipeline.py`, `tests/test_cli.py`

**Interfaces:**

- Consumes: semua step dan provider dari Task 1–13
- Produces:
  - Konstanta: `STEPS`, `VOICE_LOCKED`, `AFTER_VOICE`, `MIN_AUDIO_SECONDS = 30.0`, `STEP_ENV`
  - `step_done(step, paths) -> bool`
  - `plan_steps(done: dict[str, bool], voice_exists: bool, from_step: str | None, new_voice: bool) -> list[str]`
  - `check_voice(paths) -> dict`
  - `Deps(fetch_transcript, script_writer, tts, search, http, render, media_cache=CACHE_DIR / "media")`
  - `real_deps(settings) -> Deps`
  - `run_pipeline(video, *, settings, from_step=None, new_voice=False, deps=None, runs_dir=RUNS_DIR, log=print) -> RunPaths`
  - `cli.main(argv=None) -> int`, dengan command `run` dan `voices`

- [ ] **Step 1: Tulis test yang gagal**

`tests/test_pipeline.py`:

```python
import math
from types import SimpleNamespace

import httpx
import pytest

from mayzfact.config import Settings
from mayzfact.errors import PipelineError
from mayzfact.pipeline import STEPS, Deps, check_voice, plan_steps, run_pipeline
from mayzfact.store import RunPaths, read_json, write_json_atomic
from mayzfact.text import script_text, text_hash
from tests.factories import cand, fake_alignment, make_script

VIDEO_ID = "i2xag_1OJfM"
KEYS = {"gemini_api_key": "g", "elevenlabs_api_key": "e", "elevenlabs_voice_id": "v", "pexels_api_key": "p", "pixabay_api_key": "x"}
SETTINGS = Settings(**KEYS, max_shot_seconds=10.0)
TRANSCRIPT = [{"text": "Five ancient creatures are still alive today", "start": 0.0, "duration": 53.3}]
NONE_DONE = {step: False for step in STEPS}
ALL_DONE = {step: True for step in STEPS}
QUIET = {"log": lambda message: None}


def done_until(last: str) -> dict:
    return {step: STEPS.index(step) <= STEPS.index(last) for step in STEPS}


# --- plan_steps -------------------------------------------------------------

def test_fresh_run_runs_everything():
    assert plan_steps(NONE_DONE, False, None, False) == STEPS


def test_plain_run_resumes_from_first_missing_step():
    assert plan_steps(done_until("script"), False, None, False) == ["tts", "clips", "timeline", "render"]
    assert plan_steps(ALL_DONE, True, None, False) == []


def test_from_clips_is_allowed_with_voice():
    assert plan_steps(ALL_DONE, True, "clips", False) == ["clips", "timeline", "render"]


@pytest.mark.parametrize("step", ["source", "script", "tts"])
def test_from_locked_step_is_rejected_when_voice_exists(step):
    with pytest.raises(PipelineError, match="dikunci"):
        plan_steps(ALL_DONE, True, step, False)


def test_from_script_is_allowed_before_voice_exists():
    assert plan_steps(done_until("script"), False, "script", False) == STEPS[1:]


def test_from_step_needs_previous_outputs():
    with pytest.raises(PipelineError, match="belum pernah selesai"):
        plan_steps(done_until("tts"), True, "timeline", False)


def test_new_voice_reruns_script_and_after():
    assert plan_steps(ALL_DONE, True, None, True) == STEPS[1:]
    assert plan_steps(NONE_DONE, False, None, True) == STEPS
    with pytest.raises(PipelineError, match="nggak bisa digabung"):
        plan_steps(ALL_DONE, True, "clips", True)


def test_voice_without_metadata_needs_new_voice():
    broken = {**ALL_DONE, "tts": False}
    with pytest.raises(PipelineError, match="--new-voice"):
        plan_steps(broken, True, None, False)


# --- check_voice ------------------------------------------------------------

def write_voice_state(paths, text_beats, duration_s, sha=None):
    script = {"beats": [{"text": t, "media": "video", "queries": ["q"]} for t in text_beats], "fallback_query": "f"}
    write_json_atomic(paths.script_json, script)
    write_json_atomic(paths.tts_json, {"text_sha256": sha or text_hash(script_text(script["beats"])), "duration_s": duration_s})


def test_check_voice_accepts_matching_long_audio(tmp_path):
    paths = RunPaths(tmp_path)
    write_voice_state(paths, ["Look at this.", "It is old."], 31.0)
    assert check_voice(paths)["duration_s"] == 31.0


def test_check_voice_rejects_edited_script(tmp_path):
    paths = RunPaths(tmp_path)
    write_voice_state(paths, ["Look at this.", "It is old."], 31.0, sha="beda")
    with pytest.raises(PipelineError, match="beda"):
        check_voice(paths)


def test_check_voice_rejects_short_audio(tmp_path):
    paths = RunPaths(tmp_path)
    write_voice_state(paths, ["Look at this."], 29.0)
    with pytest.raises(PipelineError, match="--new-voice"):
        check_voice(paths)


# --- run_pipeline dengan dependency palsu ----------------------------------

class FakeWriter:
    def write(self, system, user):
        return make_script(n_beats=8, words_per_beat=10)


class FakeTTS:
    voice_id = "v"
    model_id = "eleven_v3"

    def __init__(self, audio: bytes, total_s: float):
        self.audio = audio
        self.total_s = total_s
        self.calls = 0

    def synthesize(self, text):
        self.calls += 1
        return self.audio, fake_alignment(text, self.total_s)


class FakeSearch:
    def candidates(self, kind, query):
        if kind == "video":
            return [cand("pexels", f"v{i}", "video", 1080, 1920, duration_s=30.0, rank=i, url=f"https://cdn.test/v{i}.mp4") for i in range(10)]
        return [cand("pexels", f"p{i}", "photo", 1600, 1000, rank=i, url=f"https://cdn.test/p{i}.jpg") for i in range(10)]


def build_world(tmp_path, audio_path, total_s, make_video, make_photo):
    video_bytes = make_video(1080, 1920, 5.0).read_bytes()
    photo_bytes = make_photo(1600, 1000).read_bytes()
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=video_bytes if request.url.path.endswith(".mp4") else photo_bytes)
    ))
    tts = FakeTTS(audio_path.read_bytes(), total_s)
    world = SimpleNamespace(tts=tts, writer_calls=0, renders=0, runs=tmp_path / "runs")

    def writer():
        world.writer_calls += 1
        return FakeWriter()

    def render(paths):
        world.renders += 1
        paths.final_mp4.write_bytes(b"fake-mp4")
        return paths.final_mp4

    world.deps = Deps(
        fetch_transcript=lambda video_id: TRANSCRIPT,
        script_writer=writer,
        tts=lambda: tts,
        search=FakeSearch,
        http=lambda: client,
        render=render,
        media_cache=tmp_path / "media",
    )
    return world


@pytest.fixture
def world(tmp_path, long_mp3, make_video, make_photo):
    return build_world(tmp_path, long_mp3, 30.0, make_video, make_photo)


def run(world, **kwargs):
    return run_pipeline(VIDEO_ID, settings=kwargs.pop("settings", SETTINGS), deps=world.deps, runs_dir=world.runs, **QUIET, **kwargs)


def test_full_run_then_rerun_from_clips_reuses_voice(world):
    paths = run(world)
    assert paths.final_mp4.read_bytes() == b"fake-mp4"
    assert (world.tts.calls, world.writer_calls, world.renders) == (1, 1, 1)
    timeline = read_json(paths.timeline_json)
    assert len(timeline["shots"]) == 8
    assert timeline["durationInFrames"] == math.ceil(read_json(paths.tts_json)["duration_s"] * 30 - 1e-6)
    voice_mtime = paths.voice_mp3.stat().st_mtime_ns

    run(world, from_step="clips")
    assert (world.tts.calls, world.writer_calls, world.renders) == (1, 1, 2)
    assert paths.voice_mp3.stat().st_mtime_ns == voice_mtime


def test_second_plain_run_does_nothing(world):
    run(world)
    run(world)
    assert (world.tts.calls, world.renders) == (1, 1)


def test_from_script_is_rejected_after_voice(world):
    run(world)
    with pytest.raises(PipelineError, match="dikunci"):
        run(world, from_step="script")
    assert world.tts.calls == 1


def test_new_voice_regenerates_script_and_voice(world):
    run(world)
    run(world, new_voice=True)
    assert (world.tts.calls, world.writer_calls, world.renders) == (2, 2, 2)


def test_edited_script_blocks_clips_without_calling_tts(world):
    paths = run(world)
    script = read_json(paths.script_json)
    script["beats"][0]["text"] = "Diedit manual."
    write_json_atomic(paths.script_json, script)
    with pytest.raises(PipelineError, match="beda"):
        run(world, from_step="clips")
    assert world.tts.calls == 1


def test_short_audio_stops_before_clips(tmp_path, sine_mp3, make_video, make_photo):
    world = build_world(tmp_path, sine_mp3, 2.5, make_video, make_photo)
    with pytest.raises(PipelineError, match="--new-voice"):
        run(world)
    paths = RunPaths(world.runs / VIDEO_ID)
    assert paths.voice_mp3.exists()
    assert not paths.clips_json.exists()


def test_missing_keys_fail_before_any_step(world):
    with pytest.raises(PipelineError, match="GEMINI_API_KEY.*ELEVENLABS_API_KEY.*ELEVENLABS_VOICE_ID.*PEXELS_API_KEY.*PIXABAY_API_KEY"):
        run(world, settings=Settings())
    assert not (world.runs / VIDEO_ID / "source.json").exists()


def test_from_clips_does_not_need_gemini_or_elevenlabs_keys(world):
    run(world)
    run(world, from_step="clips", settings=Settings(pexels_api_key="p", pixabay_api_key="x", max_shot_seconds=10.0))
    assert world.renders == 2
```

`tests/test_cli.py`:

```python
import pytest

from mayzfact import cli
from mayzfact.config import Settings
from mayzfact.errors import PipelineError
from mayzfact.store import RunPaths


def test_cli_rejects_unknown_step():
    with pytest.raises(SystemExit) as exc:
        cli.main(["run", "i2xag_1OJfM", "--from", "upload"])
    assert exc.value.code == 2


def test_cli_passes_flags_to_pipeline(monkeypatch, tmp_path, capsys):
    seen = {}

    def fake_run(video, *, settings, from_step, new_voice):
        seen.update(video=video, from_step=from_step, new_voice=new_voice)
        return RunPaths(tmp_path)

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "run_pipeline", fake_run)
    assert cli.main(["run", "https://youtu.be/i2xag_1OJfM", "--new-voice"]) == 0
    assert seen == {"video": "https://youtu.be/i2xag_1OJfM", "from_step": None, "new_voice": True}
    assert "Selesai:" in capsys.readouterr().out


def test_cli_prints_pipeline_error(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise PipelineError("cli", "voice.mp3 udah ada")

    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "run_pipeline", boom)
    assert cli.main(["run", "i2xag_1OJfM", "--from", "script"]) == 1
    assert "Error [cli] voice.mp3 udah ada" in capsys.readouterr().err


def test_cli_voices_needs_key(monkeypatch, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    assert cli.main(["voices"]) == 1
    assert "ELEVENLABS_API_KEY" in capsys.readouterr().err
```

- [ ] **Step 2: Jalanin test, pastiin gagal**

Run: `uv run pytest tests/test_pipeline.py tests/test_cli.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'mayzfact.pipeline'`.

- [ ] **Step 3: Implementasi**

`mayzfact/pipeline.py`:

```python
"""Urutan step, aturan kunci naskah + suara (spec 3.4), dan runner utama pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from mayzfact.cache import SearchCache
from mayzfact.config import CACHE_DIR, RUNS_DIR, Settings, missing_env
from mayzfact.errors import PipelineError
from mayzfact.net import make_client
from mayzfact.providers.elevenlabs import ElevenLabsTTS
from mayzfact.providers.gemini import GeminiScriptWriter
from mayzfact.providers.pexels import Pexels
from mayzfact.providers.pixabay import Pixabay
from mayzfact.providers.stock import StockSearch
from mayzfact.steps.clips import MediaSearch, run_clips
from mayzfact.steps.render import run_render
from mayzfact.steps.script import ScriptWriter, run_script
from mayzfact.steps.source import parse_video_id, run_source, youtube_transcript
from mayzfact.steps.timeline import run_timeline
from mayzfact.steps.tts import TTSProvider, run_tts
from mayzfact.store import RunPaths, read_json
from mayzfact.text import script_text, text_hash

STEPS = ["source", "script", "tts", "clips", "timeline", "render"]
VOICE_LOCKED = ("source", "script", "tts")
AFTER_VOICE = ("clips", "timeline", "render")
MIN_AUDIO_SECONDS = 30.0
STEP_ENV = {
    "script": ["GEMINI_API_KEY"],
    "tts": ["ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"],
    "clips": ["PEXELS_API_KEY", "PIXABAY_API_KEY"],
}
NEW_VOICE_HINT = "Pakai --new-voice kalau emang mau naskah + suara baru (pakai kredit ElevenLabs)."


def step_done(step: str, paths: RunPaths) -> bool:
    outputs = {
        "source": [paths.source_json],
        "script": [paths.script_json],
        "tts": [paths.voice_mp3, paths.tts_json],
        "clips": [paths.clips_json],
        "timeline": [paths.timeline_json],
        "render": [paths.final_mp4],
    }[step]
    return all(path.exists() for path in outputs)


def plan_steps(done: dict[str, bool], voice_exists: bool, from_step: str | None, new_voice: bool) -> list[str]:
    if new_voice and from_step:
        raise PipelineError("cli", "--new-voice nggak bisa digabung sama --from.")
    if new_voice:
        return STEPS[1:] if done["source"] else list(STEPS)
    if voice_exists:
        broken = [step for step in VOICE_LOCKED if not done[step]]
        if broken:
            raise PipelineError("cli", f"voice.mp3 ada tapi hasil step {', '.join(broken)} hilang. {NEW_VOICE_HINT}")
    if from_step:
        if voice_exists and from_step in VOICE_LOCKED:
            raise PipelineError(
                "cli", f"voice.mp3 udah ada, jadi naskah + suara dikunci. Pakai --from clips. {NEW_VOICE_HINT}"
            )
        index = STEPS.index(from_step)
        missing = [step for step in STEPS[:index] if not done[step]]
        if missing:
            raise PipelineError("cli", f"Step {', '.join(missing)} belum pernah selesai. Jalanin tanpa --from dulu.")
        return STEPS[index:]
    for index, step in enumerate(STEPS):
        if not done[step]:
            return STEPS[index:]
    return []


def check_voice(paths: RunPaths) -> dict:
    """Dicek tiap run sebelum clips: naskah masih sama dengan suara, dan suaranya cukup panjang."""
    tts = read_json(paths.tts_json)
    script = read_json(paths.script_json)
    if text_hash(script_text(script["beats"])) != tts["text_sha256"]:
        raise PipelineError(
            "tts", f"script.json beda sama naskah yang dipakai buat voice.mp3. Balikin script.json. {NEW_VOICE_HINT}"
        )
    if tts["duration_s"] < MIN_AUDIO_SECONDS:
        raise PipelineError(
            "tts", f"Audio cuma {tts['duration_s']:.1f} detik (minimal {MIN_AUDIO_SECONDS:.0f}). {NEW_VOICE_HINT}"
        )
    return tts


@dataclass
class Deps:
    fetch_transcript: Callable[[str], list[dict]]
    script_writer: Callable[[], ScriptWriter]
    tts: Callable[[], TTSProvider]
    search: Callable[[], MediaSearch]
    http: Callable[[], httpx.Client]
    render: Callable[[RunPaths], Path]
    media_cache: Path = CACHE_DIR / "media"


def real_deps(settings: Settings) -> Deps:
    shared: dict[str, httpx.Client] = {}

    def http() -> httpx.Client:
        if "client" not in shared:
            shared["client"] = make_client()
        return shared["client"]

    def search() -> StockSearch:
        cache = SearchCache(CACHE_DIR / "search")
        return StockSearch(Pexels(settings.pexels_api_key, http(), cache), Pixabay(settings.pixabay_api_key, http(), cache))

    return Deps(
        fetch_transcript=youtube_transcript,
        script_writer=lambda: GeminiScriptWriter(settings.gemini_api_key, settings.gemini_model),
        tts=lambda: ElevenLabsTTS(
            settings.elevenlabs_api_key, settings.elevenlabs_voice_id, settings.elevenlabs_model, http()
        ),
        search=search,
        http=http,
        render=run_render,
    )


def run_pipeline(
    video: str,
    *,
    settings: Settings,
    from_step: str | None = None,
    new_voice: bool = False,
    deps: Deps | None = None,
    runs_dir: Path = RUNS_DIR,
    log: Callable[[str], None] = print,
) -> RunPaths:
    video_id = parse_video_id(video)
    paths = RunPaths(runs_dir / video_id)
    done = {step: step_done(step, paths) for step in STEPS}
    steps = plan_steps(done, paths.voice_mp3.exists(), from_step, new_voice)
    if not steps:
        log(f"Semua step {video_id} udah selesai: {paths.final_mp4}. Pakai --from clips/timeline/render buat bikin ulang.")
        return paths
    missing = missing_env(settings, [name for step in steps for name in STEP_ENV.get(step, [])])
    if missing:
        raise PipelineError("config", "Isi dulu di .env: " + ", ".join(missing))
    deps = deps or real_deps(settings)
    voice_checked = False
    for step in steps:
        if step in AFTER_VOICE and not voice_checked:
            check_voice(paths)
            voice_checked = True
        log(f"[{step}] mulai")
        _run_step(step, paths, settings, deps, log)
    return paths


def _run_step(step: str, paths: RunPaths, settings: Settings, deps: Deps, log: Callable[[str], None]) -> None:
    if step == "source":
        run_source(paths.root.name, paths, fetch=deps.fetch_transcript)
    elif step == "script":
        run_script(
            paths, read_json(paths.source_json), deps.script_writer(),
            ratio=settings.target_duration_ratio, minimum_s=settings.min_duration_seconds, photo_ratio=settings.photo_ratio,
        )
    elif step == "tts":
        run_tts(paths, read_json(paths.script_json), deps.tts(), log=log)
    elif step == "clips":
        run_clips(
            paths, read_json(paths.script_json), read_json(paths.tts_json), deps.search(), deps.http(),
            max_shot_s=settings.max_shot_seconds, fg_min_ratio=settings.fg_min_height_ratio,
            media_cache=deps.media_cache, log=log,
        )
    elif step == "timeline":
        run_timeline(paths, read_json(paths.clips_json), read_json(paths.tts_json), fg_min_ratio=settings.fg_min_height_ratio)
    elif step == "render":
        deps.render(paths)
```

`mayzfact/cli.py`:

```python
"""Entry point: `uv run mayzfact run <video> [--from STEP] [--new-voice]` dan `uv run mayzfact voices`."""

from __future__ import annotations

import argparse
import sys

from mayzfact.config import Settings, load_settings, missing_env
from mayzfact.errors import PipelineError
from mayzfact.net import make_client
from mayzfact.pipeline import STEPS, run_pipeline
from mayzfact.providers.elevenlabs import list_voices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mayzfact", description="Pipeline shorts: naskah ulang + TTS + klip stock")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Bikin video dari 1 YouTube Shorts source")
    run.add_argument("video", help="Video ID atau URL YouTube")
    run.add_argument("--from", dest="from_step", choices=STEPS, help="Ulang dari step ini (script/tts dikunci kalau voice.mp3 udah ada)")
    run.add_argument("--new-voice", action="store_true", help="Bikin naskah + suara baru (pakai kredit ElevenLabs)")
    sub.add_parser("voices", help="List voice ElevenLabs di akun lu")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings()
        if args.command == "voices":
            return _print_voices(settings)
        paths = run_pipeline(args.video, settings=settings, from_step=args.from_step, new_voice=args.new_voice)
        print(f"Selesai: {paths.final_mp4}")
        return 0
    except PipelineError as exc:
        print(f"Error {exc}", file=sys.stderr)
        return 1


def _print_voices(settings: Settings) -> int:
    missing = missing_env(settings, ["ELEVENLABS_API_KEY"])
    if missing:
        raise PipelineError("voices", "Isi dulu di .env: " + ", ".join(missing))
    for voice in list_voices(settings.elevenlabs_api_key, make_client()):
        labels = ", ".join(f"{key}={value}" for key, value in voice["labels"].items())
        print(f"{voice['voice_id']}  {voice['name']}  {labels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`README.md`:

````markdown
# mayzfact-automation

Pipeline YouTube Shorts. Naskah ditulis ulang pakai Gemini, suaranya dari ElevenLabs, klip video/foto diambil dari Pexels/Pixabay, lalu di-render pakai Remotion.

- Spec Fase 1: [docs/superpowers/specs/2026-09-30-fase1-pipeline-design.md](docs/superpowers/specs/2026-09-30-fase1-pipeline-design.md)
- Keputusan project: [docs/DECISIONS.md](docs/DECISIONS.md)

## Setup

1. `uv sync`
2. `nvm use 22.23.1`, lalu `cd remotion && npm install && npx remotion browser ensure`
3. Copy `.env.example` jadi `.env`, terus isi semua key-nya.
4. `uv run mayzfact voices` buat nyari `ELEVENLABS_VOICE_ID`.

## Pakai

```bash
uv run mayzfact run <video_id atau URL>        # jalanin semua step yang belum ada
uv run mayzfact run <id> --from clips          # ulang klip + timeline + render; suara nggak dibuat ulang
uv run mayzfact run <id> --new-voice           # naskah + suara baru (pakai kredit ElevenLabs)
```

Hasilnya ada di `runs/<id>/final.mp4`. Jangan hapus `runs/<id>/voice.mp3`, soalnya kalau kehapus suara harus dibuat ulang dan kredit kepakai lagi.

## Test

```bash
uv run pytest              # semua test, tanpa API beneran
uv run pytest -m render    # render Remotion beneran (butuh Node 22)
```
````

- [ ] **Step 4: Jalanin test, pastiin lolos**

Run: `uv run pytest tests/test_pipeline.py tests/test_cli.py -v`
Expected: semua PASS (25 test).

Run: `uv run pytest`
Expected: semua test PASS kecuali `test_render_fixture_timeline` (deselected).

- [ ] **Step 5: Commit (kalau udah diizinin)**

```bash
git add mayzfact/pipeline.py mayzfact/cli.py README.md tests/test_pipeline.py tests/test_cli.py
git commit -m "feat: wire pipeline, voice lock and cli"
```

---

### Task 15: Run beneran `i2xag_1OJfM` + cek Definition of Done + handoff

**Files:**

- Create: `docs/HANDOFF.md`
- Modify: `.env` (punya Akmal, nggak di-commit). `docs/DECISIONS.md` cuma diubah kalau nama model harus diganti.

**Interfaces:**

- Consumes: CLI dari Task 14
- Produces: `runs/i2xag_1OJfM/final.mp4` + bukti verifikasi DoD, dan `docs/HANDOFF.md`

- [ ] **Step 1: Minta Akmal isi `.env`**

Minta Akmal copy `.env.example` jadi `.env` dan isi `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `PEXELS_API_KEY`, dan `PIXABAY_API_KEY`. Tunggu sampai dia bilang udah. Jangan nulis atau nampilin isi key.

- [ ] **Step 2: Pilih voice**

Run: `uv run mayzfact voices`
Expected: daftar `voice_id  nama  label`. Kasih daftarnya ke Akmal, terus minta dia pilih voice English pria dengan nada "teacher for kids" dan isi `ELEVENLABS_VOICE_ID` di `.env`. Kalau voice yang cocok belum ada di akun, Akmal bisa nambahin dulu dari Voice Library ElevenLabs, terus jalanin command ini lagi.

- [ ] **Step 3: Cek nama model (gratis, tanpa generate)**

```bash
uv run python - <<'EOF'
from google import genai
from mayzfact.config import load_settings
s = load_settings()
names = [m.name for m in genai.Client(api_key=s.gemini_api_key).models.list()]
print("\n".join(n for n in names if "gemini" in n))
print("GEMINI_MODEL ada:", any(n.endswith(s.gemini_model) for n in names))
EOF
```

```bash
uv run python - <<'EOF'
import httpx
from mayzfact.config import load_settings
s = load_settings()
r = httpx.get("https://api.elevenlabs.io/v1/models", headers={"xi-api-key": s.elevenlabs_api_key}, timeout=30)
r.raise_for_status()
ids = [m["model_id"] for m in r.json()]
print(ids)
print("ELEVENLABS_MODEL ada:", s.elevenlabs_model in ids)
EOF
```

Expected: dua-duanya `... ada: True`. Kalau `False`, pilih model terdekat dari daftar (Flash terbaru buat Gemini, `eleven_multilingual_v2` buat ElevenLabs), set di `.env`, tambahin catatan di `docs/DECISIONS.md` D-003 atau entry baru, dan kasih tahu Akmal.

- [ ] **Step 4: Run pertama (ElevenLabs dipanggil 1x)**

Run: `uv run mayzfact run i2xag_1OJfM`
Expected:

- Log `[source]`, `[script]`, `[tts] Kirim N karakter ke ElevenLabs ...`, `[clips] shot ...`, `[timeline]`, dan `[render]`.
- Baris terakhir `Selesai: ...runs\i2xag_1OJfM\final.mp4`.

Kalau stop dengan error, baca pesannya dan pakai skill `systematic-debugging`. **Jangan** pakai `--new-voice` buat nge-debug masalah yang muncul setelah step tts.

- [ ] **Step 5: Cek DoD 2 (format)**

Run: `ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate:format=duration -of compact runs/i2xag_1OJfM/final.mp4`
Expected:

- stream video `h264`, `width=1080`, `height=1920`, `r_frame_rate=30/1`
- stream audio `aac`
- `duration` antara 30 dan 70.8

- [ ] **Step 6: Cek DoD 4 & 5 (klip, layout, naskah)**

```bash
uv run python - <<'EOF'
import json
run = "runs/i2xag_1OJfM"
clips = json.load(open(f"{run}/clips.json", encoding="utf-8"))["shots"]
timeline = json.load(open(f"{run}/timeline.json", encoding="utf-8"))
script = json.load(open(f"{run}/script.json", encoding="utf-8"))
ids = [(s["provider"], s["provider_id"]) for s in clips]
blur = [s for s in timeline["shots"] if s["layout"] == "blur"]
print("shots:", len(clips), "| video:", sum(s["kind"] == "video" for s in clips), "| foto:", sum(s["kind"] == "photo" for s in clips))
print("shot terpanjang (detik):", round(max(s["end_s"] - s["start_s"] for s in clips), 3))
print("klip unik:", len(ids) == len(set(ids)), "| provider:", sorted({s["provider"] for s in clips}))
print("shot blur:", len(blur), "| fgHeight terkecil:", min((s["fgHeight"] for s in blur), default="-"))
print("kata:", script["word_count"], "target", script["target_words"], "| overlap 4-gram:", script["ngram_overlap"])
print("credit lengkap:", all(s["page_url"] and s["author"] for s in clips))
EOF
```

Expected:

- `shot terpanjang` ≤ 2.5
- `klip unik: True`
- ada shot video dan foto
- `fgHeight terkecil` ≥ 960 (kalau ada shot blur)
- overlap ≤ 0.15
- `credit lengkap: True`

- [ ] **Step 7: Cek DoD 6 (run ulang tanpa ElevenLabs)**

```bash
stat -c %Y runs/i2xag_1OJfM/voice.mp3
ELEVENLABS_API_KEY= GEMINI_API_KEY= uv run mayzfact run i2xag_1OJfM --from clips
stat -c %Y runs/i2xag_1OJfM/voice.mp3
```

Expected: run-nya sukses walaupun key ElevenLabs & Gemini dikosongin. Kalau code sampai manggil ElevenLabs, run ini bakal error karena key-nya kosong. Dua angka `stat` harus sama, artinya `voice.mp3` nggak disentuh.

- [ ] **Step 8: Cek visual**

```bash
ffmpeg -y -v error -i runs/i2xag_1OJfM/final.mp4 -vf "fps=1/2,scale=270:480,tile=6x4" -frames:v 1 runs/i2xag_1OJfM/contact_sheet.png
```

Buka `contact_sheet.png` pakai tool Read, terus cek:

- nggak ada frame hitam
- layout portrait menuhin frame
- layout landscape pakai blur + kotak tengah
- visualnya nyambung sama topik naskah

Terus minta Akmal nonton `runs/i2xag_1OJfM/final.mp4` (DoD 8). Catat jawabannya apa adanya. Kalau ada yang mau diubah, catat di handoff sebagai pekerjaan lanjutan. Jangan anggap Fase 1 selesai sebelum Akmal oke.

- [ ] **Step 9: Semua check terakhir**

Run: `uv run pytest` lalu `uv run pytest -m render`
Run (dari folder `remotion/`): `npx tsc --noEmit`
Expected: semua lolos. Kalau ada yang gagal, catat output-nya di handoff.

- [ ] **Step 10: Tulis `docs/HANDOFF.md`**

Isi pakai format di bawah, dan pakai hasil **asli** dari Step 4–9. Jangan ngarang angka.

```markdown
# Handoff — Fase 1 pipeline

- **Updated:** <tanggal jam WIB>, <agent>
- **Goal & scope:** Fase 1 sesuai docs/superpowers/specs/2026-09-30-fase1-pipeline-design.md. Belum masuk: hook matching, TikTok/Douyin/RedNote, caption/musik/SFX/overlay, upload (Fase 2–4, lihat docs/DECISIONS.md D-001).
- **Workspace:** E:\APROJECT\mayzfact-automation, branch <branch>, commit <hash atau "belum di-commit">.
- **Selesai:** <ringkasan fitur + file utama>.
- **Model yang dipakai:** GEMINI_MODEL=<nilai>, ELEVENLABS_MODEL=<nilai>, voice <nama voice>.
- **Verifikasi:**
  - uv run pytest → <hasil>
  - uv run pytest -m render → <hasil>
  - npx tsc --noEmit → <hasil>
  - Run i2xag_1OJfM → <durasi, jumlah shot, video/foto, provider>
  - Run ulang --from clips tanpa key ElevenLabs → <hasil + mtime voice.mp3 sama/beda>
  - Review Akmal → <jawaban Akmal atau "belum">
- **Delivery:** <committed/pushed atau belum>. Commit cuma kalau Akmal minta.
- **Sisa kerjaan / next:** <catatan review Akmal>. Fase berikutnya: Fase 2 (hook matching) → mulai lagi dari brainstorming.
```

- [ ] **Step 11: Commit (kalau udah diizinin)**

```bash
git add docs/HANDOFF.md docs/DECISIONS.md
git commit -m "docs: add fase 1 handoff"
```
