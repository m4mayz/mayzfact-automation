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
                entry = {k: v for k, v in value.items() if k != "sfx"}  # SFX cuma lewat attach_sfx (dicek dulu)
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


def attach_sfx(data: dict, raw_sfx: dict | None, names: set[str], plan: dict) -> None:
    """SFX kustom dari brief {idx: {"file", "at_s"} | None} → entry["sfx"]. Shot tanpa link: SFX-nya dibuang."""
    durations = {s["index"]: s["end_s"] - s["start_s"] for s in plan.get("shots", [])}
    for key, value in (raw_sfx or {}).items():
        entry = data.get("shots", {}).get(str(key))
        if not value or entry is None:
            continue
        idx = int(key)
        file, at_s = value.get("file"), float(value.get("at_s") or 0)
        if file not in names:
            raise ValueError(f"shot {idx + 1}: SFX {file} nggak ada di assets/sfx")
        if not 0 <= at_s <= durations.get(idx, 0) + 0.05:
            raise ValueError(f"shot {idx + 1}: detik SFX harus 0-{durations.get(idx, 0):.1f}")
        entry["sfx"] = {"file": file, "at_s": round(at_s, 2)}


def custom_sfx_events(plan: dict, links: dict) -> list[dict]:
    """SFX kustom per shot → [{"file", "at_s"}] dengan detik dari awal video (awal shot + detik di shot)."""
    starts = {s["index"]: s["start_s"] for s in plan.get("shots", [])}
    out = []
    for key, entry in links.get("shots", {}).items():
        sfx = entry.get("sfx") if isinstance(entry, dict) else None
        if sfx and int(key) in starts:
            out.append({"file": sfx["file"], "at_s": round(starts[int(key)] + float(sfx["at_s"]), 3)})
    return sorted(out, key=lambda e: e["at_s"])


def same_clip(a: dict, b: dict) -> bool:
    """Link + pilihan item sama; detik mulai/selesai dan SFX nggak dihitung."""
    def strip(e: dict) -> dict:
        return {k: v for k, v in e.items() if k not in ("start_s", "end_s", "sfx")}
    return strip(a) == strip(b)


def preview_starts(plan: dict, links: dict, clips: dict | None) -> dict[int, float | None]:
    """Detik mulai bagian video yang bakal jadi klip per shot (preview brief). None = dipilih otomatis pas fetch.

    Urutannya sama kayak fetch: kolom Mulai, lanjutan link yang sama dari shot sebelumnya, terus hasil fetch terakhir
    (clips.json) kalau link-nya masih sama. Clamp ke panjang video dikerjain di browser (durasinya baru ketahuan di situ).
    """
    entries = links.get("shots", {})
    done = (clips or {}).get("shots", [])
    out: dict[int, float | None] = {}
    prev: tuple[dict, float | None, float] | None = None
    for shot in sorted(plan.get("shots", []), key=lambda s: s["index"]):
        entry = entries.get(str(shot["index"]))
        if not isinstance(entry, dict):
            prev = None
            continue
        start = None
        if entry.get("start_s") is not None:
            start = float(entry["start_s"])
        elif prev and prev[1] is not None and entry.get("url") and same_clip(prev[0], entry):
            start = round(prev[1] + prev[2], 2)
        else:
            page = entry.get("url") or entry.get("file")
            for clip in done:
                if (clip.get("page_url") == page and clip.get("source_s") is not None
                        and clip["start_s"] - 1e-6 <= shot["start_s"] < clip["end_s"] - 1e-6):
                    start = round(clip["source_s"] + shot["start_s"] - clip["start_s"], 2)
                    break
        out[shot["index"]] = start
        prev = (entry, start, shot["end_s"] - shot["start_s"])
    return out


def missing_groups(plan: dict, links: dict) -> list[str]:
    filled = links.get("groups", {})
    return [group["id"] for group in plan["groups"] if not filled.get(group["id"])]


def missing_shots(plan: dict, links: dict) -> list[int]:
    filled = links.get("shots", {})
    return [s["index"] for s in plan.get("shots", []) if str(s["index"]) not in filled]
