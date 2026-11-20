"""Konstanta dan aturan murni buat format FaktaCuil."""

import math
import re

from mayzfact.countdown import parse_countdown
from mayzfact.cta import SUBSCRIBE, clean
from mayzfact.models import FaktaCuilCtaScene, Script

VOICE_SAMPLE_TEXT_ID: str = (
    "Kenapa kucing suka banget masuk ke kardus? Padahal kardus itu sempit dan nggak empuk. "
    "Tapi coba tekan like dulu, apakah like-mu berubah jadi madu? Ternyata ruang sempit bikin kucing "
    "merasa lebih aman, jadi dia bisa santai tanpa takut diganggu."
)

# Sampel Eric: 40 kata / 17,60 detik, eleven_v3, stability 0.5, tanpa delivery tag.
FAKTACUIL_RAW_WPS: float = 2.27


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
    tokens = [[clean(t) for t in _beat_text(b).split()] for b in beats]
    quiz = quiz_index(beats)
    # beat kuis nggak pernah jadi anchor walau kalimatnya nyebut "like"
    anchors = [i for i, toks in enumerate(tokens)
               if i != quiz and any(t.startswith("like") or t in SUBSCRIBE or t in ID_COMMENT for t in toks)]
    if not anchors:
        return []
    lo, hi = anchors[0], anchors[-1]
    for word in LINK_WORDS:  # beat objek/emoji tanpa "like" tetap kehitung bagian blok CTA
        if not any(t.startswith(word) for i in range(lo, hi + 1) for t in tokens[i]):
            if hi + 1 < len(beats) and hi + 1 != quiz and any(t.startswith(word) for t in tokens[hi + 1]):
                hi += 1
            elif lo > 0 and any(t.startswith(word) for t in tokens[lo - 1]):
                lo -= 1
    return list(range(lo, hi + 1))


QUIZ_PHRASE: str = "berapa kali aku bilang"
LINK_WORDS: tuple[str, ...] = ("muncul", "emoji")  # kata penghubung beat objek/emoji ke blok CTA


def _beat_text(beat) -> str:
    return beat["text"] if isinstance(beat, dict) else beat.text


def quiz_index(beats: list) -> int | None:
    """Index beat pertama yang nyebut frasa kuis, atau None."""
    return next((i for i, beat in enumerate(beats) if QUIZ_PHRASE in _beat_text(beat).lower()), None)


def count_word(text: str, word: str) -> int:
    """Kata utuh doang: "Kardus," dan "KARDUS" dihitung, "kardusnya"/"kardus-kardus" nggak."""
    return sum(1 for t in text.split() if clean(t) == word.lower())


def quiz_count(beats: list, word: str) -> int:
    """Jumlah `word` sebelum beat kuis; kalimat kuisnya sendiri nggak dihitung."""
    quiz = quiz_index(beats)
    if quiz is None:
        return 0
    return sum(count_word(_beat_text(b), word) for b in beats[:quiz])


# Format CTA FaktaCuil lama yang udah dihapus di CTA v2 (D-061); naskah lama ditolak, file dibiarin.
LEGACY_CTA_FORMATS: tuple[str, ...] = ("question", "reveal", "escape", "escalate")


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
    "toilet": ("kloset jongkok", "toilet"),
    "cat": ("kucing", "anak kucing"),
    "zebra": ("zebra", "zebra cross"),
}


def faktacuil_problems(script: Script) -> list[str]:
    """Aturan naskah FaktaCuil v2; F11 (panjang) dicek di check_script."""
    beats = script.beats
    problems: list[str] = []
    if any((c := parse_countdown(b.text)) and c.number is not None for b in beats):
        problems.append('FaktaCuil beats must not use "Number N," countdown announcements.')
    for n, b in enumerate(beats, start=1):
        if b.point or b.emoji or b.emoji_word:
            problems.append(f"FaktaCuil: panah cuma otomatis di shot pertama; beat {n} must have point=false and empty emoji fields.")
        if len(b.queries) < 2:
            problems.append(f"Beat {n} needs at least 2 search queries.")
        if any(not q.isascii() for q in b.queries):
            problems.append(f"Beat {n} search query must be English (ASCII only).")
    cta = faktacuil_cta_indices(beats)
    quiz = quiz_index(beats)
    scene = script.cta_scene
    fmt = scene.format if isinstance(scene, FaktaCuilCtaScene) else None
    if scene is None and cta:
        problems.append("FaktaCuil has CTA beats but no cta_scene. Set cta_scene or rewrite the beats.")
    elif scene is not None and not cta:
        problems.append("FaktaCuil cta_scene is set but no CTA beat was found. Write the CTA sentences from the skill.")
    if (quiz is None) != (script.cta_quiz is None):
        problems.append('FaktaCuil needs cta_quiz and the quiz beat ("berapa kali aku bilang") together, or neither.')
    if fmt == "emoji" and (quiz is not None or script.cta_quiz is not None):
        problems.append("FaktaCuil emoji CTA cannot be combined with the quiz.")
    if scene is not None and cta:
        problems.extend(_cta_problems(script, cta, fmt))
    if quiz is not None:
        problems.extend(_quiz_problems(script, quiz))
    for n, b in enumerate(beats, start=1):
        if b.keyword and (n - 1 in cta or n - 1 == quiz or clean(b.keyword) not in {clean(t) for t in b.text.split()}
                          or len(b.keyword.split()) != 1):
            problems.append(f"Beat {n} keyword {b.keyword!r} must be one word that appears in the beat text (and not in CTA beats).")
    return problems


