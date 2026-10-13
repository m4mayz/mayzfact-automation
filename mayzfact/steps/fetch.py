"""Step fetch (mode manual): link/file dari brief → potongan terbaik → clips.json (spec metode manual bagian 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np

from mayzfact.embed import Encoder, mean_unit
from mayzfact.errors import AwaitingInput, PipelineError
from mayzfact.ffmpeg import sample_frames
from mayzfact.manual.links import link_kind, load_links, missing_shots
from mayzfact.manual.obtain import cache_key, media_kind
from mayzfact.steps.clips import normalize_local
from mayzfact.store import RunPaths, write_json_atomic

LOW_TEXT_SCORE = 0.10
LOW_IMAGE_SCORE = 0.60
SAMPLE_EVERY_S = 0.5
SAMPLE_MAX_S = 60.0


def _target(shot: dict, paths: RunPaths, encoder: Encoder) -> tuple[np.ndarray, float]:
    if shot["ref_frames"]:
        return mean_unit(encoder.images([paths.root / f for f in shot["ref_frames"]])), LOW_IMAGE_SCORE
    text = shot.get("subject") or (shot["keywords"]["en"] or [shot["text"]])[0]
    return encoder.texts([text])[0], LOW_TEXT_SCORE


def _choose(shot: dict, entry: dict, files: list[Path], paths: RunPaths, encoder: Encoder) -> tuple[Path, str, float, float]:
    target, _ = _target(shot, paths, encoder)
    kinds = [(f, media_kind(f)) for f in files]
    videos = [f for f, k in kinds if k == "video"]
    photos = [f for f, k in kinds if k == "photo"]
    pick = entry.get("pick")
    if pick and photos:
        if pick > len(photos):
            raise PipelineError("fetch", f"Post ini cuma punya {len(photos)} foto, tapi diminta #{pick}.")
        chosen = photos[pick - 1]
        return chosen, "photo", float(encoder.images([chosen])[0] @ target), 0.0
    if videos:
        frames = sample_frames(videos[0], paths.plan_dir / "fetch" / f"shot_{shot['index'] + 1:02d}",
                               every_s=SAMPLE_EVERY_S, max_s=SAMPLE_MAX_S)
        if not frames:
            raise PipelineError("fetch", "Video-nya nggak punya frame yang bisa dibaca.")
        sims = encoder.images([p for _, p in frames]) @ target
        best = int(np.argmax(sims))
        return videos[0], "video", float(sims[best]), frames[best][0]
    if photos:
        sims = encoder.images(photos) @ target
        best = int(np.argmax(sims))
        return photos[best], "photo", float(sims[best]), 0.0
    raise PipelineError("fetch", "File-nya bukan video/gambar yang bisa dibaca.")


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
    missing = set(missing_shots(plan, links))
    paths.clips_dir.mkdir(parents=True, exist_ok=True)
    for old in paths.clips_dir.glob("shot_*"):
        old.unlink()
    status: dict[str, dict] = {}
    problems: list[int] = []
    clips = []
    for shot in plan["shots"]:
        number = shot["index"] + 1
        if number in missing:
            status[str(number)] = {"state": "missing", "message": "belum diisi"}
            problems.append(number)
            continue
        entry = links["shots"][str(number)]
        try:
            raw, kind, score, offset = _choose(shot, entry, obtain(entry, paths.root), paths, encoder)
            out = normalize_local(shot["index"], shot["start_s"], shot["end_s"], raw, kind, offset, paths, fg_min_ratio)
        except Exception as exc:  # error apa pun cukup bikin shot ini gagal, shot lain tetap diproses
            message = exc.message if isinstance(exc, PipelineError) else f"{type(exc).__name__}: {exc}"
            status[str(number)] = {"state": "error", "message": message[:300]}
            problems.append(number)
            log(f"[fetch] shot {number}: {message.splitlines()[0][:120]}")
            continue
        _, low = _target(shot, paths, encoder)
        url = entry.get("url")
        clips.append({
            "index": shot["index"], "beat": shot["beat"], "start_s": shot["start_s"], "end_s": shot["end_s"], **out,
            "provider": link_kind(url) if url else "upload", "provider_id": cache_key(url) if url else Path(entry["file"]).name,
            "page_url": url or entry["file"], "author": "", "query": "manual",
            "match": round(score, 4), "hook_segment": shot["hook_segment"],
        })
        status[str(number)] = {
            "state": "ok", "score": round(score, 4),
            "message": f"skor rendah ({score:.2f}), mungkin kurang cocok" if score < low else "",
        }
        log(f"[fetch] shot {number}: {kind} skor {score:.3f}")
    write_json_atomic(paths.links_status_json, {"shots": status})
    if problems:
        raise AwaitingInput(
            "fetch",
            f"{len(problems)} shot perlu diisi/diganti: {', '.join(map(str, sorted(problems)))}. "
            f"Buka: mayzfact brief {paths.root.name}",
        )
    data = {"shots": clips}
    write_json_atomic(paths.clips_json, data)
    return data
