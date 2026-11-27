"""Naskah FaktaCuil terkontrol buat test; bukan output TTS/API produksi."""
from mayzfact.models import Beat, Script

SOURCE_TEXT_EN = (
    "Cats love boxes because small spaces make them feel safe. "
    "A box is a hiding place where they can relax without being disturbed. "
    "Studies of shelter cats show that boxes lower stress. "
    "The cardboard also keeps their body heat in."
)

QUERIES = ["cat in box", "cat cardboard box"]


def faktacuil_script(total_words: int = 69, cta: str = "lucky") -> Script:
    """Naskah FaktaCuil v2; `cta` milih kombinasi CTA (none/lucky/subscribe/emoji/quiz/lucky+quiz/subscribe+quiz)."""
    valid = {"none", "lucky", "subscribe", "emoji", "quiz", "lucky+quiz", "subscribe+quiz"}
    if cta not in valid:
        raise ValueError(f"cta nggak dikenal: {cta!r}")
    base, _, extra = cta.partition("+")
    kind = "none" if base == "quiz" else base
    with_quiz = "quiz" in (base, extra)

    rows = [
        {"text": "Kenapa kucing suka banget,", "media": "video", "keyword": ""},
        {"text": "masuk ke kardus yang sempit?", "media": "photo", "keyword": ""},
        {"text": "Padahal kardus itu keras dan nggak empuk,", "media": "video", "keyword": "kardus"},
        {"text": "dan sempit buat badan mereka.", "media": "photo", "keyword": ""},
    ]
    cta_texts = {
        "lucky": ["Tapi sebelum lanjut, coba tekan like,", "jika beruntung bisa muncul madu."],
        "subscribe": ["Tapi sebelum lanjut, coba tekan like,", "nanti muncul madu, subscribe jika berhasil."],
    }
    if kind in cta_texts:
        rows += [{"text": t, "media": "video", "keyword": "", "cta": True} for t in cta_texts[kind]]
    rows += [
        {"text": "Ternyata ruang sempit bikin kucing merasa aman,", "media": "video", "keyword": "kucing"},
        {"text": "jadi dia bisa santai tanpa takut diganggu,", "media": "photo", "keyword": ""},
        {"text": "dan itu naluri bawaan mereka.", "media": "video", "keyword": ""},
    ]
    if kind == "emoji":
        rows.append({"text": "Tapi mengapa ada emoji madu saat tekan like?", "media": "video", "keyword": "", "cta": True})
    if with_quiz:
        rows.append({"text": "Nah coba tebak berapa kali aku bilang kardus?", "media": "video", "keyword": "", "cta": True})

    # Filler unik cuma di beat isi (bukan CTA/kuis) buat ngatur jumlah kata.
    delta = total_words - sum(len(r["text"].split()) for r in rows)
    order = [2, 3, 6, 7, 8, 0, 1, 4, 5, 9]
    fill = [i for i in order if i < len(rows) and not rows[i].get("cta")]
    fill += [i for i in range(len(rows)) if not rows[i].get("cta") and i not in fill]
    for i in fill:
        while delta > 0 and len(rows[i]["text"].split()) < 10:
            rows[i]["text"] = rows[i]["text"].rstrip(",.?") + f" fixture{i}x{delta},"
            delta -= 1
    assert delta == 0

    scenes = {
        "lucky": {"format": "lucky", "theme": "honey"},
        "subscribe": {"format": "subscribe", "theme": "honey"},
        "emoji": {"format": "emoji", "emoji": "🍯"},
    }
    return Script(
        narration_mode="faktacuil",
        cta_scene=scenes.get(kind),
        cta_quiz={"word": "kardus", "answer": 2} if with_quiz else None,
        beats=[
            Beat(text=r["text"], media=r["media"], queries=list(QUERIES),
                 subject="" if r.get("cta") else "cat", keyword=r["keyword"])
            for r in rows
        ],
    )


def emoji_question_script() -> dict:
    script = faktacuil_script(total_words=57, cta="none").model_dump()
    script["cta_scene"] = {"format": "emoji_question", "emoji": "🐈‍⬛"}
    script["beats"].extend([
        Beat(text=text, media="video", queries=list(QUERIES)).model_dump()
        for text in ("Lalu mengapa ada kucing hitam", "saat kamu menekan tombol like?")
    ])
    return script


def faktacuil_timeline_fixture(duration: float = 25, script: dict | None = None):
    """(script, alignment, clips) dengan 1 shot per beat, pola timeline_fixture di test_cta_scene."""
    from mayzfact.text import script_text
    from mayzfact.timing import beat_timings
    from tests.factories import fake_alignment

    script = script or faktacuil_script().model_dump()
    alignment = fake_alignment(script_text(script["beats"]), duration)
    times = beat_timings([b["text"] for b in script["beats"]], alignment, duration)
    clips = {"shots": [dict(file=f"clips/shot_{i}.mp4", kind="video", start_s=t["start_s"], end_s=t["end_s"],
                            width=1080, height=1920, beat=i) for i, t in enumerate(times)]}
    return script, alignment, clips
