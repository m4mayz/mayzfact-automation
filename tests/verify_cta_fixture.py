"""Cek ffprobe + frame nyata dan buat contact sheet berlabel untuk fixture CTA."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def verify_fixture(root: Path) -> dict:
    info = json.loads((root/'verification.json').read_text())
    video = root/'cta.mp4'
    probe = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
        'stream=codec_name,width,height,r_frame_rate:format=duration,size', '-of', 'json', str(video)],
        check=True, capture_output=True, text=True).stdout)
    stream = probe['streams'][0]
    assert (stream['codec_name'], stream['width'], stream['height'], stream['r_frame_rate']) == ('h264', 1080, 1920, '30/1')
    assert abs(float(probe['format']['duration']) - info['duration']) < .08
    thumbs = []
    for i, sample in enumerate(info['samples']):
        dest = root/f'stage-{i:02d}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(sample['seconds']), '-i', str(video),
                        '-frames:v', '1', str(dest)], check=True)
        im = Image.open(dest).convert('RGB')
        assert np.asarray(im).mean() > 4, sample['label']
        if sample['label'] == 'LIKE intro':
            pixels = np.asarray(im)[450:1100, 270:810].astype(float)
            blue = (pixels[:, :, 2] > pixels[:, :, 0]*1.4) & (pixels[:, :, 2] > pixels[:, :, 1]*1.15)
            assert blue.mean() > .3, 'tombol LIKE besar belum tampil'
        thumbs.append((sample, im.resize((270, 480))))
    sheet = Image.new('RGB', (270*len(thumbs), 530), '#101522')
    draw = ImageDraw.Draw(sheet)
    for i, (sample, im) in enumerate(thumbs):
        sheet.paste(im, (270*i, 50))
        draw.text((270*i+8, 8), sample['label'], fill='white')
        draw.text((270*i+8, 25), f"f{sample['frame']} | clip {sample['seconds']:.3f}s", fill='#99caff')
    sheet.save(root/'contact-sheet.png')
    # Cek background pada dua frame dalam scene: bukan black tail dan tidak membeku.
    crops = []
    for f in [info['scene']['from']+3, info['scene']['from']+20]:
        time = (f-info['frames'][0])/30
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(time), '-i', str(video),
                              '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'],
                             check=True, capture_output=True).stdout
        img = np.frombuffer(raw, dtype=np.uint8).reshape(1920, 1080, 3)
        crops.append(img[100:350, 50:1030].astype(float))
    motion = float(np.abs(crops[0]-crops[1]).mean())
    assert motion > .05, f'background frozen? delta={motion}'
    assert min(float(x.mean()) for x in crops) > 3
    result = dict(probe=probe, background_motion_mean_absolute_delta=motion,
                  inspected_frames=len(thumbs), contact_sheet=str(root/'contact-sheet.png'))
    (root/'render-verification.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    import sys
    print(json.dumps(verify_fixture(Path(sys.argv[1])), indent=2))
