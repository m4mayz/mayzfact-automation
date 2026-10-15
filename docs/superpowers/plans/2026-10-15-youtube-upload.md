# Upload Terjadwal ke YouTube — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Setelah `final.mp4` oke, agent nulis metadata, Akmal konfirmasi jam, terus `mayzfact upload` nge-upload ke YouTube sebagai video terjadwal (`publishAt`).

**Architecture:** Satu modul baru `mayzfact/youtube.py` (login OAuth, token di `.env`, validasi metadata, hitung slot, upload resumable). CLI nambah `login youtube`, `next-slot`, `upload`. Skill `bikin-short` nambah langkah metadata → konfirmasi jam → upload.

**Tech Stack:** Python 3.14 + uv, `google-auth-oauthlib`, `google-api-python-client`, pydantic, pytest.

**Spec:** `docs/superpowers/specs/2026-10-15-youtube-upload-design.md`

## Global Constraints

- Scope OAuth cuma `https://www.googleapis.com/auth/youtube.upload`.
- Token disimpan di baris `YOUTUBE_TOKEN_JSON` di `.env`, dalam kutip tunggal. Baris lain nggak disentuh.
- Isi `YOUTUBE_CLIENT_SECRET_JSON` / `YOUTUBE_TOKEN_JSON` nggak pernah di-print, di-log, atau masuk pesan error.
- Jam pakai WIB = UTC+7 (offset tetap, nggak pakai `zoneinfo` karena Windows nggak punya tzdata).
- Slot default: 04.00 dan 21.00 WIB. Jadwal minimal 15 menit dari sekarang.
- Upload: `privacyStatus: "private"` + `publishAt` UTC `Z`, `selfDeclaredMadeForKids: false`, bahasa default `en`.
- Komentar kode bahasa Indonesia santai. Commit Conventional Commits 1 baris, tanpa atribusi AI.

## Review Focus

1. Upload kedua kalinya buat run yang sama harus ditolak sebelum ada request ke YouTube → test di Task 3.
2. `HttpError` di tengah upload nggak boleh ninggalin `youtube.json` → test di Task 3.
3. Nulis token ke `.env` nggak boleh ngerusak baris lain (komentar, CRLF, baris kosong) → test di Task 1.
4. Pesan error dari JSON rusak nggak boleh bocorin isi secret → test di Task 1.
5. Slot yang udah kepake di `runs/*/youtube.json` dilewatin → test di Task 2.

---

### Task 1: Config, dependency, `set_env_value`, login

**Files:**
- Modify: `pyproject.toml` (via `uv add`), `mayzfact/config.py`, `.env.example`
- Create: `mayzfact/youtube.py`, `tests/test_youtube.py`

**Interfaces:**
- Produces: `Settings.youtube_client_secret_json: str`, `Settings.youtube_token_json: str`; `youtube.set_env_value(env_file: Path, name: str, value: str) -> None`; `youtube.parse_json_env(name: str, raw: str) -> dict`; `youtube.login(client_secret_json: str, env_file: Path) -> None`; konstanta `SCOPES`, `WIB`.

- [ ] **Step 1: Tambah dependency**

Run: `uv add google-auth-oauthlib google-api-python-client`

- [ ] **Step 2: Tulis test yang gagal** (`tests/test_youtube.py`)

