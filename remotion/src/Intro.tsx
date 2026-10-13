import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import type {Intro} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const BLUR_ID = 'intro-whip-blur';

// Pembuka = bagian "masuk" transisi antar scene di source i2xag (dicek frame per frame di 3.63-3.83 detik):
// frame 0-1 scene hampir putih + blur vertikal kuat + agak di-zoom, frame 2-3 cepat tajam,
// sampai frame 6 terangnya pudar ke normal. Caption nggak ikut kena efek (di source juga tetap tajam).
export const IntroWhip: React.FC<{intro: Intro | null; children: React.ReactNode}> = ({intro, children}) => {
  const frame = useCurrentFrame();
  if (!intro || frame >= intro.durationInFrames) {
    return <AbsoluteFill>{children}</AbsoluteFill>;
  }
  const end = intro.durationInFrames;
  const blurY = interpolate(frame, [0, 1, 3], [60, 35, 0], clamp);
  const scale = interpolate(frame, [0, 3], [1.18, 1], clamp);
  const brightness = interpolate(frame, [0, 1, 2, end - 2, end], [2.6, 2.0, 1.5, 1.3, 1], clamp);
  const white = interpolate(frame, [0, 1, 3], [0.55, 0.35, 0], clamp);
  return (
    <AbsoluteFill>
      <svg width="0" height="0" style={{position: 'absolute'}}>
        <filter id={BLUR_ID} x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation={`2 ${blurY}`} />
        </filter>
      </svg>
      <AbsoluteFill
        style={{
          transform: `scale(${scale})`,
          filter: `${blurY > 0.1 ? `url(#${BLUR_ID}) ` : ''}brightness(${brightness})`,
        }}
      >
        {children}
      </AbsoluteFill>
      <AbsoluteFill style={{backgroundColor: 'white', opacity: white}} />
    </AbsoluteFill>
  );
};
