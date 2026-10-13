import React from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {ANTON} from './fonts';
import type {Caption} from './types';

// Animasi masuk ngikutin source i2xag (dicek frame per frame di 30 fps):
// frame 1-2 motion blur horizontal kuat + agak kecil + agak pudar, frame 3 hampir tajam, frame 4 tajam. Keluar langsung ganti.
const ENTER_FRAMES = 3;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const Word: React.FC<{caption: Caption; id: string}> = ({caption, id}) => {
  const frame = useCurrentFrame();
  const blurX = interpolate(frame, [0, ENTER_FRAMES], [16, 0], clamp);
  const scale = interpolate(frame, [0, ENTER_FRAMES], [0.88, 1], clamp);
  const opacity = interpolate(frame, [0, ENTER_FRAMES], [0.65, 1], clamp);
  return (
    <AbsoluteFill style={{alignItems: 'center'}}>
      <svg width="0" height="0" style={{position: 'absolute'}}>
        <filter id={id} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation={`${blurX} 0`} />
        </filter>
      </svg>
      <div
        style={{
          position: 'absolute',
          top: '75%',
          transform: `translateY(-50%) scale(${scale})`,
          opacity,
          filter: blurX > 0.05 ? `url(#${id})` : undefined,
          fontFamily: ANTON,
          fontSize: 120,
          color: caption.color,
          WebkitTextStroke: '12px black',
          paintOrder: 'stroke fill',
          // Shadow tebal: bayangan padat jatuh ke kanan bawah + bayangan lembut gelap di sekeliling.
          textShadow: [
            '7px 9px 0 rgba(0,0,0,0.95)',
            '10px 14px 10px rgba(0,0,0,0.85)',
            '0 0 22px rgba(0,0,0,0.9)',
            '0 0 40px rgba(0,0,0,0.6)',
          ].join(', '),
          letterSpacing: 1,
          whiteSpace: 'nowrap',
        }}
      >
        {caption.text}
      </div>
    </AbsoluteFill>
  );
};

// Caption 1 kata per tampilan, timing-nya dari timeline.json.
export const Captions: React.FC<{captions: Caption[]}> = ({captions}) => (
  <>
    {captions.map((caption, index) => (
      <Sequence key={index} from={caption.from} durationInFrames={caption.durationInFrames} layout="none">
        <Word caption={caption} id={`caption-blur-${index}`} />
      </Sequence>
    ))}
  </>
);