```python
import pytest

from mayzfact import youtube
from mayzfact.config import load_settings
from mayzfact.errors import PipelineError

TOKEN = '{"token": "a", "refresh_token": "r", "client_id": "c", "client_secret": "s"}'


def test_set_env_value_replaces_only_that_line(tmp_path):
    env = tmp_path / ".env"
    env.write_bytes(b"# komentar\r\nGEMINI_MODEL=x\r\n\r\nYOUTUBE_TOKEN_JSON=\r\nBRIEF_PORT=3100\r\n")
    youtube.set_env_value(env, "YOUTUBE_TOKEN_JSON", TOKEN)
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines == ["# komentar", "GEMINI_MODEL=x", "", f"YOUTUBE_TOKEN_JSON='{TOKEN}'", "BRIEF_PORT=3100"]
    assert load_settings(env).youtube_token_json == TOKEN  # python-dotenv bisa baca balik


def test_set_env_value_appends_when_missing(tmp_path):
    env = tmp_path / ".env"
    env.write_text("GEMINI_MODEL=x\n", encoding="utf-8")
    youtube.set_env_value(env, "YOUTUBE_TOKEN_JSON", TOKEN)
    assert env.read_text(encoding="utf-8").splitlines()[-1] == f"YOUTUBE_TOKEN_JSON='{TOKEN}'"


def test_bad_json_env_never_echoes_its_value():
    with pytest.raises(PipelineError) as exc:
        youtube.parse_json_env("YOUTUBE_CLIENT_SECRET_JSON", "{rahasia-banget")
    assert "rahasia" not in str(exc.value) and "YOUTUBE_CLIENT_SECRET_JSON" in str(exc.value)
    with pytest.raises(PipelineError, match="kosong"):
        youtube.parse_json_env("YOUTUBE_CLIENT_SECRET_JSON", "  ")


def test_settings_hide_youtube_secrets_from_repr(tmp_path):
    env = tmp_path / ".env"
    env.write_text(f"YOUTUBE_CLIENT_SECRET_JSON='{TOKEN}'\n", encoding="utf-8")
    settings = load_settings(env)
    assert settings.youtube_client_secret_json == TOKEN and "refresh_token" not in repr(settings)


def test_login_writes_token_to_env(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("YOUTUBE_TOKEN_JSON=\n", encoding="utf-8")
    seen = {}

    class FakeFlow:
        @classmethod
        def from_client_config(cls, config, scopes):
            seen.update(config=config, scopes=scopes)
            return cls()

        def run_local_server(self, port):
            return type("Creds", (), {"to_json": lambda self: TOKEN})()

    monkeypatch.setattr(youtube, "_flow_class", lambda: FakeFlow)
    youtube.login('{"installed": {}}', env)
    assert seen == {"config": {"installed": {}}, "scopes": youtube.SCOPES}
    assert load_settings(env).youtube_token_json == TOKEN
```

- [ ] **Step 3: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_youtube.py -q`
Expected: FAIL (`mayzfact.youtube` belum ada).

- [ ] **Step 4: Implementasi**

`mayzfact/config.py`: ganti `from dataclasses import dataclass` jadi `from dataclasses import dataclass, field`, tambah di akhir `Settings`:

```python
    youtube_client_secret_json: str = field(default="", repr=False)  # JSON OAuth client, jangan pernah di-print
    youtube_token_json: str = field(default="", repr=False)
```

dan di `ENV_FIELDS`:

```python
    "YOUTUBE_CLIENT_SECRET_JSON": ("youtube_client_secret_json", str),
    "YOUTUBE_TOKEN_JSON": ("youtube_token_json", str),
```

`.env.example`: tambah dua baris di akhir:

```
YOUTUBE_CLIENT_SECRET_JSON=
YOUTUBE_TOKEN_JSON=
```

`mayzfact/youtube.py`:

```python
"""Upload terjadwal ke YouTube: login OAuth, metadata, slot jadwal, upload (spec 2026-10-15)."""

from __future__ import annotations

import json
import re
from datetime import timedelta, timezone
from pathlib import Path

from mayzfact.errors import PipelineError

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
WIB = timezone(timedelta(hours=7))  # WIB nggak pakai DST, jadi cukup offset tetap
LOGIN_HINT = "Jalanin: uv run mayzfact login youtube"


def parse_json_env(name: str, raw: str) -> dict:
    """JSON dari .env. Pesan error cuma nyebut nama variabelnya, isinya rahasia."""
    if not raw.strip():
        raise PipelineError("youtube", f"{name} masih kosong di .env")
    try:
        return json.loads(raw)
    except ValueError:
        raise PipelineError("youtube", f"{name} bukan JSON yang valid") from None  # `from None`: error JSON bisa ngutip isinya


