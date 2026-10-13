import React from 'react';
import {AbsoluteFill, random, useCurrentFrame, useVideoConfig} from 'remotion';

const COUNT = 40;

// Background card countdown: hitam kebiruan + partikel kecil yang naik pelan. Posisi dari seed, jadi tiap render sama.
export const Particles: React.FC<{seed: string}> = ({seed}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 45%, #13233f 0%, #070b16 55%, #020308 100%)'}}>
      {Array.from({length: COUNT}, (_, i) => {
        const x = random(`${seed}-x-${i}`) * width;
        const speed = 0.6 + random(`${seed}-s-${i}`) * 1.8;
        const y = (random(`${seed}-y-${i}`) * height - frame * speed + height) % height;
        const size = 2 + random(`${seed}-r-${i}`) * 5;
        const opacity = 0.25 + random(`${seed}-o-${i}`) * 0.6;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: size,
              height: size,
              borderRadius: '50%',
              background: '#9fd8ff',
              opacity,
              boxShadow: `0 0 ${size * 2}px #6cc4ff`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
