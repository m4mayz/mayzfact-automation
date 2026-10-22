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
from mayzfact.ffmpeg import probe
from mayzfact.net import download
from mayzfact.store import RunPaths, write_json_atomic

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


HOOK_BGM = "mystery.mp3"  # D-038: BGM cuma 2, mystery di hook...
MAIN_BGM = "main.mp3"  # ...terus ini mulai "Number" pertama sampai akhir


def prepare_audio(
    paths: RunPaths, script: dict, *, bgm_dir: Path, sfx_dir: Path, client: httpx.Client,
    log: Callable[[str], None],
) -> dict:
    """BGM hook + utama, siapin SFX, copy ke runs/<id>/audio/ buat Remotion. Field bgm di naskah nggak dipakai lagi."""
    choices = list_bgm(bgm_dir)
    out: dict[str, Any] = {"bgm": None, "bgm_main": None, "sfx": {}}
    for key, name in (("bgm", HOOK_BGM), ("bgm_main", MAIN_BGM)):
        if name in choices:
            out[key] = _copy(bgm_dir / name, paths.root / "audio" / "bgm", paths)
            log(f"[timeline] BGM {key}: {name}")
        else:
            log(f"[timeline] {name} nggak ada di assets/bgm, bagian itu tanpa BGM")
    write_json_atomic(paths.root / "audio.json", {"bgm": HOOK_BGM if out["bgm"] else None})
    for event, path in ensure_sfx(sfx_dir, client, load_sfx_map(sfx_dir, log), log).items():
        out["sfx"][event] = _copy(path, paths.root / "audio" / "sfx", paths)
        if event == "riser":  # panjang riser dipakai buat ngepasin ujungnya ke "Number" pertama
            try:
                out["riser_s"] = probe(path, "timeline")["duration_s"]
            except PipelineError as exc:
                log(f"[timeline] riser dilewat, durasinya nggak kebaca: {exc.message.splitlines()[0]}")
                del out["sfx"][event]
    return out


def _copy(src: Path, dest_dir: Path, paths: RunPaths) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copyfile(src, dest)
    return dest.relative_to(paths.root).as_posix()
