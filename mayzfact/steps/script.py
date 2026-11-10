"""Aturan naskah: dicek pas `mayzfact check-script` dan sebelum TTS. Naskahnya ditulis agent, bukan di sini."""

from __future__ import annotations

import re

from mayzfact.countdown import parse_countdown
from mayzfact.cta import cta_kinds
from mayzfact.errors import PipelineError
from mayzfact.models import Script
from mayzfact.store import RunPaths, read_json
from mayzfact.text import clean_text, ngram_overlap, words

PHOTO_SHARE_RANGE = (0.15, 0.45)
MAX_NGRAM_OVERLAP = 0.15
MAX_BEAT_WORDS = 10  # ±4.5 detik dengan 2.2 kata/detik


def normalize_script(script: Script) -> Script:
    """Bersihin teks & keyword, lalu paksa beat pertama jadi video."""
    beats = [
        b.model_copy(update={
            "text": clean_text(b.text), "queries": [q.strip() for q in b.queries if q.strip()],
            "subject": " ".join(b.subject.split()),
        })
        for b in script.beats
    ]
    if beats:
        beats[0] = beats[0].model_copy(update={"media": "video"})
    return script.model_copy(update={"beats": beats})


def narration_word_range(script: Script, video_speed: float = 1.1) -> tuple[int, int, int]:
    from mayzfact.narration import cta_beat_indices, top3_word_range

    # Persetujuan panjang per-run mengunci jumlah kata, bukan melewati cek lain.
    if script.approved_word_count is not None:
        count = script.approved_word_count
        return count, count, count
    # Anggaran isi tetap; hanya kata CTA di atas allowance lama yang ditambahkan.
    extra = max(0, sum(len(words(script.beats[i].text)) for i in cta_beat_indices(script.beats)) - 10)
    target, low, high = top3_word_range(video_speed)
    return target + extra, low + extra, high + extra


def check_script(script: Script, source_text: str,
                 bgm_choices: list[str] | None = None, *, video_speed: float = 1.1) -> tuple[list[str], float]:
    """Balikin (daftar masalah, overlap). Pesan pakai English biar bisa ditempel balik ke agent mana pun."""
    if not script.beats:
        return ["The script has no beats."], 0.0
    problems: list[str] = []
    from mayzfact.narration import cta_beat_indices, cta_kinds_for_beats, top3_problems

    problems.extend(top3_problems(script, source_text))
    theme = script.cta_scene.theme
    # Pakai clause transformasi asli, bukan instruksi comment atau teks kutipannya.
    cta_text = " ".join(script.beats[i].text for i in cta_beat_indices(script.beats))
    cta_text = re.sub(r'''"[^"]*"|“[^”]*”|(?<!\w)'.*?'(?!\w)|‘.*?’(?!\w)''', " ", cta_text)
    cta_text = re.split(r"\bcomment\b", cta_text, maxsplit=1, flags=re.I)[0]
    transform_text = next((clause for clause in re.split(r"[.!?;]", cta_text)
                           if re.search(rf"\b{re.escape(script.cta_scene.transform_word)}\b", clause, re.I)
                           and re.search(r"\binto\b", clause, re.I)), "")
    if not re.search(rf"\binto\s+(?:(?:a|an|the)\s+)?{re.escape(theme)}\b", transform_text, re.I):
        problems.append(f"CTA illustration {theme!r} does not match the narrated transformation object. "
                        "Use the matching supported illustration; unsupported objects need an illustration first.")
    full_text = " ".join(b.text for b in script.beats)
    count = len(words(full_text))
    _, low, high = narration_word_range(script, video_speed)
    if not low <= count <= high:
        problems.append(f"The narration has {count} words; it must have between {low} and {high}.")
    share = sum(b.media == "photo" for b in script.beats) / len(script.beats)
    share_low, share_high = PHOTO_SHARE_RANGE
    if not share_low <= share <= share_high:
        problems.append(
            f"{share:.0%} of the beats use a photo; it must be between {share_low:.0%} and {share_high:.0%}."
        )
    for number, beat in enumerate(script.beats, start=1):
        if not beat.text:
            problems.append(f"Beat {number} has empty text.")
        beat_words = len(words(beat.text))
        if beat_words > MAX_BEAT_WORDS:
            problems.append(
                f"Beat {number} has {beat_words} words; split it so every beat has at most {MAX_BEAT_WORDS} words."
            )
        if not beat.queries:
            problems.append(f"Beat {number} has no search queries.")
    countdown_indices = [
        (i, parse_countdown(b.text))
        for i, b in enumerate(script.beats)
        if parse_countdown(b.text) and parse_countdown(b.text).number is not None
    ]
    ctas = set(cta_beat_indices(script.beats))
    for idx_in_list, (beat_idx, _) in enumerate(countdown_indices):
        next_beat_idx = (
            countdown_indices[idx_in_list + 1][0]
            if idx_in_list + 1 < len(countdown_indices)
            else len(script.beats)
        )
        explanation_count = sum(i not in ctas for i in range(beat_idx + 1, next_beat_idx))
        if explanation_count < 2:
            problems.append(
                f"Countdown item '{script.beats[beat_idx].text.strip()}' has only {explanation_count} explanation beat(s); "
                f"each item must have at least 2 beats describing it."
            )
    # Aturan pemicunya sama persis dengan animasi CTA di timeline (mayzfact.cta), biar yang lolos cek beneran kepicu.
    present_cta = cta_kinds_for_beats(script.beats)
    missing_cta = sorted(cta_kinds(source_text) - present_cta)
    if missing_cta:
        hint = {"like": 'an inviting "like" (hit like / like and subscribe)', "subscribe": '"subscribe"', "comment": '"comment"'}
        problems.append("The source asks viewers to " + " and ".join(missing_cta) + "; the script must say "
                        + ", ".join(hint[w] for w in missing_cta) + " too (that is what triggers the on-screen CTA).")
    if bgm_choices is not None and script.bgm and script.bgm not in bgm_choices:
        problems.append(f"bgm {script.bgm!r} is not in assets/bgm. Choose one of: {', '.join(bgm_choices) or '(none)'}.")
    # Beat "Number N, subject" wajib sama persis dengan source, jadi nggak ikut dihitung sebagai jiplakan.
    prose = " ".join(b.text for b in script.beats if not (parse_countdown(b.text) and parse_countdown(b.text).number is not None))
    overlap = ngram_overlap(prose, source_text)
    if overlap > MAX_NGRAM_OVERLAP:
        problems.append(
            f"{overlap:.0%} of the 4-word phrases are copied from the source; "
            f"keep it at or below {MAX_NGRAM_OVERLAP:.0%}. Rephrase more."
        )
    return problems, overlap