def set_env_value(env_file: Path, name: str, value: str) -> None:
    """Ganti baris NAME=... di .env (atau tambah di akhir). Baris lain nggak disentuh."""
    if "'" in value or "\n" in value:
        raise PipelineError("youtube", f"{name} nggak bisa disimpan: ada kutip tunggal atau baris baru")
    pattern = re.compile(rf"^\s*(export\s+)?{re.escape(name)}\s*=")
    lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
    out = [line for line in lines if not pattern.match(line)]
    at = next((i for i, line in enumerate(lines) if pattern.match(line)), None)
    out.insert(len(out) if at is None else at, f"{name}='{value}'")
    tmp = env_file.with_name(env_file.name + ".tmp")
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    tmp.replace(env_file)


def _flow_class():
    from google_auth_oauthlib.flow import InstalledAppFlow

    return InstalledAppFlow


def login(client_secret_json: str, env_file: Path) -> None:
    """Browser kebuka buat izin akun Google, token-nya masuk YOUTUBE_TOKEN_JSON di .env."""
    config = parse_json_env("YOUTUBE_CLIENT_SECRET_JSON", client_secret_json)
    creds = _flow_class().from_client_config(config, SCOPES).run_local_server(port=0)
    set_env_value(env_file, "YOUTUBE_TOKEN_JSON", creds.to_json())
```

Catatan: `out.insert(at, ...)` aman karena baris yang cocok selalu dibuang dari `out`, jadi index `at` (baris cocok pertama) tetap posisi yang benar selama nggak ada duplikat sebelumnya.

- [ ] **Step 5: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_youtube.py tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock mayzfact/config.py mayzfact/youtube.py .env.example tests/test_youtube.py
git commit -m "feat(youtube): add oauth login that stores token in .env"
```

---

### Task 2: Metadata, slot jadwal, body request

**Files:**
- Modify: `mayzfact/youtube.py`, `tests/test_youtube.py`

**Interfaces:**
- Consumes: `WIB` dari Task 1.
- Produces: `UploadMeta` (pydantic); `load_meta(paths: RunPaths) -> UploadMeta`; `taken_slots(runs_dir: Path) -> list[datetime]`; `next_slot(taken: list[datetime], now: datetime) -> datetime`; `parse_publish_at(text: str, now: datetime) -> datetime`; `video_body(meta: UploadMeta, publish_at: datetime) -> dict`.

- [ ] **Step 1: Tulis test yang gagal** (tambah ke `tests/test_youtube.py`)

```python
from datetime import datetime

from mayzfact.store import RunPaths, write_json_atomic

META = {"title": "5 Birds With Real Superpowers #Shorts", "description": "Birds that break the rules.\n#birds",
        "tags": ["birds", "animals"], "category_id": "15"}


def wib(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=youtube.WIB)


@pytest.mark.parametrize("bad", [{"title": "x" * 101}, {"title": "a <b>"}, {"description": "a > b"},
                                 {"tags": ["x" * 300, "y" * 300]}, {"category_id": "pets"}])
def test_upload_meta_rejects_bad_fields(bad):
    with pytest.raises(ValueError):
        youtube.UploadMeta(**{**META, **bad})


def test_load_meta_reports_problems(tmp_path):
    paths = RunPaths(tmp_path)
    with pytest.raises(PipelineError, match="upload.json"):
        youtube.load_meta(paths)
    write_json_atomic(paths.root / "upload.json", {**META, "title": ""})
    with pytest.raises(PipelineError, match="title"):
        youtube.load_meta(paths)
    write_json_atomic(paths.root / "upload.json", META)
    assert youtube.load_meta(paths).category_id == "15"


def test_next_slot_skips_taken_and_too_soon():
    now = wib("2026-10-15 20:50")  # 21.00 cuma 10 menit lagi → lewat
    assert youtube.next_slot([], now) == wib("2026-10-16 04:00")
    assert youtube.next_slot([wib("2026-10-16 04:00")], now) == wib("2026-10-16 21:00")
    assert youtube.next_slot([], wib("2026-10-15 12:00")) == wib("2026-10-15 21:00")


def test_taken_slots_reads_uploaded_runs(tmp_path):
    write_json_atomic(tmp_path / "a" / "youtube.json", {"publish_at": "2026-10-15T21:00:00+07:00"})
    (tmp_path / "b").mkdir()
    assert youtube.taken_slots(tmp_path) == [wib("2026-10-15 21:00")]


def test_parse_publish_at_is_wib_and_in_the_future():
    now = wib("2026-10-15 12:00")
    assert youtube.parse_publish_at("2026-10-15 21:00", now) == wib("2026-10-15 21:00")
    for bad in ("2026-10-15 12:10", "15-10-2026 21:00", "besok"):
        with pytest.raises(PipelineError):
            youtube.parse_publish_at(bad, now)


def test_video_body_schedules_private_video():
    body = youtube.video_body(youtube.UploadMeta(**META), wib("2026-10-15 21:00"))
    assert body["status"] == {"privacyStatus": "private", "publishAt": "2026-10-15T14:00:00Z",
                              "selfDeclaredMadeForKids": False}
    assert body["snippet"] == {"title": META["title"], "description": META["description"], "tags": META["tags"],
                               "categoryId": "15", "defaultLanguage": "en", "defaultAudioLanguage": "en"}
```

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_youtube.py -q`
Expected: FAIL (`UploadMeta` belum ada).

- [ ] **Step 3: Implementasi** (tambah ke `mayzfact/youtube.py`; gabungin import di atas)

```python
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ValidationError, field_validator

