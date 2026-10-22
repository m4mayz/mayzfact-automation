import React from 'react';
import {Video} from '@remotion/media';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import fire from './assets/fire-burst.mp4';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Ledakan api biru pas angka countdown (di atas angka) dan box foto subjek (di belakang box) masuk, niru source
// i2xag (#3 platypus 37.65-38.05 dtk): api rapet di tengah, ngembang jadi cincin dengan tengah gelap, terus pudar.
// Sumbernya "Blue Fire Powers Pack" blackscreen (youtube.com/watch?v=Q46O_LHNDns, detik 64,7-65,45, kecepatan
// normal), diputer 90° jadi portrait biar menuhin layar tanpa di-crop. Blend `screen` bikin hitamnya ilang.
export const BURST_FRAMES = 23;
const FADE_FROM = 9;

export const FireBurst: React.FC = () => {
  const frame = useCurrentFrame();
  // ujung klipnya jadi putih menuhin layar: dipudarin pelan dari frame 9. Opacity ditaruh di Video-nya sendiri,
  // kalau di wrapper jadi grup terisolasi dan blend `screen`-nya nggak kena background (hitamnya keliatan).
  const opacity = interpolate(frame, [0, 1, FADE_FROM, BURST_FRAMES], [0.6, 1, 1, 0], clamp);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <Video src={fire} muted objectFit="contain" style={{width: '100%', height: '100%', opacity, mixBlendMode: 'screen'}} />
    </AbsoluteFill>
  );
};