AWAIT_SCRIPT_HINT = ("Naskah belum ada. Agent nulis runs/<id>/script.json (lihat .agents/skills/bikin-short/SKILL.md), "
                     "terus cek: uv run mayzfact check-script <id>")


def load_script(paths: RunPaths) -> Script:
    if not paths.script_json.exists():
        raise PipelineError("script", f"{paths.script_json} belum ada. {AWAIT_SCRIPT_HINT}")
    try:
        raw = read_json(paths.script_json)
        mode = raw.get("narration_mode") if isinstance(raw, dict) else None
        if mode != "top3":
            shown = "nggak ada" if mode is None else repr(mode)
            raise PipelineError("script", f"script.json pakai format lama (narration_mode: {shown}). Pipeline sekarang cuma "
                                          f'support narration_mode "top3" (D-050). File run ini dibiarin apa adanya; '
                                          f"bikin run baru pakai format top3.")
        if "cta_scene" not in raw:
            raise PipelineError("script", "script.json belum punya cta_scene. Format top3 sekarang wajib cta_scene (D-050). "
                                          "Tambahin cta_scene sesuai skill bikin-short langkah 2; ini metadata visual, "
                                          "hash suara nggak berubah.")
        return normalize_script(Script(**raw))
    except (ValueError, TypeError) as exc:  # JSON rusak atau field kurang (ValidationError juga ValueError)
        raise PipelineError("script", f"script.json nggak valid (cek JSON/field-nya): {str(exc)[:300]}") from exc


def check_script_file(paths: RunPaths, source: dict, *,
                      bgm_choices: list[str] | None, video_speed: float = 1.1) -> list[str]:
    """Cek runs/<id>/script.json yang ditulis agent pakai aturan yang sama kayak check_script."""
    script = load_script(paths)
    source_text = " ".join(s["text"] for s in source["transcript"])
    try:
        problems, _ = check_script(script, source_text, bgm_choices, video_speed=video_speed)
    except ValueError as exc:
        raise PipelineError("script", str(exc)) from exc
    return problems
