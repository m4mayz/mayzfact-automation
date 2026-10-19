"""Upload terjadwal ke YouTube: login OAuth, metadata, slot jadwal, upload (spec 2026-10-15)."""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import datetime, timedelta, timezone
from http.client import HTTPException
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, field_validator

from mayzfact.errors import PipelineError
from mayzfact.store import (
    REPLACE_TRIES,
    REPLACE_WAIT_S,
    RunPaths,
    read_json,
    write_json_atomic,
)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
WIB = timezone(timedelta(hours=7))  # WIB nggak pakai DST, jadi cukup offset tetap
LOGIN_HINT = "Jalanin: uv run mayzfact login youtube"
SLOT_HOURS = (1, 4)
MIN_LEAD = timedelta(minutes=15)
CHUNK = 8 * 1024 * 1024


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
    # mkstemp: nama unik + permission owner-only (0600), soalnya isinya semua secret di .env
    fd, tmp = tempfile.mkstemp(dir=env_file.parent, prefix=".env.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "\n")
        for attempt in range(REPLACE_TRIES):
            try:
                os.replace(tmp, env_file)
                return
            except PermissionError:  # Windows: .env lagi dibuka proses lain
                if attempt == REPLACE_TRIES - 1:
                    raise PipelineError("youtube", f"{env_file.name} lagi dikunci proses lain, {name} nggak kesimpen. "
                                        "Tutup yang lagi buka file itu, terus login ulang.") from None
                time.sleep(REPLACE_WAIT_S)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _flow_class():
    from google_auth_oauthlib.flow import InstalledAppFlow

    return InstalledAppFlow


def login(client_secret_json: str, env_file: Path) -> None:
    """Browser kebuka buat izin akun Google, token-nya masuk YOUTUBE_TOKEN_JSON di .env."""
    config = parse_json_env("YOUTUBE_CLIENT_SECRET_JSON", client_secret_json)
    creds = _flow_class().from_client_config(config, SCOPES).run_local_server(port=0)
    set_env_value(env_file, "YOUTUBE_TOKEN_JSON", creds.to_json())


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
    except (ValueError, TypeError) as exc:
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
    """Slot 01.00/04.00 WIB pertama yang belum kepake dan minimal 15 menit dari sekarang."""
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


def video_body(meta: UploadMeta, publish_at: datetime | None) -> dict:
    """publish_at None = langsung public sekarang, tanpa jadwal."""
    if publish_at is None:
        status = {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    else:
        status = {
            "privacyStatus": "private",  # private + publishAt = terjadwal; YouTube yang bikin public di jamnya
            "publishAt": publish_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "selfDeclaredMadeForKids": False,
        }
    return {
        "snippet": {
            "title": meta.title, "description": meta.description, "tags": meta.tags, "categoryId": meta.category_id,
            "defaultLanguage": meta.language, "defaultAudioLanguage": meta.language,
        },
        "status": status,
    }


def service(token_json: str) -> Any:
    """Client YouTube Data API. Access token di-refresh otomatis; refresh token-nya tetap, jadi .env nggak ditulis ulang."""
    from google.auth.exceptions import GoogleAuthError, RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not token_json.strip():
        raise PipelineError("youtube", f"Belum login YouTube. {LOGIN_HINT}")
    info = parse_json_env("YOUTUBE_TOKEN_JSON", token_json)
    try:
        creds = Credentials.from_authorized_user_info(info, SCOPES)
    except ValueError:
        raise PipelineError("youtube", f"YOUTUBE_TOKEN_JSON nggak lengkap. Login ulang. {LOGIN_HINT}") from None
    if not creds.valid:
        try:
            creds.refresh(Request())
        except RefreshError:
            raise PipelineError("youtube", f"Token YouTube ditolak (dicabut atau expired). Login ulang. {LOGIN_HINT}") from None
        except GoogleAuthError as exc:  # TransportError: offline / DNS putus
            raise PipelineError("youtube", f"Nggak bisa nyambung ke Google buat refresh token ({type(exc).__name__}). "
                                "Cek koneksi internet, terus coba lagi.") from None
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_video(paths: RunPaths, meta: UploadMeta, publish_at: datetime | None, make_service: Callable[[], Any],
                 log: Callable[[str], None]) -> dict:
    """Upload final.mp4 sebagai video terjadwal. Semua cek lokal dulu, baru nyentuh YouTube."""
    from google.auth.exceptions import GoogleAuthError
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    from httplib2 import HttpLib2Error

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
    except (OSError, HTTPException, HttpLib2Error, GoogleAuthError) as exc:
        # Kalau putusnya pas chunk terakhir, videonya bisa udah masuk walau response-nya ilang.
        raise PipelineError("upload", f"Koneksi ke YouTube putus pas upload ({type(exc).__name__}). Cek YouTube Studio "
                            "dulu sebelum upload ulang, bisa jadi videonya udah masuk.") from exc
    video_id = response["id"]
    uploaded = datetime.now(WIB)
    data = {
        "video_id": video_id,
        "url": f"https://youtube.com/shorts/{video_id}",
        "studio_url": f"https://studio.youtube.com/video/{video_id}/edit",
        "publish_at": (publish_at or uploaded).astimezone(WIB).isoformat(timespec="seconds"),
        "uploaded_at": uploaded.isoformat(timespec="seconds"),
    }
    write_json_atomic(out, data)
    return data
