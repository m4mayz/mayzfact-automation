"""Step plan (mode manual): daftar shot + frame referensi hook + keyword buat brief (spec metode manual bagian 3)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from mayzfact.matching import hook_slot_map
from mayzfact.steps.clips import beat_subjects, split_shots
from mayzfact.steps.hook import prepare_source_segments
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import beat_texts
from mayzfact.timing import beat_timings


def group_of(shot: dict) -> tuple[str, str]:
    """(id, label) kelompok konteks shot: semua hook jadi 1, sisanya per subjek, atau per beat kalau subjeknya kosong."""
    if shot["hook_segment"] is not None:
        return "hook", "HOOK"
    if shot["subject"]:
        return re.sub(r"[^a-z0-9]+", "-", shot["subject"].lower()).strip("-") or f"beat-{shot['beat'] + 1}", shot["subject"]
    return f"beat-{shot['beat'] + 1}", f"beat {shot['beat'] + 1}"


def _groups(shots: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    for shot in shots:
        gid, label = group_of(shot)
        shot["group"] = gid
        group = groups.setdefault(gid, {"id": gid, "label": label, "shots": [], "keywords": {"en": [], "zh": []}})
        group["shots"].append(shot["index"])
        for lang in ("en", "zh"):
            group["keywords"][lang] += [k for k in shot["keywords"][lang] if k not in group["keywords"][lang]]
    return list(groups.values())


def run_plan(
    paths: RunPaths,
    script: dict,
    tts: dict,
    source: dict,
    *,
    max_shot_s: float,
    hook_seconds: float,
    download_source: Callable[[str, Path], Path],
    describe: Callable[[list[dict], list[Path]], dict[int, dict]],
    translate: Callable[[list[str]], dict[str, str]],
    log: Callable[[str], None] = print,
) -> dict:
    beats = script["beats"]
    slots = split_shots(beat_timings(beat_texts(beats), tts["alignment"], tts["duration_s"]), beats, max_shot_s)
    subjects = beat_subjects(beats)
    segs = prepare_source_segments(paths, source, download_source, hook_seconds, paths.plan_dir, retry_step="plan") if hook_seconds > 0 else []
    mapping = hook_slot_map(slots, len(segs), hook_seconds)
    infos = [{k: s[k] for k in ("index", "start_s", "end_s", "transcript")} for s in segs]
    hook_keywords = describe(infos, [s["frames"][1] for s in segs]) if mapping else {}
    zh = translate(sorted({q for beat in beats for q in beat["queries"]}))

    def rel(path: Path) -> str:
        return path.relative_to(paths.root).as_posix()

    shots = []
    for slot in slots:
        beat = beats[slot.beat]
        segment = mapping.get(slot.index)
        if segment is not None:
            keywords = hook_keywords.get(segment, {"en": [], "zh": []})
            ref_frames = [rel(f) for f in segs[segment]["frames"]]
        else:
            keywords = {"en": list(beat["queries"]), "zh": [zh[q] for q in beat["queries"] if zh.get(q)]}
            ref_frames = []
        shots.append({
            "index": slot.index, "beat": slot.beat, "start_s": slot.start_s, "end_s": slot.end_s, "media": slot.media,
            "text": beat["text"], "subject": subjects[slot.beat], "hook_segment": segment,
            "ref_frames": ref_frames, "keywords": keywords,
        })
    data = {
        "hook_seconds": hook_seconds,
        "segments": [{"index": s["index"], "start_s": s["start_s"], "end_s": s["end_s"], "frames": [rel(f) for f in s["frames"]]} for s in segs],
        "groups": _groups(shots),
        "shots": shots,
    }
    write_json_atomic(paths.shots_plan_json, data)
    log(f"[plan] {len(shots)} shot ({len(mapping)} hook), {len(data['groups'])} kelompok. Isi link: mayzfact brief {paths.root.name}")
    return data
