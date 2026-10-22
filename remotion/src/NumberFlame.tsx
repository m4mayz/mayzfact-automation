import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const FRAMES = 14;

// Ledakan api biru di belakang angka countdown, niru source i2xag (#3 platypus 37.65-38.05 dtk):
// frame 0 api rapet di sekitar angka, frame 1-5 cincin api ngembang keluar, frame 6-13 makin tipis terus hilang.
// Api dibikin dari lingkaran gradasi biru yang dirusak noise (feTurbulence + feDisplacementMap), seed ganti tiap frame
// biar lidah apinya gerak.
const Layer: React.FC<{id: string; frame: number; radius: number; displace: number; freq: string; seed: number; rotate: number}> = ({
  id,
  frame,
  radius,
  displace,
  freq,
  seed,
  rotate,
}) => (
  <g transform={`rotate(${rotate})`}>
    <defs>
      <radialGradient id={`${id}-grad`}>
        <stop offset="0%" stopColor="#06154a" stopOpacity={frame < 2 ? 0.8 : 0} />
        <stop offset="38%" stopColor="#0d47c9" stopOpacity={frame < 2 ? 0.9 : 0.25} />
        <stop offset="58%" stopColor="#2f8dff" stopOpacity={0.95} />
        <stop offset="72%" stopColor="#c6ecff" stopOpacity={1} />
        <stop offset="84%" stopColor="#2b7bff" stopOpacity={0.85} />
        <stop offset="100%" stopColor="#0a2f9c" stopOpacity={0} />
      </radialGradient>
      <filter id={`${id}-fire`} x="-60%" y="-60%" width="220%" height="220%">
        <feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={4} seed={seed} result="noise" />
        <feDisplacementMap in="SourceGraphic" in2="noise" scale={displace} xChannelSelector="R" yChannelSelector="G" result="fire" />
        <feGaussianBlur in="fire" stdDeviation={12} result="glow" />
        <feMerge>
          <feMergeNode in="glow" />
          <feMergeNode in="fire" />
        </feMerge>
      </filter>
    </defs>
    <circle r={radius} fill={`url(#${id}-grad)`} filter={`url(#${id}-fire)`} />
  </g>
);

export const NumberFlame: React.FC<{id: string}> = ({id}) => {
  const frame = useCurrentFrame();
  if (frame >= FRAMES) {
    return null;
  }
  const radius = interpolate(frame, [0, 2, 6, FRAMES], [300, 520, 640, 720], {...clamp, easing: Easing.out(Easing.quad)});
  const opacity = interpolate(frame, [0, 6, FRAMES - 1], [1, 0.9, 0], clamp);
  const displace = interpolate(frame, [0, FRAMES], [180, 300], clamp);
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', pointerEvents: 'none'}}>
      <svg width={1800} height={1800} viewBox="-900 -900 1800 1800" style={{overflow: 'visible', opacity}}>
        {/* 2 lapis api dengan noise beda biar lidah apinya acak, nggak bulet rata */}
        <Layer id={`${id}-a`} frame={frame} radius={radius} displace={displace} freq="0.007 0.014" seed={frame * 2 + 1} rotate={0} />
        <Layer id={`${id}-b`} frame={frame} radius={radius * 0.82} displace={displace * 0.7} freq="0.016 0.03" seed={frame * 2 + 2} rotate={37} />
      </svg>
    </AbsoluteFill>
  );
};