from mayzfact.store import RunPaths, read_json

SLOT_HOURS = (4, 21)
MIN_LEAD = timedelta(minutes=15)


class UploadMeta(BaseModel):
    """Isi runs/<id>/upload.json yang ditulis agent. Batasnya ngikutin YouTube Data API."""

    title: str
    description: str
    tags: list[str] = []
    category_id: str
    language: str = "en"

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= 100:
            raise ValueError("judul harus 1–100 karakter")
        if "<" in value or ">" in value:
            raise ValueError("judul nggak boleh ada < atau >")
        return value

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 5000:
            raise ValueError("deskripsi maksimal 5000 byte")
        if "<" in value or ">" in value:
            raise ValueError("deskripsi nggak boleh ada < atau >")
        return value

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: list[str]) -> list[str]:
        value = [tag.strip() for tag in value if tag.strip()]
        if len(",".join(value)) > 500:
            raise ValueError("total tag maksimal 500 karakter")
        return value

    @field_validator("category_id")
    @classmethod
    def _category(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("category_id harus angka, misal 15")
        return value


def load_meta(paths: RunPaths) -> UploadMeta:
    path = paths.root / "upload.json"
    if not path.exists():
        raise PipelineError("upload", f"{path} belum ada. Agent harus nulis metadata-nya dulu.")
    try:
        return UploadMeta(**read_json(path))
    except (ValidationError, TypeError) as exc:
        raise PipelineError("upload", f"upload.json nggak valid: {exc}") from exc


def taken_slots(runs_dir: Path) -> list[datetime]:
    """Jadwal video yang udah ke-upload, dari runs/*/youtube.json."""
    out = []
    for path in sorted(runs_dir.glob("*/youtube.json")):
        try:
            out.append(datetime.fromisoformat(read_json(path)["publish_at"]))
        except (KeyError, ValueError, TypeError):
            continue
    return out


def next_slot(taken: list[datetime], now: datetime) -> datetime:
    """Slot 04.00/21.00 WIB pertama yang belum kepake dan minimal 15 menit dari sekarang."""
    used = {t.astimezone(WIB) for t in taken}
    start = now.astimezone(WIB).replace(hour=0, minute=0, second=0, microsecond=0)
    for day in range(366):
        for hour in SLOT_HOURS:
            slot = start + timedelta(days=day, hours=hour)
            if slot >= now + MIN_LEAD and slot not in used:
                return slot
    raise PipelineError("upload", "Nggak ada slot kosong setahun ke depan")


def parse_publish_at(text: str, now: datetime) -> datetime:
    """'YYYY-MM-DD HH:MM' dibaca sebagai WIB."""
    try:
        when = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=WIB)
    except ValueError:
        raise PipelineError("upload", f'Format jam salah: {text!r}. Contoh: "2026-10-15 21:00" (WIB)') from None
    if when < now + MIN_LEAD:
        raise PipelineError("upload", f"Jadwal {text} WIB terlalu dekat atau udah lewat (minimal 15 menit dari sekarang)")
    return when


