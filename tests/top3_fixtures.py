"""Naskah terkontrol buat test Top 3; bukan output TTS/API produksi."""
from mayzfact.models import Beat, CtaScene, Script

SOURCE_TEXT = (
    'Number five, wood frogs. Frozen winter. Number four, archerfish. Water jets. '
    'Number three, basilisk lizards. They sprint over water. '
    'Number two, immortal jellyfish. Their life cycle changes. '
    'Number one, tardigrades. Dormant creatures survive.'
)


def top3_script(total_words=80):
    texts = [
        'These three animals have unusual survival tricks.',
        'Number three, basilisk lizards.',
        'They can sprint briefly across water,',
        'using fast movements and specialized feet.',
        'Number two, immortal jellyfish.',
        'Under certain conditions they reverse development,',
        'potentially repeating an earlier stage.',
        "Subscribe, it turns into a volcano, like,",
        "or comment 'nope'.",
        'Number one, tardigrades.',
        'They can endure radiation and dehydration while dormant,',
        "even space's vacuum under certain conditions.",
    ]
    # Filler unik hanya untuk menguji batas anggaran, tanpa mengubah struktur fixture.
    delta = total_words - sum(len(t.split()) for t in texts)
    for i in [2, 3, 5, 6, 10, 11, 0]:
        while delta > 0 and len(texts[i].split()) < 10:
            texts[i] = texts[i].rstrip(',.') + f' fixture{i}x{delta},'
            delta -= 1
    assert delta == 0
    return Script(narration_mode='top3',
                  cta_scene=CtaScene(theme='volcano', transform_word='turns', comment_text='NOPE'),
                  beats=[
        Beat(text=t, media='photo' if i in [1, 4, 9] else 'video', queries=['animal close up', 'animal behavior'],
             subject='lizard' if i in [1,2,3] else 'jellyfish' if i in [4,5,6] else 'tardigrade' if i >= 9 else '')
        for i,t in enumerate(texts)
    ])


APPROVED_CTA = [
    'But before number one, try tapping like.',
    'Did the button turn into a volcano?',
    'Subscribe if it worked,',
    "and comment 'erupted'.",
]


def playful_script(base_words=80):
    script = top3_script(base_words)
    script.beats[7:9] = [Beat(media='video', text=text, queries=['phone button close up', 'hand tapping phone'])
                         for text in APPROVED_CTA]
    script.cta_scene = CtaScene(theme='volcano', transform_word='turn', comment_text='ERUPTED')
    return script
