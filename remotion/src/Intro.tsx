import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import type {Intro} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Pembuka video: gambar "nembus" (zoom 1.6 → 1) di balik white flash yang cepat pudar. Barengan SFX hook.
export const IntroZoom: React.FC<{intro: Intro | null; children: React.ReactNode}> = ({intro, children}) => {
  const frame = useCurrentFrame();
  const scale = intro
    ? interpolate(frame, [0, intro.durationInFrames], [1.6, 1], {...clamp, easing: Easing.out(Easing.cubic)})
    : 1;
  return <AbsoluteFill style={{transform: `scale(${scale})`}}>{children}</AbsoluteFill>;
};

export const IntroFlash: React.FC<{intro: Intro | null}> = ({intro}) => {
  const frame = useCurrentFrame();
  if (!intro || frame >= intro.durationInFrames) {
    return null;
  }
  const opacity = interpolate(frame, [0, 2, intro.durationInFrames], [1, 0.95, 0], clamp);
  return <AbsoluteFill style={{backgroundColor: 'white', opacity}} />;
};
