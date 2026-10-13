"""BGM sesuai konteks (assets/bgm, dipilih Gemini) + SFX dari myinstants (spec Fase 3B)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Callable

import httpx

from mayzfact.config import PROJECT_ROOT
from mayzfact.errors import PipelineError
from mayzfact.net import download
from mayzfact.store import RunPaths, read_json, write_json_atomic
from mayzfact.text import script_text

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
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "pick_bgm.md"


def load_sfx_map(sfx_dir: Path) -> dict[str, str]:
    """sfx.json: momen → nama file di myinstants. Dibikin dari default kalau belum ada."""
    path = sfx_dir / "sfx.json"
    if not path.exists():
        sfx_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(SFX_DEFAULTS, indent=2) + "\n", encoding="utf-8")
        return dict(SFX_DEFAULTS)
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_sfx(sfx_dir: Path, client: httpx.Client, mapping: dict[str, str], log: Callable[[str], None]) -> dict[str, Path]:
    """Download SFX yang belum ada. Yang gagal dilewat (video tetap jadi, momennya tanpa bunyi)."""
    out: dict[str, Path] = {}
    for event, name in mapping.items():
        try:
            out[event] = download(client, MYINSTANTS + name, sfx_dir / name, step="timeline")
        except PipelineError as exc:
            log(f"[timeline] SFX {event} ({name}) gagal di-download, dilewat: {exc.message[:120]}")
    return out


def list_bgm(bgm_dir: Path) -> list[str]:
    if not bgm_dir.is_dir():
        return []
    return sorted(p.name for p in bgm_dir.iterdir() if p.suffix.lower() in AUDIO_EXTS)


def pick_bgm(choices: list[str], script: dict, writer: Any, log: Callable[[str], None]) -> str | None:
    if not choices:
        log("[timeline] assets/bgm kosong, video tanpa BGM")
        return None
    if len(choices) == 1:
        return choices[0]
    if writer is None:
        log("[timeline] Gemini nggak ada, BGM nggak dipilih")
        return None
    from mayzfact.models import BgmChoice

    contents = json.dumps({"files": choices, "script": script_text(script["beats"])}, ensure_ascii=False)
    try:
        result = writer.generate(PROMPT_PATH.read_text(encoding="utf-8"), contents, BgmChoice, step="timeline")
    except PipelineError as exc:
        log(f"[timeline] Gemini gagal milih BGM, video tanpa BGM: {exc.message[:120]}")
        return None
    if result.file not in choices:
        log(f"[timeline] Gemini milih BGM yang nggak ada ({result.file}), video tanpa BGM")
        return None
    return result.file


def prepare_audio(
    paths: RunPaths, script: dict, *, bgm_dir: Path, sfx_dir: Path, client: httpx.Client, writer: Any,
    log: Callable[[str], None],
) -> dict:
    """Pilih BGM (pakai audio.json kalau masih valid), siapin SFX, copy ke runs/<id>/audio/ buat Remotion."""
    choices = list_bgm(bgm_dir)
    saved = paths.root / "audio.json"
    bgm = read_json(saved).get("bgm") if saved.exists() else None
    if bgm not in choices:
        bgm = pick_bgm(choices, script, writer, log)
        write_json_atomic(saved, {"bgm": bgm})
    out: dict[str, Any] = {"bgm": None, "sfx": {}}
    if bgm:
        out["bgm"] = _copy(bgm_dir / bgm, paths.root / "audio" / "bgm", paths)
        log(f"[timeline] BGM: {bgm}")
    for event, path in ensure_sfx(sfx_dir, client, load_sfx_map(sfx_dir), log).items():
        out["sfx"][event] = _copy(path, paths.root / "audio" / "sfx", paths)
    return out


def _copy(src: Path, dest_dir: Path, paths: RunPaths) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copyfile(src, dest)
    return dest.relative_to(paths.root).as_posix()
