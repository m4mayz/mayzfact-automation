"""BGM dari naskah (dipilih agent, field `bgm` di script.json) + SFX dari myinstants (spec Fase 3B)."""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from mayzfact.config import PROJECT_ROOT
from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import probe
from mayzfact.net import download
from mayzfact.store import RunPaths, read_json, write_json_atomic

BGM_DIR = PROJECT_ROOT / "assets" / "bgm"
SFX_DIR = PROJECT_ROOT / "assets" / "sfx"
FAKTACUIL_BGM_DIR = PROJECT_ROOT / "assets" / "channels" / "faktacuil" / "bgm"  # lagu lokal, di-gitignore
FAKTACUIL_BGM_REFERENCE = "bully-main-theme.m4a"
FAKTACUIL_BGM_VOLUME = 0.06
FAKTACUIL_BGM_MAX_BOOST_DB = 12
FAKTACUIL_BGM_PEAK_CEILING_DB = -12
FAKTACUIL_BGM_TRACK_BOOST_DB = {"rude-boy-white-cherry-late-night-melancholy.m4a": 8}
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


def faktacuil_bgm_names(bgm_dir: Path) -> list[str]:
    return [name for name in list_bgm(bgm_dir)
            if (bgm_dir / name).is_file() and not (bgm_dir / name).is_symlink()]


def load_faktacuil_bgm_choice(paths: RunPaths) -> str | None:
    try:
        data = read_json(paths.bgm_choice_json)
    except (OSError, ValueError):
        return None
    track = data.get("track") if isinstance(data, dict) else None
    return track if isinstance(track, str) and track else None


def _bgm_levels(song: Path, duration_s: float) -> tuple[float, float]:
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostdin", "-stream_loop", "-1", "-t", str(duration_s), "-i", str(song),
        "-vn", "-map", "0:a:0", "-af", "ebur128=peak=true:framelog=verbose", "-f", "null", "-",
    ], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True, timeout=15,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    summary = result.stderr.rsplit("Summary:", 1)[-1]
    loudness = re.search(r"^\s*I:\s*(-?[\d.]+) LUFS", summary, re.M)
    peak = re.search(r"^\s*Peak:\s*(-?[\d.]+) dBFS", summary, re.M)
    if not loudness or not peak or float(loudness[1]) <= -70:
        raise ValueError("loudness tidak terbaca atau track hening")
    return float(loudness[1]), float(peak[1])


def faktacuil_bgm_volume(song: Path, reference: Path, duration_s: float, log: Callable[[str], None] = print) -> float:
    if song == reference:
        return FAKTACUIL_BGM_VOLUME
    base_db = 20 * math.log10(FAKTACUIL_BGM_VOLUME) + FAKTACUIL_BGM_TRACK_BOOST_DB.get(song.name, 0)
    fallback = round(10 ** (base_db / 20), 5)
    if not math.isfinite(duration_s) or duration_s < .4:
        return fallback
    if not reference.is_file():
        log(f"[timeline] Referensi BGM Bully nggak ada, pakai volume {fallback:.1%}")
        return fallback
    try:
        ref_loudness, _ = _bgm_levels(reference, duration_s)
        loudness, peak = _bgm_levels(song, duration_s)
    except (OSError, ValueError, subprocess.SubprocessError):
        log(f"[timeline] Loudness BGM {song.name} nggak kebaca, pakai volume {fallback:.1%}")
        return fallback
    gain_db = base_db + min(ref_loudness - loudness, FAKTACUIL_BGM_MAX_BOOST_DB)
    volume = round(10 ** (min(gain_db, FAKTACUIL_BGM_PEAK_CEILING_DB - peak) / 20), 5)
    log(f"[timeline] BGM {song.name}: {loudness:.1f} LUFS vs Bully {ref_loudness:.1f} LUFS, volume {volume:.1%}")
    return volume


def audible_start(path: Path) -> float:
    """Detik sampai bunyi pertama kedengeran (hening di depan file). Dipakai buat nyejajarin SFX yang ditumpuk."""
    import re
    import subprocess

    result = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-af", "silencedetect=noise=-40dB:d=0.02", "-f", "null", "-"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", result.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", result.stderr)]
    if starts and ends and starts[0] <= 0.01:
        return round(ends[0], 3)
    return 0.0


ONSET_EVENTS = ("cut", "hook_cut", "extra_", "hook_extra_")  # SFX transisi yang ditumpuk: bunyinya disejajarin


def audible_length(path: Path) -> float:
    """Detik sampai bunyi terakhir yang kedengeran (hening di ujung file nggak dihitung)."""
    import re
    import subprocess

    total = probe(path, "timeline")["duration_s"]
    result = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-af", "silencedetect=noise=-40dB:d=0.05", "-f", "null", "-"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", result.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", result.stderr)]
    if starts and len(starts) > len(ends) or (starts and ends and abs(ends[-1] - total) < 0.05 and starts[-1] < ends[-1]):
        return starts[-1]  # hening terakhir nyampe ujung file
    return total