def _cta_problems(script: Script, cta: list[int], fmt: str | None) -> list[str]:
    beats = script.beats
    problems: list[str] = []
    quiz = quiz_index(beats)
    if fmt == "emoji":
        if len(cta) > 2 or cta[-1] != len(beats) - 1:
            problems.append("FaktaCuil emoji CTA must be the last 1-2 beats.")
    else:
        if not 1 <= len(cta) <= 3:
            problems.append("FaktaCuil CTA must be one contiguous block of 1-3 beats.")
        if not [i for i in range(1, cta[0]) if i not in cta]:
            problems.append("FaktaCuil needs at least one misconception beat between the hook and the CTA.")
        answers = [i for i in range(cta[-1] + 1, len(beats)) if i != quiz]
        if len(answers) < 2:
            problems.append("FaktaCuil needs at least two answer beats after the CTA.")
    tokens = [beats[i].text.split() for i in cta]
    cleaned = {clean(t) for ts in tokens for t in ts}
    invites = sum(len(id_like_positions(ts)) for ts in tokens)
    if invites != 1 or cleaned & ID_COMMENT or (fmt != "subscribe" and cleaned & SUBSCRIBE):
        tail = "must not ask to comment." if fmt == "subscribe" else "must not ask to subscribe or comment."
        problems.append(f'FaktaCuil CTA must invite exactly one like ("tekan like") and {tail}')
    if fmt == "subscribe" and not cleaned & SUBSCRIBE:
        problems.append('FaktaCuil subscribe CTA must ask to subscribe ("subscribe if it worked").')
    if fmt in ("lucky", "subscribe"):
        theme = script.cta_scene.theme
        nouns = "|".join(re.escape(n) for n in THEME_NOUNS_ID[theme])
        if not any(clean(t).startswith("muncul") for ts in tokens for t in ts):
            problems.append("FaktaCuil CTA must say 'muncul' so the object beat stays inside the block.")
        if not any(re.search(rf"\b(?:{nouns})\b", beats[i].text, re.I) for i in cta):
            problems.append(f"FaktaCuil CTA must name the sticker object {theme!r}; "
                            "if that object has no sticker yet, make one first.")
    if fmt == "emoji":
        if "emoji" not in cleaned or not beats[cta[-1]].text.rstrip().endswith("?"):
            problems.append("FaktaCuil emoji CTA must say 'emoji' and its last beat must end with '?'.")
    for i in cta:
        tokens_i = [clean(t) for t in beats[i].text.split()]
        linked = any(t.startswith("muncul") or t.startswith("emoji") or t in SUBSCRIBE for t in tokens_i)
        if any(t.startswith("like") for t in tokens_i) and not (id_like_positions(beats[i].text.split()) or linked):
            problems.append(f"Beat {i + 1} uses 'like' outside the CTA; rephrase it so it is not part of the CTA block.")
            continue
        if beats[i].subject:
            problems.append(f"CTA beat {i + 1} must have an empty subject.")
    return problems


def _quiz_problems(script: Script, quiz: int) -> list[str]:
    beats = script.beats
    problems: list[str] = []
    if quiz != len(beats) - 1:
        problems.append("FaktaCuil quiz beat must be the last beat.")
    if beats[quiz].subject:
        problems.append(f"CTA beat {quiz + 1} must have an empty subject.")
    config = script.cta_quiz
    if config is None:
        return problems
    if clean(config.word) not in {clean(t) for t in beats[quiz].text.split()}:
        problems.append(f"FaktaCuil quiz beat must name cta_quiz.word {config.word!r}.")
    count = quiz_count(beats, config.word)
    if count < 2:
        problems.append(f"FaktaCuil {config.word!r} must be said at least twice before the quiz.")
    elif config.answer != count:
        problems.append(f"cta_quiz.answer is {config.answer} but {config.word!r} is said {count} times before the quiz beat. "
                        f"Set answer to {count}.")
    return problems
