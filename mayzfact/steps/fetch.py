"""Step fetch (mode manual): link/file per kelompok konteks → potongan terbaik per shot → clips.json (spec metode manual 5 + 10)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from mayzfact.embed import Encoder, mean_unit
from mayzfact.errors import AwaitingInput, PipelineError
from mayzfact.ffmpeg import probe, sample_frames
from mayzfact.manual.links import link_kind, load_links, missing_groups
from mayzfact.manual.obtain import cache_key, media_kind
from mayzfact.steps.clips import normalize_local
from mayzfact.store import RunPaths, write_json_atomic

LOW_TEXT_SCORE = 0.10
LOW_IMAGE_SCORE = 0.60
SAMPLE_EVERY_S = 0.5
SAMPLE_MAX_S = 60.0
TAIL_S = 0.2  # normalize_local motong durasi shot + 0.2 detik


@dataclass
class Source:
    """1 video atau 1 foto dari link/file kelompok, plus embedding-nya."""

    entry: dict
    kind: str
    path: Path
    vectors: np.ndarray  # video: 1 per frame sample; foto: 1 baris
    times: list[float] = field(default_factory=list)
    total_s: float = 0.0
    used: list[tuple[float, float]] = field(default_factory=list)  # video: window terpakai; foto: isi = sudah dipakai


def _message(exc: Exception) -> str:
    return exc.message if isinstance(exc, PipelineError) else f"{type(exc).__name__}: {exc}"


def _target(shot: dict, paths: RunPaths, encoder: Encoder) -> tuple[np.ndarray, float]:
    if shot["ref_frames"]:
        return mean_unit(encoder.images([paths.root / f for f in shot["ref_frames"]])), LOW_IMAGE_SCORE
    text = shot.get("subject") or (shot["keywords"]["en"] or [shot["text"]])[0]
    return encoder.texts([text])[0], LOW_TEXT_SCORE


def _window_start(center: float, duration: float, total: float) -> float:
    """Sama persis dengan aturan clamp di normalize_local."""
    return min(max(0.0, center - duration / 2), total - duration - TAIL_S)


def _sources(entry: dict, files: list[Path], paths: RunPaths, encoder: Encoder) -> list[Source]:
    kinds = [(f, media_kind(f)) for f in files]
    videos = [f for f, k in kinds if k == "video"]
    photos = [f for f, k in kinds if k == "photo"]
    pick = entry.get("pick")
    if pick and photos:
        if pick > len(photos):
            raise PipelineError("fetch", f"post ini cuma punya {len(photos)} foto, tapi diminta #{pick}")
        photos = [photos[pick - 1]]
    if videos:
        video = videos[0]
        frames = sample_frames(video, paths.plan_dir / "fetch" / video.stem, every_s=SAMPLE_EVERY_S, max_s=SAMPLE_MAX_S)
        if not frames:
            raise PipelineError("fetch", "video-nya nggak punya frame yang bisa dibaca")
        total = probe(video, "fetch")["duration_s"] or 0.0
        return [Source(entry, "video", video, encoder.images([p for _, p in frames]), [t for t, _ in frames], total)]
    if photos:
        vectors = encoder.images(photos)
        return [Source(entry, "photo", photo, vectors[i:i + 1]) for i, photo in enumerate(photos)]
    raise PipelineError("fetch", "file-nya bukan video/gambar yang bisa dibaca")


def _best(sources: list[Source], target: np.ndarray, duration: float, used_sources: bool) -> tuple[Source, float, float] | None:
    """(source, skor, detik mulai) terbaik dari yang belum pernah tampil.

    Potongan yang udah tampil nggak pernah dipakai lagi: foto yang udah kepakai dilewat, window video nggak boleh overlap.
    used_sources=False: cuma video/foto yang belum kepakai sama sekali. True: boleh bagian lain dari video yang udah kepakai.
    """
    best: tuple[Source, float, float] | None = None
    for source in sources:
        if source.used and (not used_sources or source.kind == "photo"):
            continue
        sims = source.vectors @ target
        if source.kind == "photo":
            options = [(float(sims[0]), 0.0)]
        else:
            if source.total_s < duration + TAIL_S:
                continue
            options = []
            for t, sim in zip(source.times, sims):
                start = _window_start(t, duration, source.total_s)
                end = start + duration + TAIL_S
                if any(start < u_end and u_start < end for u_start, u_end in source.used):
                    continue
                options.append((float(sim), start))
        for score, start in options:
            if best is None or score > best[1]:
                best = (source, score, start)
    return best


class Progress:
    """fetch_progress.json: dibaca halaman brief tiap 2 detik buat nampilin progres fetch."""

    MAX_LOG = 40

    def __init__(self, path: Path, links_total: int, shots_total: int, log: Callable[[str], None]) -> None:
        self.path = path
        self._log = log
        self.data = {"state": "running", "current": "", "links_done": 0, "links_total": links_total,
                     "shots_done": 0, "shots_total": shots_total, "log": []}
        self.save()

    def save(self) -> None:
        try:
            write_json_atomic(self.path, self.data)
        except OSError:  # cuma buat tampilan, jangan sampai bikin fetch gagal
            pass

    def update(self, **fields: Any) -> None:
        self.data.update(fields)
        self.save()

    def log(self, line: str) -> None:
        self._log(line)
        self.data["log"] = (self.data["log"] + [line])[-self.MAX_LOG:]
        self.save()


def _continuous(group: dict, shots: list[dict], source: Source, paths: RunPaths, encoder: Encoder,
                fg_min_ratio: float, progress: Progress) -> dict | None:
    """Hook dengan 1 video: diputer nyambung sepanjang semua shot hook, nggak dipotong-potong.

    Titik mulai = detik sample yang bikin rata-rata kemiripan tiap shot (frame di tengah shot vs ref-nya) paling tinggi.
    None kalau video-nya kependekan, nanti balik ke cara potong per shot.
    """
    first, last = shots[0]["start_s"], shots[-1]["end_s"]
    span = last - first
    if source.total_s < span + TAIL_S:
        return None
    times = np.array(source.times)
    sims = [source.vectors @ _target(shot, paths, encoder)[0] for shot in shots]
    mids = [(shot["start_s"] + shot["end_s"]) / 2 - first for shot in shots]
    best: tuple[float, float] | None = None
    for start in source.times:
        if start + span + TAIL_S > source.total_s + 1e-6:
            break
        score = float(np.mean([sim[int(np.argmin(np.abs(times - (start + mid))))] for sim, mid in zip(sims, mids)]))
        if best is None or score > best[0]:
            best = (score, start)
    if best is None:
        return None
    score, start = best
    source.used.append((start, start + span + TAIL_S))
    head = shots[0]
    out = normalize_local(head["index"], first, last, source.path, "video", start + span / 2, paths, fg_min_ratio)
    url = source.entry.get("url")
    progress.data["shots_done"] += len(shots)
    progress.log(f"[fetch] shot {head['index'] + 1}-{shots[-1]['index'] + 1} ({group['label']}): 1 video nyambung, skor {score:.3f} dari detik {start:.1f}")
    return {
        "index": head["index"], "beat": head["beat"], "start_s": first, "end_s": last, **out,
        "provider": link_kind(url) if url else "upload",
        "provider_id": cache_key(url) if url else Path(source.entry["file"]).name,
        "page_url": url or source.entry["file"], "author": "", "query": "manual",
        "match": round(score, 4), "hook_segment": head["hook_segment"], "source_s": round(start, 2),
    }


def _run_group(group: dict, shots: list[dict], entries: list[dict], obtain: Callable[[dict, Path], list[Path]],
               paths: RunPaths, encoder: Encoder, fg_min_ratio: float, progress: Progress,
               shown: dict[Path, list[tuple[float, float]]]) -> tuple[list[dict], list[str]]:
    sources: list[Source] = []
    errors = []
    for line, entry in enumerate(entries, 1):
        progress.update(current=f"{group['label']}: download baris {line}/{len(entries)}")
        try:
            sources += _sources(entry, obtain(entry, paths.root), paths, encoder)
            progress.log(f"[fetch] {group['label']} baris {line}: siap")
        except Exception as exc:  # 1 link gagal = kelompok gagal, tapi baris lain tetap dicek biar semua error kelihatan
            errors.append(f"baris {line} ({entry.get('url') or entry.get('file')}): {_message(exc)[:200]}")
            progress.log(f"[fetch] {group['label']} baris {line}: GAGAL {_message(exc).splitlines()[0][:120]}")
        progress.update(links_done=progress.data["links_done"] + 1)
    if errors:
        raise PipelineError("fetch", "; ".join(errors))
    for source in sources:  # catatan "udah tampil" dibagi per file, jadi link yang sama di kelompok lain ikut kehitung
        source.used = shown.setdefault(source.path, [])
    clips, warnings = [], []
    progress.update(current=f"{group['label']}: milih potongan")
    if group["id"] == "hook" and len(sources) == 1 and sources[0].kind == "video":
        clip = _continuous(group, shots, sources[0], paths, encoder, fg_min_ratio, progress)
        if clip is not None:
            return [clip], warnings
    for shot in shots:
        number = shot["index"] + 1
        duration = shot["end_s"] - shot["start_s"]
        target, low = _target(shot, paths, encoder)
        chosen = _best(sources, target, duration, used_sources=False)
        if chosen is None:
            chosen = _best(sources, target, duration, used_sources=True)
            if chosen is None:
                raise PipelineError("fetch", f"shot {number}: klip di kelompok ini udah kepakai semua (atau kependekan), tambah link lagi")
            warnings.append(f"shot {number} pakai bagian lain dari video yang udah kepakai")
        source, score, start = chosen
        source.used.append((start, start + duration + TAIL_S))
        if score < low:
            warnings.append(f"shot {number} skor rendah ({score:.2f})")
        out = normalize_local(shot["index"], shot["start_s"], shot["end_s"], source.path, source.kind,
                              start + duration / 2, paths, fg_min_ratio)
        url = source.entry.get("url")
        clips.append({
            "index": shot["index"], "beat": shot["beat"], "start_s": shot["start_s"], "end_s": shot["end_s"], **out,
            "provider": link_kind(url) if url else "upload",
            "provider_id": cache_key(url) if url else Path(source.entry["file"]).name,
            "page_url": url or source.entry["file"], "author": "", "query": "manual",
            "match": round(score, 4), "hook_segment": shot["hook_segment"], "source_s": round(start, 2),
        })
        progress.data["shots_done"] += 1
        progress.log(f"[fetch] shot {number} ({group['label']}): {source.kind} skor {score:.3f} dari detik {start:.1f}")
    return clips, warnings


def run_fetch(
    paths: RunPaths,
    plan: dict,
    *,
    obtain: Callable[[dict, Path], list[Path]],
    encoder: Encoder | Any,
    fg_min_ratio: float,
    log: Callable[[str], None] = print,
) -> dict:
    links = load_links(paths.links_json)
    missing = set(missing_groups(plan, links))
    paths.clips_dir.mkdir(parents=True, exist_ok=True)
    for old in paths.clips_dir.glob("shot_*"):
        old.unlink()
    shots = {shot["index"]: shot for shot in plan["shots"]}
    status: dict[str, dict] = {}
    problems: list[str] = []
    clips: list[dict] = []
    links_total = sum(len(links["groups"].get(g["id"], [])) for g in plan["groups"])
    progress = Progress(paths.fetch_progress_json, links_total, len(plan["shots"]), log)
    shown: dict[Path, list[tuple[float, float]]] = {}
    try:
        for group in plan["groups"]:
            gid = group["id"]
            if gid in missing:
                status[gid] = {"state": "missing", "message": "belum diisi"}
                problems.append(group["label"])
                continue
            try:
                group_clips, warnings = _run_group(group, [shots[i] for i in group["shots"]], links["groups"][gid],
                                                   obtain, paths, encoder, fg_min_ratio, progress, shown)
            except Exception as exc:  # error apa pun cukup bikin kelompok ini gagal, kelompok lain tetap diproses
                status[gid] = {"state": "error", "message": _message(exc)[:600]}
                problems.append(group["label"])
                progress.log(f"[fetch] {group['label']}: {_message(exc).splitlines()[0][:160]}")
                continue
            clips += group_clips
            status[gid] = {"state": "ok", "message": "; ".join(warnings)}
        write_json_atomic(paths.links_status_json, {"groups": status})
        if problems:
            progress.update(state="awaiting", current="")
            raise AwaitingInput(
                "fetch", f"{len(problems)} kelompok perlu diisi/diganti: {', '.join(problems)}. Buka: mayzfact brief {paths.root.name}"
            )
        data = {"shots": sorted(clips, key=lambda clip: clip["index"])}
        write_json_atomic(paths.clips_json, data)
        progress.update(state="done", current="")
    finally:
        if progress.data["state"] == "running":  # crash / Ctrl+C: jangan biarin brief nampilin "Lagi jalan" selamanya
            progress.update(state="failed", current="")
    return data
