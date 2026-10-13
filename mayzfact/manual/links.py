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
    data = read_json(path) if path.exists() else {}
    return data if "groups" in data else {"groups": {}}  # format lama per shot diabaikan


def save_links(path: Path, data: dict) -> None:
    write_json_atomic(path, data)


def _entry(line: str, where: str) -> dict:
    if line.startswith("file:"):
        file = line[len("file:"):].strip()
        if not file.startswith("manual/") or ".." in file:
            raise ValueError(f"{where}: file harus di folder manual/")
        return {"file": file}
    url, pick = parse_entry(line)
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError(f"{where}: link harus diawali http(s)://")
    if pick is not None and pick < 1:
        raise ValueError(f"{where}: #n mulai dari #1")
    return {"url": url, "pick": pick} if pick else {"url": url}


def lines_of(entries: list[dict]) -> str:
    """Kebalikan dari normalize: entry → teks textarea (1 baris = 1 link/file)."""
    return "\n".join(
        f"file:{e['file']}" if e.get("file") else e["url"] + (f" #{e['pick']}" if e.get("pick") else "") for e in entries
    )


def normalize_links(raw: dict, group_ids: list[str]) -> dict:
    """{"groups": {id: teks textarea | list entry}} → {"groups": {id: [entry, …]}}. Kelompok kosong dibuang."""
    groups: dict[str, list[dict]] = {}
    for gid, value in (raw.get("groups") or {}).items():
        if gid not in group_ids:
            raise ValueError(f"kelompok {gid} nggak ada di plan")
        lines = value.splitlines() if isinstance(value, str) else [lines_of([v]) for v in value if isinstance(v, dict)]
        entries = [_entry(line.strip(), f"kelompok {gid} baris {n}") for n, line in enumerate(lines, 1) if line.strip()]
        if entries:
            groups[gid] = entries
    return {"groups": groups}


def missing_groups(plan: dict, links: dict) -> list[str]:
    filled = links.get("groups", {})
    return [group["id"] for group in plan["groups"] if not filled.get(group["id"])]