def faktacuil_bgm_preview_volume(paths: RunPaths, *, bgm_dir: Path = BGM_DIR,
                                 faktacuil_bgm_dir: Path = FAKTACUIL_BGM_DIR) -> float:
    """Volume BGM yang bakal dipakai timeline FaktaCuil (lagu pilihan + durasi suara), buat label di brief."""
    song = _faktacuil_song(bgm_dir, faktacuil_bgm_dir, lambda _: None, selected=load_faktacuil_bgm_choice(paths))
    if song is None:
        return 0.0
    duration = read_json(paths.tts_json).get("duration_s", 30.0) if paths.tts_json.exists() else 30.0
    return faktacuil_bgm_volume(song, faktacuil_bgm_dir / FAKTACUIL_BGM_REFERENCE, float(duration), lambda _: None)


HOOK_BGM = "mystery.mp3"  # D-038: BGM cuma 2, mystery di hook...
MAIN_BGM = "main.mp3"  # ...terus ini mulai "Number" pertama sampai akhir


def prepare_audio(
    paths: RunPaths, script: dict, *, bgm_dir: Path, sfx_dir: Path, client: httpx.Client,
    log: Callable[[str], None], custom: list[dict] | None = None, faktacuil_bgm_dir: Path = FAKTACUIL_BGM_DIR,
    duration_s: float | None = None,
) -> dict:
    """BGM hook + utama, siapin SFX, copy ke runs/<id>/audio/ buat Remotion. Field bgm di naskah nggak dipakai lagi.

    custom: SFX kustom dari brief [{"file", "at_s"}], file-nya dari sfx_dir (nggak di-download).
    """
    choices = list_bgm(bgm_dir)
    out: dict[str, Any] = {"bgm": None, "bgm_main": None, "sfx": {}}
    if script.get("narration_mode") == "faktacuil":
        song = _faktacuil_song(bgm_dir, faktacuil_bgm_dir, log, selected=load_faktacuil_bgm_choice(paths))
        if song:
            out["bgm_main"] = _copy(song, paths.root / "audio" / "bgm", paths)
            if duration_s is not None:
                out["bgm_volume"] = faktacuil_bgm_volume(song, faktacuil_bgm_dir / FAKTACUIL_BGM_REFERENCE,
                                                         duration_s, log)
        write_json_atomic(paths.root / "audio.json", {"bgm": None, "bgm_main": song.name if song else None})
    else:
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
                out["riser_s"] = audible_length(path)
            except PipelineError as exc:
                log(f"[timeline] riser dilewat, durasinya nggak kebaca: {exc.message.splitlines()[0]}")
                del out["sfx"][event]
        if event.startswith(ONSET_EVENTS):
            try:
                out.setdefault("sfx_onset", {})[event] = audible_start(path)
            except Exception as exc:  # hiasan: gagal = SFX diputer apa adanya
                log(f"[timeline] awal bunyi {path.name} nggak kebaca, nggak disejajarin: {exc}")
    for item in custom or []:
        name = item.get("file")
        path = sfx_dir / str(name)
        if not isinstance(name, str) or Path(name).name != name or not path.is_file():
            log(f"[timeline] SFX kustom {name!r} nggak ada di assets/sfx, dilewat")
            continue
        try:
            src = _copy(path, paths.root / "audio" / "sfx", paths)
        except OSError as exc:  # hiasan: SFX ini doang yang dilewat, BGM + SFX lain tetap jalan
            log(f"[timeline] SFX kustom {name} gagal di-copy, dilewat: {exc}")
            continue
        try:
            onset = audible_start(path)
        except Exception:  # hiasan: gagal baca = diputer apa adanya
            onset = 0.0
        out.setdefault("custom", []).append({"src": src, "at_s": float(item["at_s"]), "onset": onset})
    return out


def _faktacuil_song(bgm_dir: Path, local_dir: Path, log: Callable[[str], None], *, selected: str | None = None) -> Path | None:
    songs = faktacuil_bgm_names(local_dir)
    if selected:
        if selected in songs:
            log(f"[timeline] BGM FaktaCuil dari brief: {selected}")
            return local_dir / selected
        log(f"[timeline] BGM pilihan {selected!r} nggak ada, pakai default")
    if songs:
        extra = f" (ada {len(songs)} file: {', '.join(songs)})" if len(songs) > 1 else ""
        log(f"[timeline] BGM FaktaCuil: {songs[0]}{extra}")
        return local_dir / songs[0]
    if MAIN_BGM in list_bgm(bgm_dir):
        log(f"[timeline] BGM FaktaCuil belum ada di assets/channels/faktacuil/bgm/, sementara pakai {MAIN_BGM}")
        return bgm_dir / MAIN_BGM
    log(f"[timeline] BGM FaktaCuil belum ada dan {MAIN_BGM} nggak ada di assets/bgm, video tanpa BGM")
    return None


def _copy(src: Path, dest_dir: Path, paths: RunPaths) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copyfile(src, dest)
    return dest.relative_to(paths.root).as_posix()
