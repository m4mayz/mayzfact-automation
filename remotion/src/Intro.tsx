import React from 'react';
import {AbsoluteFill, Easing, Freeze, interpolate, useCurrentFrame} from 'remotion';
import type {Intro} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const BLUR_ID = 'intro-motion-blur';

// Pembuka ngikutin source i2xag (dicek frame per frame):
// frame 0-1 "cover" = still dari momen caption berwarna pertama (gambar + caption), lebih terang, biar jadi thumbnail Shorts.
export const IntroCover: React.FC<{intro: Intro | null; children: React.ReactNode}> = ({intro, children}) => {
  const frame = useCurrentFrame();
  if (intro && frame < intro.coverFrames) {
    return (
      <AbsoluteFill style={{filter: 'brightness(1.35) saturate(0.75) contrast(0.95)'}}>
        <Freeze frame={intro.coverFrame}>{children}</Freeze>
      </AbsoluteFill>
    );
  }
  return <>{children}</>;
};

// frame 2-6: video mulai zoom-in ±1.3x (pusat kanan bawah, jadi objek kegeser ke kiri atas) + blur gerak menyamping,
// terus zoom out ke normal.
// Caption nggak ikut di-zoom.
export const IntroZoom: React.FC<{intro: Intro | null; children: React.ReactNode}> = ({intro, children}) => {
  const frame = useCurrentFrame();
  if (!intro || frame < intro.coverFrames || frame >= intro.durationInFrames) {
    return <AbsoluteFill>{children}</AbsoluteFill>;
  }
  const range = [intro.coverFrames, intro.durationInFrames];
  const scale = interpolate(frame, range, [1.3, 1], {...clamp, easing: Easing.out(Easing.quad)});
  const blur = interpolate(frame, range, [1, 0], clamp);
  return (
    <AbsoluteFill>
      <svg width="0" height="0" style={{position: 'absolute'}}>
        <filter id={BLUR_ID} x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation={`${12 * blur} ${4 * blur}`} />
        </filter>
      </svg>
      <AbsoluteFill style={{transform: `scale(${scale})`, transformOrigin: '70% 78%', filter: `url(#${BLUR_ID})`}}>
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
