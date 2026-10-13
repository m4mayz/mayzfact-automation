import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {Intro} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const BLUR_ID = 'intro-whip-blur';

// Pembuka = bagian "masuk" transisi antar scene di source i2xag (dicek frame per frame di 3.63-3.83 detik):
// frame 0-1 scene hampir putih + blur vertikal kuat + agak di-zoom, frame 2-3 cepat tajam,
// sampai frame 6 terangnya pudar ke normal. Caption nggak ikut kena efek (di source juga tetap tajam).
// Struktur elemen sengaja selalu sama: kalau berubah pas efek selesai, video di dalamnya ke-remount dan kedip hitam.
export const IntroWhip: React.FC<{intro: Intro | null; children: React.ReactNode}> = ({intro, children}) => {
  const frame = useCurrentFrame();
  const active = intro !== null && frame < intro.durationInFrames;
  const end = intro?.durationInFrames ?? 1;
  const blurY = active ? interpolate(frame, [0, 1, 3], [60, 35, 0], clamp) : 0;
  const scale = active ? interpolate(frame, [0, 3], [1.18, 1], clamp) : 1;
  const brightness = active ? interpolate(frame, [0, 1, 2, end - 2, end], [2.6, 2.0, 1.5, 1.3, 1], clamp) : 1;
  const white = active ? interpolate(frame, [0, 1, 3], [0.55, 0.35, 0], clamp) : 0;
  const filters = [blurY > 0.1 ? `url(#${BLUR_ID})` : '', brightness !== 1 ? `brightness(${brightness})` : '']
    .filter(Boolean)
    .join(' ');
  return (
    <AbsoluteFill>
      <svg width="0" height="0" style={{position: 'absolute'}}>
        <filter id={BLUR_ID} x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation={`2 ${blurY}`} />
        </filter>
      </svg>
      <AbsoluteFill style={{transform: scale !== 1 ? `scale(${scale})` : undefined, filter: filters || undefined}}>
        {children}
      </AbsoluteFill>
      <AbsoluteFill style={{backgroundColor: 'white', opacity: white, pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