def video_body(meta: UploadMeta, publish_at: datetime) -> dict:
    return {
        "snippet": {
            "title": meta.title, "description": meta.description, "tags": meta.tags, "categoryId": meta.category_id,
            "defaultLanguage": meta.language, "defaultAudioLanguage": meta.language,
        },
        "status": {
            "privacyStatus": "private",  # private + publishAt = terjadwal; YouTube yang bikin public di jamnya
            "publishAt": publish_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "selfDeclaredMadeForKids": False,
        },
    }
```

- [ ] **Step 4: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_youtube.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/youtube.py tests/test_youtube.py
git commit -m "feat(youtube): validate upload metadata and pick schedule slots"
```

---

### Task 3: Upload resumable

**Files:**
- Modify: `mayzfact/youtube.py`, `tests/test_youtube.py`

**Interfaces:**
- Consumes: `video_body`, `WIB`, `LOGIN_HINT`, `parse_json_env` dari Task 1–2.
- Produces: `service(token_json: str) -> Any`; `upload_video(paths: RunPaths, meta: UploadMeta, publish_at: datetime, make_service: Callable[[], Any], log: Callable[[str], None]) -> dict` (isi `youtube.json`: `video_id`, `url`, `studio_url`, `publish_at`, `uploaded_at`).

- [ ] **Step 1: Tulis test yang gagal**

```python
import httplib2
from googleapiclient.errors import HttpError

from mayzfact.store import read_json


class FakeRequest:
    def __init__(self, error=None):
        self.error, self.calls = error, 0

    def next_chunk(self, num_retries=0):
        self.calls += 1
        if self.error:
            raise self.error
        if self.calls == 1:
            return type("Status", (), {"progress": lambda self: 0.5})(), None
        return None, {"id": "abc123"}


class FakeService:
    def __init__(self, request):
        self.request, self.inserted = request, []

    def videos(self):
        return self

    def insert(self, part, body, media_body):
        self.inserted.append((part, body))
        return self.request


def ready_run(tmp_path):
    paths = RunPaths(tmp_path / "vid")
    paths.root.mkdir()
    paths.final_mp4.write_bytes(b"mp4")
    return paths


def test_upload_writes_result_and_logs_progress(tmp_path):
    paths, logs = ready_run(tmp_path), []
    fake = FakeService(FakeRequest())
    data = youtube.upload_video(paths, youtube.UploadMeta(**META), wib("2026-10-15 21:00"), lambda: fake, logs.append)
    assert data["video_id"] == "abc123" and data["url"] == "https://youtube.com/shorts/abc123"
    assert data["studio_url"] == "https://studio.youtube.com/video/abc123/edit"
    assert data["publish_at"] == "2026-10-15T21:00:00+07:00"
    assert read_json(paths.root / "youtube.json") == data
    assert fake.inserted[0][0] == "snippet,status" and fake.inserted[0][1]["status"]["privacyStatus"] == "private"
    assert any("50%" in line for line in logs)


def test_upload_refuses_second_upload_without_calling_youtube(tmp_path):
    paths = ready_run(tmp_path)
    write_json_atomic(paths.root / "youtube.json", {"url": "https://youtube.com/shorts/old"})
    called = []
    with pytest.raises(PipelineError, match="shorts/old"):
        youtube.upload_video(paths, youtube.UploadMeta(**META), wib("2026-10-15 21:00"), lambda: called.append(1), print)
    assert called == []


def test_upload_needs_final_mp4(tmp_path):
    paths = RunPaths(tmp_path / "vid")
    paths.root.mkdir()
    with pytest.raises(PipelineError, match="final.mp4"):
        youtube.upload_video(paths, youtube.UploadMeta(**META), wib("2026-10-15 21:00"), lambda: None, print)


def test_youtube_error_leaves_no_result(tmp_path):
    paths = ready_run(tmp_path)
    error = HttpError(httplib2.Response({"status": 403}), b'{"error": {"message": "quotaExceeded"}}')
    with pytest.raises(PipelineError, match="403"):
        youtube.upload_video(paths, youtube.UploadMeta(**META), wib("2026-10-15 21:00"),
                             lambda: FakeService(FakeRequest(error)), print)
    assert not (paths.root / "youtube.json").exists()


def test_service_needs_login():
    with pytest.raises(PipelineError, match="login youtube"):
        youtube.service("")
```

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_youtube.py -q`
Expected: FAIL (`upload_video` belum ada).

- [ ] **Step 3: Implementasi** (tambah ke `mayzfact/youtube.py`)

```python
from typing import Any, Callable

