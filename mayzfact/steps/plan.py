"""Step plan (mode manual): daftar shot + frame referensi hook + keyword buat brief (spec metode manual bagian 3)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from mayzfact.countdown import Countdown, parse_countdown
from mayzfact.ffmpeg import extract_frame, probe
from mayzfact.matching import hook_slot_map
from mayzfact.steps.clips import beat_subjects, split_shots
from mayzfact.steps.hook import prepare_source_segments
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import beat_texts
from mayzfact.timing import beat_timings

SOURCE_FRAMES = (0.25, 0.5, 0.75)
_NO_COUNTDOWN = Countdown(None, "", -1)


LIST_WINDOW_S = 5.0  # sebutan subjek lain sedekat ini = daftar (misalnya intro), bukan awal bagian subjek


def _mentions(transcript: list[dict], subject: str) -> list[float]:
    """Semua detik subjek disebut (kata utuh). Nama lengkap dulu; kalau nggak ada, kata terakhirnya."""
    words = subject.lower().split()
    for needle in dict.fromkeys([" ".join(words), words[-1]] if words else []):
        pattern = re.compile(rf"\b{re.escape(needle)}\b")
        times = [
            snippet["start"] + snippet["duration"] * m.start() / max(len(snippet["text"]), 1)
            for snippet in transcript for m in pattern.finditer(snippet["text"].lower())
        ]
        if times:
            return sorted(times)
    return []


def subject_ranges(transcript: list[dict], subjects: list[str], total_s: float) -> dict[str, tuple[float, float]]:
    """Rentang waktu tiap subjek di source: dari awal bagiannya sampai subjek berikutnya mulai.

    Subjek dicari sesuai urutan beat. Sebutan yang deket sama sebutan subjek lain dianggap daftar (intro) dan dilewat.
    """
    subjects = [s.strip() for s in subjects if s and s.strip()]
    found_all = {s: _mentions(transcript, s) for s in subjects}

    def listed(t: float, subject: str) -> bool:
        return any(abs(o - t) < LIST_WINDOW_S for other in subjects if other != subject for o in found_all[other])

    found: list[tuple[float, str]] = []
    after = 0.0
    for subject in subjects:
        later = [t for t in found_all[subject] if t >= after]
        picks = [t for t in later if not listed(t, subject)] or later
        if picks:
            found.append((picks[0], subject))
            after = picks[0]
    found.sort()
    return {s: (t, found[i + 1][0] if i + 1 < len(found) else total_s) for i, (t, s) in enumerate(found)}


def group_of(shot: dict) -> tuple[str, str]:
    """(id, label) kelompok konteks shot: semua hook jadi 1, sisanya per subjek, atau per beat kalau subjeknya kosong."""
    if shot["hook_segment"] is not None:
        return "hook", "HOOK"
    subject = (shot["subject"] or "").strip()
    slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")
    if slug:
        return ("subject-hook" if slug == "hook" else slug), subject  # "hook" khusus buat kelompok hook
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
    for group in groups.values():
        group["ref_frames"] = []
    return list(groups.values())


def _source_frames(paths: RunPaths, source: dict, groups: list[dict], shots: list[dict],
                   download_source: Callable[[str, Path], Path]) -> None:
    """Frame source buat kelompok isi, dari rentang waktu subjeknya disebut di transcript. Buat referensi nyari klip."""
    subjects = {g["id"]: shots[g["shots"][0]]["subject"] for g in groups if g["id"] != "hook"}
    if not any(subjects.values()):
        return
    src = paths.source_mp4
    paths.plan_dir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        download_source(source["video_id"], src)
    total = probe(src, "plan")["duration_s"] or source.get("duration_s") or 0.0
    ranges = subject_ranges(source["transcript"], [s for s in subjects.values() if s], total)
    for group in groups:
        span = ranges.get(subjects.get(group["id"]) or "")
        if not span:
            continue
        start, end = span
        group["ref_frames"] = [
            extract_frame(src, min(start + (end - start) * pos, total - 0.05), paths.plan_dir / f"{group['id']}_{k}.jpg")
            .relative_to(paths.root).as_posix()
            for k, pos in enumerate(SOURCE_FRAMES)
        ]


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
            "countdown": (parse_countdown(beat["text"]) or _NO_COUNTDOWN).number,
        })
    groups = _groups(shots)
    _source_frames(paths, source, groups, shots, download_source)
    data = {
        "hook_seconds": hook_seconds,
        "segments": [{"index": s["index"], "start_s": s["start_s"], "end_s": s["end_s"], "frames": [rel(f) for f in s["frames"]]} for s in segs],
        "groups": groups,
        "shots": shots,
    }
    write_json_atomic(paths.shots_plan_json, data)
    log(f"[plan] {len(shots)} shot ({len(mapping)} hook), {len(data['groups'])} kelompok. Isi link: mayzfact brief {paths.root.name}")
    return data
