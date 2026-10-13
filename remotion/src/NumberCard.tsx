import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {ANTON} from './fonts';
import {Particles} from './Particles';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const FLY_FRAMES = 4; // whoosh-clean: puncak ±0.1 detik, ekornya habis ±0.4 detik

// Angka countdown chrome di background gelap berpartikel (gaya source i2xag).
// Background udah tampil dari awal beat; angkanya baru melesat masuk pas narasi "Number" kedengeran (numberAt),
// barengan puncak whoosh: zoom dari jauh lebih gede + blur, langsung tajam, terus zoom pelan.
export const NumberCard: React.FC<{number: number; numberAt: number; durationInFrames: number}> = ({
  number,
  numberAt,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const local = frame - numberAt;
  const fly = interpolate(local, [0, FLY_FRAMES], [2.6, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  const drift = interpolate(local, [FLY_FRAMES, Math.max(FLY_FRAMES + 1, durationInFrames - numberAt)], [1, 1.05], clamp);
  const blur = interpolate(local, [0, FLY_FRAMES], [14, 0], clamp);
  const opacity = local < 0 ? 0 : interpolate(local, [0, 1], [0.6, 1], clamp);
  return (
    <AbsoluteFill>
      <Particles seed={`number-${number}`} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div
          style={{
            fontFamily: ANTON,
            fontSize: 900,
            lineHeight: 1,
            transform: `scale(${fly * drift})`,
            opacity,
            background: 'linear-gradient(180deg, #ffffff 0%, #c9d2dc 38%, #ffffff 52%, #6b7480 78%, #dfe6ee 100%)',
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            color: 'transparent',
            WebkitTextStroke: '4px rgba(255,255,255,0.55)',
            filter: `blur(${blur}px) drop-shadow(0 18px 30px rgba(0,0,0,0.75)) drop-shadow(0 0 22px rgba(140,200,255,0.35))`,
          }}
        >
          {number}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
