"""Fixture render lokal CTA; synthetic alignment berlabel, tanpa source run/voice/API."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from mayzfact.cta_background import reuse_backgrounds
from mayzfact.narration import cta_beat_indices
from mayzfact.steps.timeline import build_timeline
from mayzfact.store import RunPaths, write_json_atomic
from tests.test_cta_scene import timeline_fixture


def make_fixture(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    media = root/'earlier-local.mp4'
    if not media.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'testsrc2=size=360x640:rate=30:duration=4', '-an', '-c:v', 'libx264',
                        '-pix_fmt', 'yuv420p', str(media)], check=True)
    script, alignment, clips = timeline_fixture(24)
    script['cta_scene']['transform_word'] = 'turn'  # morph mulai di "turn", gunung utuh saat "volcano" terdengar
    allowed = set(cta_beat_indices(script['beats']))
    for s in clips['shots']:
        s.update(index=s['beat'], file=media.name, page_url='fixture-local-earlier', width=360, height=640,
                 hook_segment=None, source_s=0, text=script['beats'][s['beat']]['text'])
    earlier = [s for s in clips['shots'] if s['beat'] < min(allowed)]
    slots = [s for s in clips['shots'] if s['beat'] in allowed]
    auto = reuse_backgrounds(slots, earlier, RunPaths(root))
    clips['shots'] = sorted([s for s in clips['shots'] if s['beat'] not in allowed] + auto, key=lambda s: s['index'])
    timeline = build_timeline(clips, 24, .5, script=script, alignment=alignment)
    timeline['audio'] = ''  # fixture sengaja tanpa suara; tidak mengarang hasil TTS
    write_json_atomic(root/'timeline.json', timeline)
    write_json_atomic(root/'clips.json', clips)
    write_json_atomic(root/'fixture-script.json', script)
    scene = timeline['ctaScene']
    end = scene['from'] + scene['durationInFrames']
    render_start = max(0, scene['from']-15)
    render_end = min(timeline['durationInFrames']-1, end+24)
    stage = {s['kind']: s for s in scene['stages']}
    samples = [('before CTA', render_start+3), ('LIKE intro', stage['like']['from']+8),
               ('LIKE cue', next(c['from'] for c in scene['cues'] if c['kind']=='like')+3),
               ('morph', stage['transform']['from']+4), ('VOLCANO', stage['transform']['from']+14),
               ('SUBSCRIBE', stage['subscribe']['from']+5), ('ERUPTED', stage['comment']['from']+8),
               ('CTA tail', end-1), ('Number one', end+5)]
    info = dict(note='Synthetic alignment fixture only. No voice generation, production assets, BGM or SFX.',
                frames=[render_start, render_end], duration=(render_end-render_start+1)/30,
                samples=[dict(label=label, frame=f, seconds=(f-render_start)/30) for label, f in samples], scene=scene)
    write_json_atomic(root/'verification.json', info)
    return info


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(make_fixture(args.output), indent=2))
