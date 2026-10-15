"""BGM dari naskah (dipilih agent, field `bgm` di script.json) + SFX dari myinstants (spec Fase 3B)."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from mayzfact.config import PROJECT_ROOT
from mayzfact.errors import PipelineError
from mayzfact.net import download
from mayzfact.store import RunPaths, read_json, write_json_atomic

BGM_DIR = PROJECT_ROOT / "assets" / "bgm"
SFX_DIR = PROJECT_ROOT / "assets" / "sfx"
MYINSTANTS = "https://www.myinstants.com/media/sounds/"
SFX_DEFAULTS = {
    "hook": "cinematicboom.mp3",
    "number": "vine-boom.mp3",
    "subject": "transition-whoosh.mp3",
    "cut": "fast-whoosh.mp3",
}
AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".ogg"}


def load_sfx_map(sfx_dir: Path, log: Callable[[str], None] = print) -> dict[str, str]:
    """sfx.json: momen → nama file di myinstants. Dibikin dari default kalau belum ada, default juga kalau rusak."""
    path = sfx_dir / "sfx.json"
    if not path.exists():
        sfx_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(SFX_DEFAULTS, indent=2) + "\n", encoding="utf-8")
        return dict(SFX_DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        log(f"[timeline] sfx.json rusak ({exc}), pakai SFX default")
        return dict(SFX_DEFAULTS)
    return data if isinstance(data, dict) else dict(SFX_DEFAULTS)


def ensure_sfx(sfx_dir: Path, client: httpx.Client, mapping: dict[str, str], log: Callable[[str], None],
               sleep: Callable[[float], None] = time.sleep) -> dict[str, Path]:
    """Download SFX yang belum ada. Yang gagal dilewat (video tetap jadi, momennya tanpa bunyi).

    Kalau myinstants nggak bisa dihubungi, sisanya langsung dilewat: SFX cuma hiasan, jangan bikin pipeline nunggu lama.
    """
    out: dict[str, Path] = {}
    for event, name in mapping.items():
        if not isinstance(name, str) or not name or Path(name).name != name or name.startswith("."):
            log(f"[timeline] SFX {event}: nama file {name!r} nggak valid, dilewat")
            continue
        try:
            out[event] = download(client, MYINSTANTS + name, sfx_dir / name, step="timeline", sleep=sleep)
        except PipelineError as exc:
            if isinstance(exc.__cause__, httpx.TransportError):
                log(f"[timeline] myinstants nggak bisa dihubungi, SFX yang belum ke-download dilewat: {exc.message[:120]}")
                break
            log(f"[timeline] SFX {event} ({name}) gagal di-download, dilewat: {exc.message[:120]}")
    return out


def list_bgm(bgm_dir: Path) -> list[str]:
    if not bgm_dir.is_dir():
        return []
    return sorted(p.name for p in bgm_dir.iterdir() if p.suffix.lower() in AUDIO_EXTS)


def prepare_audio(
    paths: RunPaths, script: dict, *, bgm_dir: Path, sfx_dir: Path, client: httpx.Client,
    log: Callable[[str], None],
) -> dict:
    """BGM dari naskah, siapin SFX, copy ke runs/<id>/audio/ buat Remotion."""
    choices = list_bgm(bgm_dir)
    saved = paths.root / "audio.json"
    if "bgm" in script:
        bgm = script.get("bgm") or None  # dipilih agent pas nulis naskah
    else:  # naskah lama (sebelum agent nulis bgm): pakai pilihan yang udah disetujui di run sebelumnya
        bgm = read_json(saved).get("bgm") if saved.exists() else None
    if bgm and bgm not in choices:
        log(f"[timeline] BGM {bgm!r} nggak ada di assets/bgm, video tanpa BGM")
        bgm = None
    write_json_atomic(saved, {"bgm": bgm})
    out: dict[str, Any] = {"bgm": None, "sfx": {}}
    if bgm:
        out["bgm"] = _copy(bgm_dir / bgm, paths.root / "audio" / "bgm", paths)
        log(f"[timeline] BGM: {bgm}")
    for event, path in ensure_sfx(sfx_dir, client, load_sfx_map(sfx_dir, log), log).items():
        out["sfx"][event] = _copy(path, paths.root / "audio" / "sfx", paths)
    return out


def _copy(src: Path, dest_dir: Path, paths: RunPaths) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copyfile(src, dest)
    return dest.relative_to(paths.root).as_posix()
