import React from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {ANTON, FREDOKA} from './fonts';
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

// FaktaCuil: Fredoka 700, pop tanpa blur (scale 0.6 → 1.12 → 1 dalam 5 frame, opacity 0 → 1 dalam 2 frame).
const FC_MAX_WIDTH = 648; // 60% lebar frame: sisa kiri-kanan ±20% (Akmal)
const FC_MAX_SIZE = 120;
const FC_MIN_SIZE = 56;
const FC_CHAR_EM = 0.72; // perkiraan lebar rata-rata huruf kapital Fredoka 700 + stroke, dalam em

const fcFontSize = (text: string): number =>
  Math.max(FC_MIN_SIZE, Math.min(FC_MAX_SIZE, Math.floor(FC_MAX_WIDTH / (Math.max(1, text.length) * FC_CHAR_EM))));

const FaktaCuilWord: React.FC<{caption: Caption}> = ({caption}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 3, 5], [0.6, 1.12, 1], clamp);
  const opacity = interpolate(frame, [0, 2], [0, 1], clamp);
  return (
    <AbsoluteFill style={{alignItems: 'center'}}>
      <div
        style={{
          position: 'absolute',
          top: '75%',
          transform: `translateY(-50%) scale(${scale})`,
          opacity,
          fontFamily: FREDOKA,
          fontWeight: 700,
          fontSize: fcFontSize(caption.text),
          color: caption.color,
          WebkitTextStroke: '10px black',
          paintOrder: 'stroke fill',
          textShadow: ['10px 13px 0 rgba(0,0,0,0.95)', '0 0 18px rgba(0,0,0,0.8)'].join(', '),
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
export const Captions: React.FC<{captions: Caption[]; style?: 'faktacuil'}> = ({captions, style}) => (
  <>
    {captions.map((caption, index) => (
      <Sequence key={index} from={caption.from} durationInFrames={caption.durationInFrames} layout="none">
        {style === 'faktacuil' ? (
          <FaktaCuilWord caption={caption} />
        ) : (
          <Word caption={caption} id={`caption-blur-${index}`} />
        )}
      </Sequence>
    ))}
  </>
);
