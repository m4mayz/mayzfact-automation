import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {ANTON} from './fonts';
import {Particles} from './Particles';

// Angka countdown chrome di background gelap berpartikel (gaya source i2xag).
export const NumberCard: React.FC<{number: number; durationInFrames: number}> = ({number, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 12, stiffness: 160}, durationInFrames: 8});
  const scale = interpolate(pop, [0, 1], [1.4, 1]) * interpolate(frame, [0, Math.max(1, durationInFrames)], [1, 1.05]);
  const opacity = interpolate(frame, [0, 4], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill>
      <Particles seed={`number-${number}`} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div
          style={{
            fontFamily: ANTON,
            fontSize: 900,
            lineHeight: 1,
            transform: `scale(${scale})`,
            opacity,
            background: 'linear-gradient(180deg, #ffffff 0%, #c9d2dc 38%, #ffffff 52%, #6b7480 78%, #dfe6ee 100%)',
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            color: 'transparent',
            WebkitTextStroke: '4px rgba(255,255,255,0.55)',
            filter: 'drop-shadow(0 18px 30px rgba(0,0,0,0.75)) drop-shadow(0 0 22px rgba(140,200,255,0.35))',
          }}
        >
          {number}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