from mayzfact.store import write_json_atomic

CHUNK = 8 * 1024 * 1024


def service(token_json: str) -> Any:
    """Client YouTube Data API. Access token di-refresh otomatis; refresh token-nya tetap, jadi .env nggak ditulis ulang."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not token_json.strip():
        raise PipelineError("youtube", f"Belum login YouTube. {LOGIN_HINT}")
    creds = Credentials.from_authorized_user_info(parse_json_env("YOUTUBE_TOKEN_JSON", token_json), SCOPES)
    if not creds.valid:
        try:
            creds.refresh(Request())
        except RefreshError:
            raise PipelineError("youtube", f"Token YouTube ditolak (dicabut atau expired). Login ulang. {LOGIN_HINT}") from None
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_video(paths: RunPaths, meta: UploadMeta, publish_at: datetime, make_service: Callable[[], Any],
                 log: Callable[[str], None]) -> dict:
    """Upload final.mp4 sebagai video terjadwal. Semua cek lokal dulu, baru nyentuh YouTube."""
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    out = paths.root / "youtube.json"
    if out.exists():
        old = read_json(out).get("url", "?")
        raise PipelineError("upload", f"Video ini udah pernah di-upload: {old}. Mau upload ulang? Hapus {out} dulu.")
    if not paths.final_mp4.exists():
        raise PipelineError("upload", f"{paths.final_mp4} belum ada. Render dulu.")
    media = MediaFileUpload(str(paths.final_mp4), mimetype="video/mp4", chunksize=CHUNK, resumable=True)
    request = make_service().videos().insert(part="snippet,status", body=video_body(meta, publish_at), media_body=media)
    response = None
    try:
        while response is None:
            status, response = request.next_chunk(num_retries=3)
            if status:
                log(f"[upload] {int(status.progress() * 100)}%")
    except HttpError as exc:
        reason = getattr(exc, "reason", "") or ""
        raise PipelineError("upload", f"YouTube nolak upload ({getattr(exc, 'status_code', '?')}): {reason}") from exc
    except OSError as exc:
        raise PipelineError("upload", f"Koneksi putus pas upload: {exc}. Aman dicoba lagi.") from exc
    video_id = response["id"]
    data = {
        "video_id": video_id,
        "url": f"https://youtube.com/shorts/{video_id}",
        "studio_url": f"https://studio.youtube.com/video/{video_id}/edit",
        "publish_at": publish_at.astimezone(WIB).isoformat(),
        "uploaded_at": datetime.now(WIB).isoformat(timespec="seconds"),
    }
    write_json_atomic(out, data)
    return data
```

- [ ] **Step 4: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_youtube.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/youtube.py tests/test_youtube.py
git commit -m "feat(youtube): resumable scheduled upload with duplicate guard"
```

---

### Task 4: CLI

**Files:**
- Modify: `mayzfact/cli.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: semua fungsi `youtube.*` di atas, `PROJECT_ROOT` dari config.

- [ ] **Step 1: Tulis test yang gagal** (tambah ke `tests/test_cli.py`)

```python
def test_login_youtube_writes_into_project_env(monkeypatch):
    from mayzfact import youtube

    seen = {}
    monkeypatch.setattr(cli, "load_settings", lambda: Settings(youtube_client_secret_json='{"installed": {}}'))
    monkeypatch.setattr(youtube, "login", lambda secret, env: seen.update(secret=secret, env=env))
    assert cli.main(["login", "youtube"]) == 0
    assert seen["secret"] == '{"installed": {}}' and seen["env"].name == ".env"


def test_next_slot_prints_wib_time(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["next-slot"]) == 0
    out = capsys.readouterr().out.strip()
    assert out.endswith(("04:00", "21:00")) and len(out) == len("2026-10-15 21:00")


def test_upload_without_login_fails_cleanly(monkeypatch, tmp_path, capsys):
    from mayzfact.store import write_json_atomic

    paths = RunPaths(tmp_path / "NSua7RPoFJg")
    paths.root.mkdir()
    paths.final_mp4.write_bytes(b"mp4")
    write_json_atomic(paths.root / "upload.json", {"title": "T #Shorts", "description": "d", "tags": [], "category_id": "15"})
    monkeypatch.setattr(cli, "load_settings", lambda: Settings())
    monkeypatch.setattr(cli, "RUNS_DIR", tmp_path)
    assert cli.main(["upload", "NSua7RPoFJg", "--at", "2099-01-01 21:00"]) == 1
    assert "login youtube" in capsys.readouterr().err
```

- [ ] **Step 2: Jalanin, pastiin gagal**

Run: `uv run pytest tests/test_cli.py -q`
Expected: FAIL (`youtube` bukan pilihan `login`, `next-slot` belum ada).

- [ ] **Step 3: Implementasi** (`mayzfact/cli.py`)

Import: `from mayzfact.config import PROJECT_ROOT, RUNS_DIR, Settings, load_settings, missing_env` dan `from datetime import datetime`.

Parser:

```python
    login = sub.add_parser("login", help="Login ke platform hook (TikTok/Douyin/Pinterest) atau YouTube buat upload")
    login.add_argument("platform", nargs="?", choices=sorted([*PLATFORMS, "youtube"]))
    ...
    sub.add_parser("next-slot", help="Slot jadwal YouTube kosong berikutnya (04.00/21.00 WIB)")
    upload = sub.add_parser("upload", help="Upload final.mp4 ke YouTube sebagai video terjadwal")
    upload.add_argument("video", help="Video ID atau URL YouTube source")
    upload.add_argument("--at", required=True, help='Jam tayang WIB, format "YYYY-MM-DD HH:MM"')
```

Dispatch di `main` (sebelum `run_pipeline`):

```python
        if args.command == "next-slot":
            return _next_slot()
        if args.command == "upload":
            return _upload(args, settings)
```

Di awal `_login`, setelah blok `--check`:

```python
    if args.platform == "youtube":
        from mayzfact import youtube

        youtube.login(settings.youtube_client_secret_json, PROJECT_ROOT / ".env")
        print("YouTube: login berhasil, token disimpan di .env")
        return 0
```

Fungsi baru:

```python
def _next_slot() -> int:
    from mayzfact import youtube

    print(youtube.next_slot(youtube.taken_slots(RUNS_DIR), datetime.now(youtube.WIB)).strftime("%Y-%m-%d %H:%M"))
    return 0


def _upload(args: argparse.Namespace, settings: Settings) -> int:
    from mayzfact import youtube
    from mayzfact.steps.source import parse_video_id

    paths = RunPaths(RUNS_DIR / parse_video_id(args.video))
    meta = youtube.load_meta(paths)
    publish_at = youtube.parse_publish_at(args.at, datetime.now(youtube.WIB))
    data = youtube.upload_video(paths, meta, publish_at, lambda: youtube.service(settings.youtube_token_json), print)
    print(f"Ke-upload, tayang {args.at} WIB\n  Video : {data['url']}\n  Studio: {data['studio_url']}")
    return 0
```

(`RunPaths` kalau belum di-import di `cli.py`: `from mayzfact.store import RunPaths`.)

- [ ] **Step 4: Jalanin, pastiin lolos**

Run: `uv run pytest tests/test_cli.py tests/test_youtube.py -q`, terus `uvx ruff check --select F,I mayzfact/cli.py mayzfact/youtube.py mayzfact/config.py tests/test_cli.py tests/test_youtube.py`
Expected: PASS, lint bersih.

- [ ] **Step 5: Commit**

```bash
git add mayzfact/cli.py tests/test_cli.py
git commit -m "feat(cli): add youtube login, next-slot and upload commands"
```

---

### Task 5: Skill, AGENTS, docs

**Files:**
- Modify: `.agents/skills/bikin-short/SKILL.md`, `AGENTS.md`, `README.md`, `docs/DECISIONS.md`, `docs/HANDOFF.md`

- [ ] **Step 1: Skill `bikin-short`** — ganti bagian "## 6. Metadata upload" dan "## 7. Checkpoint: Akmal upload" jadi:

```markdown
## 6. Metadata YouTube

Agent nulis `runs/<id>/upload.json` dari `script.json` dan `clips.json`:

```json
{"title": "...", "description": "...", "tags": ["..."], "category_id": "15", "language": "en"}
```

- **title:** bahasa Inggris, maksimal 100 karakter, ada `#Shorts`, tanpa `<` `>`. Jangan clickbait yang nggak ada di video.
- **description:** 1–2 kalimat ringkasan, hashtag, terus credit: satu baris per sumber klip yang beda dari `clips.json` (`provider` + `page_url`, + `author` kalau ada; lewati `upload` tanpa `page_url`). Maksimal 5000 byte, tanpa `<` `>`.
- **tags:** 5–10 tag topik, total maksimal 500 karakter.
- **category_id:** pilih sesuai isi, misal `15` Pets & Animals, `27` Education, `28` Science & Technology, `24` Entertainment.

## 7. Checkpoint: konfirmasi jadwal

Jalanin `uv run mayzfact next-slot`. Tunjukin ke Akmal judul + jam usulan (WIB), terus tanya: jadwalin jam segitu atau jam lain? Tunggu jawabannya. Jangan upload sebelum Akmal konfirmasi.

## 8. Upload

Jalanin di background:

```bash
uv run mayzfact upload <id> --at "<YYYY-MM-DD HH:MM>"
```

- Kalau error "Belum login YouTube" / "Token YouTube ditolak": minta Akmal jalanin `uv run mayzfact login youtube` (browser kebuka buat izin akun), terus ulang.
- Kalau error "udah pernah di-upload": jangan hapus `youtube.json` sendiri, tanya Akmal.
- Sukses: kasih Akmal link video dan link YouTube Studio dari output-nya.
```

Ubah juga alur di atas skill jadi: `… → render → **[Akmal cek final]** → metadata → **[Akmal konfirmasi jam]** → upload`, dan `description` frontmatter nambah "upload terjadwal ke YouTube".

- [ ] **Step 2: `AGENTS.md`**
  - Bagian Perintah: tambah `uv run mayzfact login youtube`, `uv run mayzfact next-slot`, `uv run mayzfact upload <id> --at "YYYY-MM-DD HH:MM"`.
  - File penting: tambah `upload.json` (metadata dari agent) dan `youtube.json` (hasil upload; jangan dihapus tanpa izin Akmal).
  - Keamanan: tambah "Jangan print isi `YOUTUBE_CLIENT_SECRET_JSON` / `YOUTUBE_TOKEN_JSON`." dan "Upload ke YouTube itu aksi keluar: jalanin `mayzfact upload` cuma setelah Akmal konfirmasi jamnya."
  - Ganti kalimat "Teks di luar pipeline, misalnya metadata upload, boleh ditulis agent." tetap, tapi sebut `upload.json`.

- [ ] **Step 3: `README.md`** — tambah bagian "## Upload ke YouTube": login sekali (`mayzfact login youtube`), `next-slot`, `upload --at` WIB, isi `upload.json`.

- [ ] **Step 4: `docs/DECISIONS.md`** — tambah D-027 "Upload terjadwal lewat YouTube Data API" (status accepted, ngegantiin D-025 poin 4; project Google Cloud udah lolos audit; token di `.env`; private + `publishAt`; konfirmasi jam wajib; authority Akmal chat 2026-10-15). Ubah status D-025 jadi "Poin 4 diganti D-027".

- [ ] **Step 5: `docs/HANDOFF.md`** — tambah section "Handoff — Upload terjadwal ke YouTube": yang selesai, test, dan "Belum dites: login + upload beneran (upload pertama Akmal jadi tesnya)".

- [ ] **Step 6: Full test + commit**

Run: `uv run pytest -q`
Expected: semua lolos.

```bash
git add .agents/skills/bikin-short/SKILL.md AGENTS.md README.md docs/DECISIONS.md docs/HANDOFF.md
git commit -m "docs: add youtube upload flow to agent guide and skill"
```
