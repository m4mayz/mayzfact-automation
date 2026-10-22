import React from 'react';
import {Video} from '@remotion/media';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import fire from './assets/number-fire.mp4';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Ledakan api biru di atas angka countdown, niru source i2xag (#3 platypus 37.65-38.05 dtk): api rapet di sekitar
// angka, ngembang jadi cincin dengan tengah gelap, terus pudar. Sumbernya "Blue Fire Powers Pack" blackscreen
// (youtube.com/watch?v=Q46O_LHNDns, detik 64,7-65,45, dipercepat 1,5x), diputer 90° jadi portrait biar menuhin
// layar tanpa di-crop. Blend `screen` bikin hitamnya ilang.
export const BURST_FRAMES = 16;

export const NumberFlame: React.FC = () => {
  const frame = useCurrentFrame();
  // ujung klipnya jadi putih menuhin layar: dipudarin sebelum nutup angka. Opacity ditaruh di Video-nya sendiri,
  // kalau di wrapper jadi grup terisolasi dan blend `screen`-nya nggak kena background (hitamnya keliatan).
  const opacity = interpolate(frame, [0, 1, 9, BURST_FRAMES], [0.6, 1, 1, 0], clamp);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <Video src={fire} muted objectFit="contain" style={{width: '100%', height: '100%', opacity, mixBlendMode: 'screen'}} />
    </AbsoluteFill>
  );
};
