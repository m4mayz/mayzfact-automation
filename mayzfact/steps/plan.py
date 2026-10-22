"""Step plan (mode manual): daftar shot + frame referensi hook + keyword buat brief (spec metode manual bagian 3)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from mayzfact.countdown import Countdown, parse_countdown
from mayzfact.errors import PipelineError
from mayzfact.ffmpeg import extract_frame, probe
from mayzfact.matching import hook_slot_map
from mayzfact.shots import beat_subjects, split_shots, tighten_countdown
from mayzfact.source_frames import prepare_source_segments
from mayzfact.store import RunPaths, write_json_atomic
from mayzfact.text import beat_texts, words
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
    return list(groups.values())


def _shot_frames(paths: RunPaths, source: dict, shots: list[dict], voice_total_s: float,
                 download_source: Callable[[str, Path], Path], log: Callable[[str], None] = print) -> None:
    """3 frame source per shot buat referensi nyari klip: rentang subjeknya di transcript, atau posisi proporsional."""
    todo = [s for s in shots if not s["ref_frames"]]
    if not todo:
        return
    src = paths.source_mp4
    paths.plan_dir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        download_source(source["video_id"], src)
    total = probe(src, "plan")["duration_s"] or source.get("duration_s") or 0.0
    # Urut card countdown: beat pembuka bisa nyebut subjek nomor 1 duluan, padahal di source dibahas paling akhir.
    names = {s["subject"] for s in shots if s.get("subject")}
    order = sorted(names, key=lambda name: next((s["index"] for s in shots if s.get("subject") == name and s.get("countdown")),
                                                 next(s["index"] for s in shots if s.get("subject") == name)))
    ranges = subject_ranges(source["transcript"], order, total)
    for shot in todo:
        span = ranges.get(shot.get("subject") or "")
        if span is None:  # CTA/intro/subjek nggak ketemu: posisi beat di naskah dipetain ke durasi source
            scale = total / voice_total_s if voice_total_s else 0.0
            span = (shot["start_s"] * scale, shot["end_s"] * scale)
        start, end = span
        try:
            shot["ref_frames"] = [
                extract_frame(src, max(0.0, min(start + (end - start) * pos, total - 0.05)),
                              paths.plan_dir / f"shot_{shot['index'] + 1:02d}_{k}.jpg").relative_to(paths.root).as_posix()
                for k, pos in enumerate(SOURCE_FRAMES)
            ]
        except PipelineError as exc:  # 1 shot gagal jangan bikin plan gagal; brief yang nolak nanti
            log(f"[plan] frame shot {shot['index'] + 1} gagal: {exc.message.splitlines()[0][:120]}")


def run_plan(
    paths: RunPaths,
    script: dict,
    tts: dict,
    source: dict,
    *,
    max_shot_s: float,
    hook_seconds: float,
    download_source: Callable[[str, Path], Path],
    log: Callable[[str], None] = print,
) -> dict:
    beats = script["beats"]
    slots = split_shots(beat_timings(beat_texts(beats), tts["alignment"], tts["duration_s"]), beats, max_shot_s)
    slots = tighten_countdown(slots, beats, tts["alignment"])
    subjects = beat_subjects(beats)
    segs = prepare_source_segments(paths, source, download_source, hook_seconds, paths.plan_dir, retry_step="plan") if hook_seconds > 0 else []
    mapping = hook_slot_map(slots, len(segs), hook_seconds)
    hook_queries = script.get("hook_queries", {})  # ditulis agent sambil lihat frame plan/seg_*.jpg

    def rel(path: Path) -> str:
        return path.relative_to(paths.root).as_posix()

    shots = []
    for slot in slots:
        beat = beats[slot.beat]
        segment = mapping.get(slot.index)
        if segment is not None:
            given = hook_queries.get(str(segment))
            if given and (given.get("en") or given.get("zh")):
                keywords = {"en": list(given.get("en", [])), "zh": list(given.get("zh", []))}
            else:  # agent nggak ngisi: 8 kata pertama transcript segmen itu
                snippet = " ".join(words(segs[segment]["transcript"])[:8])
                keywords = {"en": [snippet] if snippet else [], "zh": []}
            ref_frames = [rel(f) for f in segs[segment]["frames"]]
        else:
            keywords = {"en": list(beat["queries"]), "zh": list(beat.get("queries_zh", []))}
            ref_frames = []
        shots.append({
            "index": slot.index, "beat": slot.beat, "start_s": slot.start_s, "end_s": slot.end_s, "media": slot.media,
            "text": beat["text"], "subject": subjects[slot.beat], "hook_segment": segment,
            "ref_frames": ref_frames, "keywords": keywords,
            "countdown": (parse_countdown(beat["text"]) or _NO_COUNTDOWN).number,
        })
    _shot_frames(paths, source, shots, tts["duration_s"], download_source, log)
    groups = _groups(shots)
    data = {
        "hook_seconds": hook_seconds,
        "segments": [{"index": s["index"], "start_s": s["start_s"], "end_s": s["end_s"], "frames": [rel(f) for f in s["frames"]]} for s in segs],
        "groups": groups,
        "shots": shots,
    }
    write_json_atomic(paths.shots_plan_json, data)
    log(f"[plan] {len(shots)} shot ({len(mapping)} hook), {len(data['groups'])} kelompok. Isi link: mayzfact brief {paths.root.name}")
    return data
