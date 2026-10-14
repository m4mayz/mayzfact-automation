import React from 'react';
import {Easing, interpolate, Sequence, useCurrentFrame} from 'remotion';
import type {Overlay, OverlayKeyframe} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ARROW_LENGTH = 230;
const BIG_W = 950;
const BIG_H = 1100;
const EDGE = 40;
const FRAME_W = 1080;
const FRAME_H = 1920;

// Posisi subjek di frame ini: interpolasi linear antar titik deteksi (tiap 1 detik).
const boxAt = (keyframes: OverlayKeyframe[], frame: number): OverlayKeyframe => {
  if (keyframes.length === 1 || frame <= keyframes[0].frame) {
    return keyframes[0];
  }
  const last = keyframes[keyframes.length - 1];
  if (frame >= last.frame) {
    return last;
  }
  const next = keyframes.findIndex((k) => k.frame > frame);
  const a = keyframes[next - 1];
  const b = keyframes[next];
  const mix = (key: 'x' | 'y' | 'w' | 'h') => interpolate(frame, [a.frame, b.frame], [a[key], b[key]]);
  return {frame, x: mix('x'), y: mix('y'), w: mix('w'), h: mix('h')};
};

// Panah tebal (ujung di titik 0,0, ngarah ke bawah), isi warna + outline hitam, kayak source i2xag.
const ARROW_PATH = 'M0 0 L-62 -100 L-24 -100 L-24 -230 L24 -230 L24 -100 L62 -100 Z';

const POP_FRAMES = 4;
const FADE_FRAMES = 8;
const ORBIT_FROM = 20; // derajat; 0 = kanan subjek, -90 = atas, -180 = kiri
const ORBIT_TO = -160; // 1 sapuan setengah putaran lewat atas (kanan → kiri), direntangin sepanjang durasi tampil

// Muncul seketika (bareng quick-ting), fade di akhir.
const appear = (frame: number, duration: number) => ({
  scale: interpolate(frame, [0, 2, POP_FRAMES], [0.3, 1.15, 1], clamp),
  opacity: interpolate(frame, [duration - FADE_FRAMES, duration], [1, 0], clamp),
});

// Panah nyapu setengah putaran di sekitar subjek (sekali, sepanjang durasi tampil), ujungnya selalu nunjuk ke subjek.
const Arrow: React.FC<{overlay: Overlay}> = ({overlay}) => {
  const frame = useCurrentFrame();
  const box = boxAt(overlay.keyframes, frame);
  const big = box.w > BIG_W || box.h > BIG_H;
  const cx = box.x + box.w / 2;
  const cy = big ? box.y + box.h * 0.35 : box.y + box.h / 2;
  const rx = Math.min(box.w / 2 + 20, 360);
  const ry = Math.min(box.h / 2 + 20, 520);
  const theta = (interpolate(frame, [0, overlay.durationInFrames], [ORBIT_FROM, ORBIT_TO], {
    ...clamp,
    easing: Easing.inOut(Easing.quad),
  }) * Math.PI) / 180;
  const ux = Math.cos(theta);
  const uy = Math.sin(theta);
  // Batasi ujung panah biar badannya (ke arah luar) tetap di dalam layar.
  const tailX = ARROW_LENGTH * ux;
  const tailY = ARROW_LENGTH * uy;
  const tipX = Math.min(Math.max(cx + rx * ux, EDGE - Math.min(0, tailX)), FRAME_W - EDGE - Math.max(0, tailX));
  const tipY = Math.min(Math.max(cy + ry * uy, EDGE - Math.min(0, tailY)), FRAME_H - EDGE - Math.max(0, tailY));
  const angle = (Math.atan2(ux, -uy) * 180) / Math.PI; // panah default ngarah ke bawah; diputer biar ngarah ke dalam
  const {scale, opacity} = appear(frame, overlay.durationInFrames);
  return (
    <svg
      width={ARROW_LENGTH * 2}
      height={ARROW_LENGTH * 2}
      viewBox={`${-ARROW_LENGTH} ${-ARROW_LENGTH} ${ARROW_LENGTH * 2} ${ARROW_LENGTH * 2}`}
      style={{
        position: 'absolute',
        left: tipX - ARROW_LENGTH,
        top: tipY - ARROW_LENGTH,
        overflow: 'visible',
        opacity,
        transform: `rotate(${angle}deg) scale(${scale})`,
        transformOrigin: '50% 50%',
        filter: 'drop-shadow(0 6px 10px rgba(0,0,0,0.55))',
      }}
    >
      <path d={ARROW_PATH} fill={overlay.color} stroke="black" strokeWidth={9} strokeLinejoin="round" />
    </svg>
  );
};

const DRAW_FRAMES = 6;

// Lingkaran digambar cepat ngelilingin subjek, terus fade.
const Circle: React.FC<{overlay: Overlay}> = ({overlay}) => {
  const frame = useCurrentFrame();
  const box = boxAt(overlay.keyframes, frame);
  const rx = box.w * 0.55;
  const ry = box.h * 0.55;
  // Keliling elips (Ramanujan), buat animasi "digambar" pakai stroke-dashoffset.
  const perimeter = Math.PI * (3 * (rx + ry) - Math.sqrt((3 * rx + ry) * (rx + 3 * ry)));
  const drawn = interpolate(frame, [0, DRAW_FRAMES], [0, 1], clamp);
  const {opacity} = appear(frame, overlay.durationInFrames);
  const ring: React.SVGProps<SVGEllipseElement> = {
    cx: box.x + box.w / 2,
    cy: box.y + box.h / 2,
    rx,
    ry,
    fill: 'none',
    strokeDasharray: perimeter,
    strokeDashoffset: perimeter * (1 - drawn),
    strokeLinecap: 'round',
  };
  return (
    <svg width="1080" height="1920" style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity}}>
      <ellipse {...ring} stroke="black" strokeWidth={24} />
      <ellipse {...ring} stroke={overlay.color} strokeWidth={14} />
    </svg>
  );
};

// Panah / lingkaran yang ngikutin subjek, 1 Sequence per shot.
export const Overlays: React.FC<{overlays: Overlay[]}> = ({overlays}) => (
  <>
    {overlays.map((overlay, index) => (
      <Sequence key={index} from={overlay.from} durationInFrames={overlay.durationInFrames}>
        {overlay.type === 'circle' ? <Circle overlay={overlay} /> : <Arrow overlay={overlay} />}
      </Sequence>
    ))}
  </>
);
