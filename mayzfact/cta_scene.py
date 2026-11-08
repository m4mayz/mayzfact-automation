"""Stage scene CTA dari kata alignment asli, atau batas struktur yang dilabeli jujur."""
from __future__ import annotations

import math
import re

from mayzfact.countdown import parse_countdown
from mayzfact.cta import COMMENT, SUBSCRIBE, clean, cta_kinds, is_like_cta
from mayzfact.narration import cta_beat_indices


def build_scene(script: dict, shots: list[dict], entries: list[dict], words: list[dict], beat_of: list[int],
                countdown: list[dict], total: int) -> dict | None:
    config = script.get('cta_scene')
    if not config or script.get('narration_mode') != 'top3':
        return None
    beats = script['beats']
    allowed = set(cta_beat_indices(beats))
    spans = [(s, e) for s, e in zip(shots, entries) if s.get('beat') in allowed]
    if not spans:
        return None
    start = min(e['from'] for _, e in spans)
    one = next((i for i, b in enumerate(beats) if (c := parse_countdown(b['text'])) and c.number == 1), len(beats))
    stop = next((c['numberFrom'] for c in countdown if c['number'] == 1),
                min((e['from'] for s, e in zip(shots, entries) if s.get('beat', -1) >= one), default=total))
    if stop <= start:
        return None
    cues = {}
    like_begin = None
    for beat in sorted(allowed):
        local = [w for w, b in zip(words, beat_of) if b == beat]
        for i, w in enumerate(local):
            token = clean(w['text'])
            kind = ('transform' if token == config['transform_word'].lower() else
                    'subscribe' if token in SUBSCRIBE else 'comment' if token in COMMENT else
                    'like' if is_like_cta([x['text'] for x in local], i) else None)
            frame = int(math.floor(w['start_s'] * 30 + .5))
            if kind and start <= frame < stop and kind not in cues:
                cues[kind] = dict(kind=kind, word=w['text'], **{'from': frame})
                if kind == 'like':
                    # Mulai saat frasa ajakan terdengar; klik tetap di kata like.
                    begin = i
                    if i >= 1 and clean(local[i-1]['text']) in {'tap', 'tapping', 'hit', 'press', 'smash'}:
                        begin = i-1
                        if i >= 2 and clean(local[i-2]['text']) == 'try':
                            begin = i-2
                    like_begin = max(start, int(math.floor(local[begin]['start_s'] * 30 + .5)))
    bounds = {}
    for beat in sorted(allowed):
        text = beats[beat]['text']
        kinds = cta_kinds(text)
        if re.search(rf"\b{re.escape(config['transform_word'])}\b", text, re.I):
            kinds.add('transform')
        first = min((e['from'] for s, e in spans if s.get('beat') == beat), default=None)
        if first is not None:
            for kind in kinds:
                bounds.setdefault(kind, first)
    for kind, cue in cues.items():
        if kind != 'like':
            bounds[kind] = cue['from']
    if like_begin is not None:
        bounds['like'] = like_begin
    ordered = sorted(bounds.items(), key=lambda item: (item[1], ['like', 'transform', 'subscribe', 'comment'].index(item[0])))
    stages = []
    for i, (kind, begin) in enumerate(ordered):
        end = min(stop, ordered[i + 1][1] if i + 1 < len(ordered) else stop)
        if end <= begin:
            continue
        stage = dict(kind=kind, durationInFrames=end-begin, timing='word' if kind in cues and (begin == cues[kind]['from'] or kind == 'like' and begin == like_begin) else 'structure',
                     **{'from': begin})
        if kind in cues:
            stage['triggerAt'] = cues[kind]['from'] - begin
        stages.append(stage)
    return dict(theme=config['theme'], label=config.get('label', ''), commentText=config['comment_text'],
                durationInFrames=stop-start, stages=stages,
                cues=sorted(cues.values(), key=lambda c: c['from']), **{'from': start})
