"""Background CTA dekoratif: cuma klip lokal yang sudah tampil, tanpa download/ML."""
from __future__ import annotations

import hashlib
import math
import random

from mayzfact.ffmpeg import probe
from mayzfact.store import RunPaths


def reuse_backgrounds(shots: list[dict], earlier: list[dict], paths: RunPaths) -> list[dict]:
    if not shots:
        return []
    start = min(s['start_s'] for s in shots)
    pool = []
    for clip in sorted(earlier, key=lambda c: c['index']):
        if clip.get('auto_cta') or clip['kind'] != 'video' or clip['end_s'] > start + 1e-6:
            continue
        try:
            frames = math.floor((probe(paths.root / clip['file'], 'fetch')['duration_s'] or 0) * 30 + 1e-6)
            if frames > 1:
                pool.append((clip, frames))
        except Exception:
            continue  # hiasan gagal dibaca: fallback warna, bukan minta link CTA
    seed = hashlib.sha256('|'.join(f"{s['index']}:{s['text']}" for s in shots).encode()).hexdigest()
    rng = random.Random(seed)
    cursors = {c['file']: rng.randrange(1, n) for c, n in pool}
    out = []
    elapsed = 0
    for shot in sorted(shots, key=lambda s: s['index']):
        base = dict(index=shot['index'], beat=shot['beat'], start_s=shot['start_s'], end_s=shot['end_s'],
                    auto_cta=True, reused=True, match=None, query='decorative reuse', hook_segment=None)
        duration = round(shot['end_s'] * 30) - round(shot['start_s'] * 30)
        if pool:
            clip, frames = rng.choice(pool)
            offset = cursors[clip['file']]
            out.append({**clip, **base, 'reused_from': clip['index'], 'clipOffset': offset,
                        'loopFrames': frames, 'source_s': clip.get('source_s', 0) + (offset % frames) / 30})
            cursors[clip['file']] += duration
        else:
            out.append({**base, 'kind': 'video', 'file': '', 'width': 1080, 'height': 1920,
                        'generated': True, 'clipOffset': elapsed, 'page_url': '', 'source_s': 0})
        elapsed += duration
    return out
