"""Konstanta dan aturan murni buat format FaktaCuil."""

from mayzfact.cta import SUBSCRIBE, clean

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
