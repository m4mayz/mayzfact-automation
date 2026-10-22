import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {Intro, Transition} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const BLUR_ID = 'intro-whip-blur';

// Pembuka = bagian "masuk" transisi antar scene di source i2xag (dicek frame per frame di 3.63-3.83 detik):
// frame 0-1 scene hampir putih + blur vertikal kuat + agak di-zoom, frame 2-3 cepat tajam,
// sampai frame 6 terangnya pudar ke normal. Caption nggak ikut kena efek (di source juga tetap tajam).
// Efek yang sama dipakai lagi di transisi magic reveal tiap item (D-038): transitions = frame mulai + durasi.
// Ganti klip di hook (cuts) niru source i2xag 3.63-3.77 & 6.03-6.13 dtk: 1 frame sebelum cut klip lama ke-blur
// horizontal + agak gelap, frame cut klip baru hampir putih + blur vertikal kuat, frame berikutnya blur tipis, lalu tajam.
// Struktur elemen sengaja selalu sama: kalau berubah pas efek selesai, video di dalamnya ke-remount dan kedip hitam.
export const IntroWhip: React.FC<{
  intro: Intro | null;
  transitions?: Transition[];
  cuts?: Transition[];
  children: React.ReactNode;
}> = ({intro, transitions = [], cuts = [], children}) => {
  const now = useCurrentFrame();
  const starts = [...(intro ? [{from: 0, durationInFrames: intro.durationInFrames}] : []), ...transitions];
  const current = starts.find((t) => now >= t.from && now < t.from + t.durationInFrames) ?? null;
  const frame = current ? now - current.from : now;
  const active = current !== null;
  const end = current?.durationInFrames ?? 1;
  let blurY = active ? interpolate(frame, [0, 1, 3], [60, 35, 0], clamp) : 0;
  let blurX = 0;
  let scale = active ? interpolate(frame, [0, 3], [1.18, 1], clamp) : 1;
  let brightness = active ? interpolate(frame, [0, 1, 2, end - 2, end], [2.6, 2.0, 1.5, 1.3, 1], clamp) : 1;
  let white = active ? interpolate(frame, [0, 1, 3], [0.55, 0.35, 0], clamp) : 0;
  if (!active) {
    const outgoing = cuts.some((c) => now === c.from - 1);
    const incoming = cuts.find((c) => now >= c.from && now < c.from + 2);
    if (outgoing) {
      blurX = 45;
      brightness = 0.75;
    } else if (incoming) {
      const k = now - incoming.from;
      blurY = k === 0 ? 50 : 22;
      white = k === 0 ? 0.75 : 0.3;
      brightness = k === 0 ? 1.8 : 1.3;
      scale = k === 0 ? 1.08 : 1.03;
    }
  }
  const blurred = blurY > 0.1 || blurX > 0.1;
  const filters = [blurred ? `url(#${BLUR_ID})` : '', brightness !== 1 ? `brightness(${brightness})` : '']
    .filter(Boolean)
    .join(' ');
  return (
    <AbsoluteFill>
      <svg width="0" height="0" style={{position: 'absolute'}}>
        <filter id={BLUR_ID} x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation={`${2 + blurX} ${blurY}`} />
        </filter>
      </svg>
      <AbsoluteFill style={{transform: scale !== 1 ? `scale(${scale})` : undefined, filter: filters || undefined}}>
        {children}
      </AbsoluteFill>
      <AbsoluteFill style={{backgroundColor: 'white', opacity: white, pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
