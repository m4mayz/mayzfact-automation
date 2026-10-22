import React from 'react';
import {AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {ANTON} from './fonts';
import {BURST_FRAMES, FireBurst} from './FireBurst';
import {Particles} from './Particles';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const POP_FRAMES = 2;

// Angka countdown chrome di background gelap berpartikel (gaya source i2xag).
// Masuknya kayak source: angka langsung nongol (sedikit mengecil ke ukuran penuh, 2 frame) dengan ledakan api biru
// numpuk di atasnya (FireBurst, VFX ledakan api biru), barengan SFX fire whoosh. Abis itu zoom pelan.
export const NumberCard: React.FC<{number: number; numberAt: number; durationInFrames: number}> = ({
  number,
  numberAt,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const local = frame - numberAt;
  const pop = interpolate(local, [0, POP_FRAMES], [0.88, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  const drift = interpolate(local, [POP_FRAMES, Math.max(POP_FRAMES + 1, durationInFrames - numberAt)], [1, 1.05], clamp);
  const glow = interpolate(local, [0, 6], [1, 0.35], clamp); // angka nyala biru pas api meledak
  const opacity = local < 0 ? 0 : 1;
  return (
    <AbsoluteFill>
      <Particles seed={`number-${number}`} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div
          style={{
            fontFamily: ANTON,
            fontSize: 900,
            lineHeight: 1,
            transform: `scale(${pop * drift})`,
            opacity,
            background: 'linear-gradient(180deg, #ffffff 0%, #c9d2dc 38%, #ffffff 52%, #6b7480 78%, #dfe6ee 100%)',
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            color: 'transparent',
            WebkitTextStroke: '4px rgba(255,255,255,0.55)',
            filter: `drop-shadow(0 18px 30px rgba(0,0,0,0.75)) drop-shadow(0 0 ${22 + 30 * glow}px rgba(120,190,255,${glow}))`,
          }}
        >
          {number}
        </div>
      </AbsoluteFill>
      {local >= 0 ? (
        <Sequence from={numberAt} durationInFrames={BURST_FRAMES} layout="none">
          <FireBurst />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
