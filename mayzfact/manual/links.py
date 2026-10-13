"""links.json: link/file per shot yang diisi Akmal lewat halaman brief (spec metode manual bagian 4)."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from mayzfact.store import read_json, write_json_atomic

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_URL = re.compile(r"https?://[^\s，。！？、]+", re.IGNORECASE)
_PICK = re.compile(r"\s+#(\d+)\s*$")


def parse_entry(text: str) -> tuple[str, int | None]:
    """'<teks share> https://… #3' → ('https://…', 3). Teks share Douyin/RedNote dibuang."""
    text = text.strip()
    pick = None
    match = _PICK.search(text)
    if match:
        pick = int(match.group(1))
        text = text[: match.start()].strip()
    url = _URL.search(text)
    return (url.group(0) if url else text), pick


def link_kind(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "douyin.com" in host or "iesdouyin.com" in host:
        return "douyin"
    if any(h in host for h in ("xiaohongshu.com", "xhslink.com", "xhslink.cn", "rednote.com")):
        return "rednote"
    if "tiktok.com" in host:
        return "tiktok"
    if "pinterest." in host or host == "pin.it":
        return "pinterest"
    if PurePosixPath(parsed.path).suffix.lower() in VIDEO_EXTS | IMAGE_EXTS:
        return "direct"
    return "other"


def load_links(path: Path) -> dict:
    return read_json(path) if path.exists() else {"shots": {}}


def save_links(path: Path, data: dict) -> None:
    write_json_atomic(path, data)


def normalize_links(raw: dict, shot_count: int) -> dict:
    shots: dict[str, dict] = {}
    for key, entry in (raw.get("shots") or {}).items():
        number = int(key)
        if not 1 <= number <= shot_count:
            raise ValueError(f"shot {number} nggak ada di plan (1-{shot_count})")
        if not isinstance(entry, dict):
            continue
        out: dict = {}
        url_text = str(entry.get("url") or "").strip()
        file = str(entry.get("file") or "").strip()
        if url_text:
            url, pick = parse_entry(url_text)
            if not url.lower().startswith(("http://", "https://")):
                raise ValueError(f"shot {number}: link harus diawali http(s)://")
            out["url"] = url
            pick = entry.get("pick") or pick
        elif file:
            if not file.startswith("manual/") or ".." in file:
                raise ValueError(f"shot {number}: file harus di folder manual/")
            out["file"] = file
            pick = entry.get("pick")
        else:
            continue
        if pick:
            out["pick"] = int(pick)
        shots[str(number)] = out
    return {"shots": shots}


def missing_shots(plan: dict, links: dict) -> list[int]:
    filled = links.get("shots", {})
    return [shot["index"] + 1 for shot in plan["shots"] if not filled.get(str(shot["index"] + 1))]
