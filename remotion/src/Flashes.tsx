import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import type {Transition} from './types';

// Flash putih di pergantian klip hook, barengan SFX camera flash: langsung putih, terus pudar.
// Caption, panah, dan emoji ada di atas layer ini, jadi tetap kebaca.
export const Flashes: React.FC<{flashes: Transition[]}> = ({flashes}) => {
  const frame = useCurrentFrame();
  const current = flashes.find((f) => frame >= f.from && frame < f.from + f.durationInFrames);
  const opacity = current
    ? interpolate(frame - current.from, [0, current.durationInFrames], [0.95, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
        easing: Easing.out(Easing.quad),
      })
    : 0;
  return <AbsoluteFill style={{backgroundColor: 'white', opacity, pointerEvents: 'none'}} />;
};
