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


_TIME_RANGE = re.compile(
    r"(?:\s+@(?P<at_start>\d+(?:\.\d+)?)(?:s)?(?:\s*-\s*(?P<at_end>\d+(?:\.\d+)?)(?:s)?)?|"
    r"\s+#(?P<hash_start>\d+(?:\.\d+)?)(?:s)?\s*-\s*(?P<hash_end>\d+(?:\.\d+)?)(?:s)?|"
    r"\s+#(?P<hash_single>\d+(?:\.\d+)?)[sS])\s*$"
)


def parse_time_range(text: str) -> tuple[str, float | None, float | None]:
    """Cari @start[-end], #start-end, atau #starts di akhir string."""
    text = text.strip()
    match = _TIME_RANGE.search(text)
    if not match:
        return text, None, None
    d = match.groupdict()
    if d.get("at_start") is not None:
        start_s = float(d["at_start"])
        end_s = float(d["at_end"]) if d.get("at_end") is not None else None
    elif d.get("hash_start") is not None:
        start_s = float(d["hash_start"])
        end_s = float(d["hash_end"]) if d.get("hash_end") is not None else None
    elif d.get("hash_single") is not None:
        start_s = float(d["hash_single"])
        end_s = None
    else:
        return text, None, None
    clean = text[: match.start()].strip()
    return clean, start_s, end_s


def parse_entry(text: str) -> tuple[str, int | None]:
    """'<teks share> https://… #3' → ('https://…', 3). Teks share (Douyin dll) dibuang."""
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
    if "shots" in data or "groups" in data:
        return data
    return {"groups": {}}


def save_links(path: Path, data: dict) -> None:
    write_json_atomic(path, data)


def _format_time(s: float) -> str:
    return f"{s:g}"


def _entry(line: str, where: str) -> dict:
    line, start_s, end_s = parse_time_range(line)
    if start_s is not None and start_s < 0:
        raise ValueError(f"{where}: detik mulai harus >= 0")
    if end_s is not None and end_s <= start_s:
        raise ValueError(f"{where}: detik selesai ({_format_time(end_s)}) harus lebih besar dari mulai ({_format_time(start_s)})")

    if line.startswith("file:"):
        file = line[len("file:"):].strip()
        if not file.startswith("manual/") or ".." in file:
            raise ValueError(f"{where}: file harus di folder manual/")
        entry = {"file": file}
    else:
        url, pick = parse_entry(line)
        if not url.lower().startswith(("http://", "https://")):
            raise ValueError(f"{where}: link harus diawali http(s)://")
        if link_kind(url) == "rednote":  # D-022: note RedNote minta login, link-nya nggak bisa di-download
            raise ValueError(f"{where}: link RedNote nggak dipakai (butuh login). Save file-nya dari app, terus upload")
        if pick is not None and pick < 1:
            raise ValueError(f"{where}: #n mulai dari #1")
        entry = {"url": url, "pick": pick} if pick else {"url": url}

    if start_s is not None:
        entry["start_s"] = start_s
    if end_s is not None:
        entry["end_s"] = end_s
    return entry


def lines_of(entries: list[dict]) -> str:
    """Kebalikan dari normalize: entry → teks textarea (1 baris = 1 link/file)."""
    lines = []
    for e in entries:
        base = f"file:{e['file']}" if e.get("file") else e["url"]
        if e.get("pick"):
            base += f" #{e['pick']}"
        start_s = e.get("start_s")
        end_s = e.get("end_s")
        if start_s is not None:
            if end_s is not None:
                base += f" @{_format_time(start_s)}-{_format_time(end_s)}"
            else:
                base += f" @{_format_time(start_s)}"
        lines.append(base)
    return "\n".join(lines)



def normalize_links(raw: dict, group_ids: list[str] | None = None, shot_count: int | None = None) -> dict:
    """{"shots": {idx: link_string | entry}} atau legacy {"groups": {gid: lines}}."""
    if "shots" in raw:
        shots: dict[str, dict] = {}
        for key, value in (raw.get("shots") or {}).items():
            try:
                idx = int(key)
            except (ValueError, TypeError):
                raise ValueError(f"index shot {key} nggak valid")
            if shot_count is not None and (idx < 0 or idx >= shot_count):
                raise ValueError(f"shot {idx + 1 if idx >= 0 else idx} nggak ada di plan")
            if isinstance(value, str):
                line = value.strip()
                if not line:
                    continue
                entry = _entry(line, f"shot {idx + 1}")
            elif isinstance(value, dict):
                entry = value
            else:
                continue
            shots[str(idx)] = entry
        return {"shots": shots}

    groups: dict[str, list[dict]] = {}
    valid_groups = group_ids or []
    for gid, value in (raw.get("groups") or {}).items():
        if valid_groups and gid not in valid_groups:
            raise ValueError(f"kelompok {gid} nggak ada di plan")
        lines = value.splitlines() if isinstance(value, str) else [lines_of([v]) for v in value if isinstance(v, dict)]
        entries = [_entry(line.strip(), f"kelompok {gid} baris {n}") for n, line in enumerate(lines, 1) if line.strip()]
        if entries:
            groups[gid] = entries
    return {"groups": groups}


def missing_groups(plan: dict, links: dict) -> list[str]:
    filled = links.get("groups", {})
    return [group["id"] for group in plan["groups"] if not filled.get(group["id"])]


def missing_shots(plan: dict, links: dict) -> list[int]:
    filled = links.get("shots", {})
    return [s["index"] for s in plan.get("shots", []) if str(s["index"]) not in filled]
