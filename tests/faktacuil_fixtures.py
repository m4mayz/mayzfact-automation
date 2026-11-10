"""Naskah FaktaCuil terkontrol buat test; bukan output TTS/API produksi."""
from mayzfact.models import Beat, CtaScene, Script

SOURCE_TEXT_EN = (
    "Cats love boxes because small spaces make them feel safe. "
    "A box is a hiding place where they can relax without being disturbed. "
    "Studies of shelter cats show that boxes lower stress. "
    "The cardboard also keeps their body heat in."
)


def faktacuil_script(total_words: int = 69) -> Script:
    texts = [
        "Kenapa kucing suka banget,",
        "masuk ke kardus yang sempit?",
        "Padahal kardus itu keras dan nggak empuk,",
        "dan sempit buat badan mereka.",
        "Tapi coba tekan like dulu,",
        "apakah like-mu berubah jadi madu?",
        "Ternyata ruang sempit bikin kucing merasa aman,",
        "jadi dia bisa santai tanpa takut diganggu,",
        "dan itu naluri bawaan mereka.",
    ]
    # Filler unik cuma di beat non-CTA (4-5 dibiarin) buat ngatur jumlah kata.
    delta = total_words - sum(len(t.split()) for t in texts)
    for i in [2, 3, 6, 7, 8, 0, 1]:
        while delta > 0 and len(texts[i].split()) < 10:
            texts[i] = texts[i].rstrip(",.?") + f" fixture{i}x{delta},"
            delta -= 1
    assert delta == 0
    keywords = {2: "kardus", 6: "kucing"}
    return Script(
        narration_mode="faktacuil",
        cta_scene=CtaScene(theme="honey", transform_word="berubah", comment_text="MADU"),
        beats=[
            Beat(text=t, media="photo" if i in [1, 3, 7] else "video",
                 queries=["cat in box", "cat cardboard box"], subject="" if i in (4, 5) else "cat", keyword=keywords.get(i, ""))
            for i, t in enumerate(texts)
        ],
    )


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
