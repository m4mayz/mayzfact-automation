import React from 'react';
import {interpolate, Sequence, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Overlay, OverlayKeyframe} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ARROW_LENGTH = 230;
const SIDE_TOP_LIMIT = 260; // subjek mepet atas layar: panah datang dari kanan

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

const Arrow: React.FC<{overlay: Overlay}> = ({overlay}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const box = boxAt(overlay.keyframes, frame);
  const side = box.y < SIDE_TOP_LIMIT;
  const tipX = side ? box.x + box.w * 0.92 : box.x + box.w / 2;
  const tipY = side ? box.y + box.h / 2 : box.y + box.h * 0.08;
  // Dari serong kanan atas pelan-pelan jadi tegak (source: arah panah berubah sepanjang shot).
  const angle = side ? 90 : interpolate(frame, [0, overlay.durationInFrames], [35, 0], clamp);
  const pop = spring({frame, fps, config: {damping: 11, stiffness: 180}, durationInFrames: 6});
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
        transform: `rotate(${angle}deg) scale(${pop})`,
        transformOrigin: '50% 50%',
        filter: 'drop-shadow(0 6px 10px rgba(0,0,0,0.55))',
      }}
    >
      <path d={ARROW_PATH} fill={overlay.color} stroke="black" strokeWidth={9} strokeLinejoin="round" />
    </svg>
  );
};

const DRAW_FRAMES = 8;

const Circle: React.FC<{overlay: Overlay}> = ({overlay}) => {
  const frame = useCurrentFrame();
  const box = boxAt(overlay.keyframes, frame);
  const rx = box.w * 0.55;
  const ry = box.h * 0.55;
  // Keliling elips (Ramanujan), buat animasi "digambar" pakai stroke-dashoffset.
  const perimeter = Math.PI * (3 * (rx + ry) - Math.sqrt((3 * rx + ry) * (rx + 3 * ry)));
  const drawn = interpolate(frame, [0, DRAW_FRAMES], [0, 1], clamp);
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
    <svg width="1080" height="1920" style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
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
