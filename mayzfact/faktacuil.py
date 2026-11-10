"""Konstanta dan aturan murni buat format FaktaCuil."""

import math
import re

from mayzfact.countdown import parse_countdown
from mayzfact.cta import SUBSCRIBE, clean
from mayzfact.models import Script

VOICE_SAMPLE_TEXT_ID: str = (
    "Kenapa kucing suka banget masuk ke kardus? Padahal kardus itu sempit dan nggak empuk. "
    "Tapi coba tekan like dulu, apakah like-mu berubah jadi madu? Ternyata ruang sempit bikin kucing "
    "merasa lebih aman, jadi dia bisa santai tanpa takut diganggu."
)

# Asumsi awal; dikalibrasi dari sampel yang dipilih Akmal.
FAKTACUIL_RAW_WPS: float = 2.5


ID_LIKE_VERBS = {"tekan", "pencet", "klik", "kasih", "tekanlah"}
ID_COMMENT = {"komen", "komentar", "comment"}


def _like_verb_index(tokens: list[str], j: int) -> int | None:
    """Index kata kerja ajakan sebelum `like` ("tekan like", "tekan tombol like"), atau None."""
    for k in (j - 1, j - 2):
        if k < 0:
            break
        if clean(tokens[k]) in ID_LIKE_VERBS:
            return k
        if k == j - 1 and clean(tokens[k]) != "tombol":
            break
    return None


def id_like_positions(tokens: list[str]) -> list[int]:
    return [j for j, t in enumerate(tokens) if clean(t) == "like" and _like_verb_index(tokens, j) is not None]


def id_like_begin(tokens: list[str], j: int) -> int:
    verb = _like_verb_index(tokens, j)
    if verb is None:
        return j
    return verb - 1 if verb and clean(tokens[verb - 1]) == "coba" else verb


def faktacuil_cta_indices(beats: list) -> list[int]:
    anchors = []
    for i, beat in enumerate(beats):
        text = beat["text"] if isinstance(beat, dict) else beat.text
        tokens = [clean(t) for t in text.split()]
        if any(t.startswith("like") or t in SUBSCRIBE or t in ID_COMMENT for t in tokens):
            anchors.append(i)
    return list(range(anchors[0], anchors[-1] + 1)) if anchors else []


def faktacuil_word_range(video_speed: float) -> tuple[int, int, int]:
    """(target, bawah, atas) jumlah kata buat final 25 detik (20-30 detik)."""
    from mayzfact.narration import validate_video_speed

    validate_video_speed(video_speed)
    k = video_speed * FAKTACUIL_RAW_WPS
    # round(…, 6) buang noise float, misal 20 * 2.2 = 44.00000000000001
    return round(25 * k), math.ceil(round(20 * k, 6)), math.floor(round(30 * k, 6))


THEME_NOUNS_ID: dict[str, tuple[str, ...]] = {
    "volcano": ("gunung berapi", "gunung meletus", "gunung api"),
    "unicorn": ("unicorn",),
    "honey": ("madu",),
    "puppy": ("anak anjing", "anjing"),
    "lion": ("singa",),
    "shark": ("hiu", "ikan hiu"),
}


def faktacuil_problems(script: Script) -> list[str]:
    """Aturan F1-F10 naskah FaktaCuil; F11 (panjang) dicek di check_script."""
    from mayzfact.narration import cta_indices

    beats = script.beats
    problems: list[str] = []
    if not (re.match(r"\s*kenapa\b", beats[0].text, re.I) and any("?" in b.text for b in beats[:2])):
        problems.append('FaktaCuil hook must open with "Kenapa" and end the question with "?" within the first two beats.')
    if any((c := parse_countdown(b.text)) and c.number is not None for b in beats):
        problems.append('FaktaCuil beats must not use "Number N," countdown announcements.')
    cta = cta_indices(script)
    if not 1 <= len(cta) <= 3:
        problems.append("FaktaCuil CTA must be one contiguous block of 1-3 beats.")
    for n, b in enumerate(beats, start=1):
        if b.point or b.emoji or b.emoji_word:
            problems.append(f"FaktaCuil does not use arrows or emoji; beat {n} must have point=false and empty emoji fields.")
    if cta:
        problems.extend(_cta_problems(script, cta))
    for n, b in enumerate(beats, start=1):
        if b.keyword and (n - 1 in cta or clean(b.keyword) not in {clean(t) for t in b.text.split()}
                          or len(b.keyword.split()) != 1):
            problems.append(f"Beat {n} keyword {b.keyword!r} must be one word that appears in the beat text (and not in CTA beats).")
    return problems


def _cta_problems(script: Script, cta: list[int]) -> list[str]:
    beats = script.beats
    problems: list[str] = []
    hook_end = next((i for i, b in enumerate(beats) if "?" in b.text), 1)
    if not [i for i in range(hook_end + 1, cta[0]) if i not in cta]:
        problems.append("FaktaCuil needs at least one misconception beat between the hook question and the CTA.")
    if len(range(cta[-1] + 1, len(beats))) < 2:
        problems.append("FaktaCuil needs at least two answer beats after the CTA.")
    tokens = [beats[i].text.split() for i in cta]
    cleaned = {clean(t) for ts in tokens for t in ts}
    if sum(len(id_like_positions(ts)) for ts in tokens) != 1 or cleaned & (SUBSCRIBE | ID_COMMENT):
        problems.append('FaktaCuil CTA must invite exactly one like ("tekan like") and must not ask to subscribe or comment.')
    theme, word = script.cta_scene.theme, script.cta_scene.transform_word
    nouns = "|".join(re.escape(n) for n in THEME_NOUNS_ID[theme])
    pattern = rf"\bjadi\s+(?:seekor\s+|sebuah\s+)?(?:{nouns})\b"
    if not any(re.search(rf"\b{re.escape(word)}\b", beats[i].text, re.I) and beats[i].text.rstrip().endswith("?")
               and re.search(pattern, beats[i].text, re.I) for i in cta):
        problems.append(f"CTA illustration {theme!r} does not match the narrated transformation object. "
                        "Use the matching supported illustration; unsupported objects need an illustration first.")
    for i in cta:
        if beats[i].subject:
            problems.append(f"CTA beat {i + 1} must have an empty subject.")
        if beats[i].point:
            problems.append(f"CTA beat {i + 1} must have point=false.")
    return problems
