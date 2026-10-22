import React from 'react';
import {Video} from '@remotion/media';
import {AbsoluteFill, Easing, Img, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {BURST_FRAMES, FireBurst} from './FireBurst';
import {ANTON} from './fonts';
import {Particles} from './Particles';
import {TextBlurs} from './TextBlurs';
import type {CountdownCard} from './types';

const BOX = 820;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const BLUR_ID = 'subject-exit-blur';
// Dicek frame per frame di source i2xag (#5 horseshoe crab 17.50 & 18.20 dtk, #3 platypus 38.33 & 38.73 dtk):
// masuk 3 frame dari ±2,4x mengecil ke ukuran normal sambil blur; keluar 4 frame makin terang + blur vertikal
// + sedikit membesar (frame terakhir agak menyempit), terus cut biasa ke klip berikutnya.
const ENTER_FRAMES = 3;
const EXIT_FRAMES = 4;

// Klip subjek di dalam frame menyala + label nama (gaya STURGEON di source i2xag). Api biru meledak di belakang box
// pas masuk, sama kayak kartu angka.
export const SubjectCard: React.FC<{card: CountdownCard}> = ({card}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const glow = 0.65 + 0.35 * Math.sin((frame / fps) * Math.PI * 2.2);
  const enter = interpolate(frame, [0, ENTER_FRAMES - 1], [2.4, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  const enterBlur = interpolate(frame, [0, ENTER_FRAMES - 1], [16, 0], clamp);
  const e = frame - Math.max(ENTER_FRAMES, card.cardDuration - EXIT_FRAMES); // 0..3 di 4 frame terakhir
  const exiting = e >= 0;
  const exitScale = exiting ? interpolate(e, [0, EXIT_FRAMES - 1], [1.04, 1.14], clamp) : 1;
  const squeezeX = exiting ? interpolate(e, [EXIT_FRAMES - 2, EXIT_FRAMES - 1], [1, 0.85], clamp) : 1;
  const brightness = exiting ? interpolate(e, [0, EXIT_FRAMES - 2, EXIT_FRAMES - 1], [2.2, 3.4, 2.4], clamp) : 1;
  const blurY = exiting ? interpolate(e, [0, EXIT_FRAMES - 1], [14, 40], clamp) : 0;
  const boxFilter = [
    enterBlur > 0.1 ? `blur(${enterBlur}px)` : '',
    blurY > 0.1 ? `url(#${BLUR_ID})` : '',
    brightness !== 1 ? `brightness(${brightness})` : '',
  ]
    .filter(Boolean)
    .join(' ');
  const src = staticFile(card.src);
  const media: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover'};
  return (
    <AbsoluteFill>
      <svg width="0" height="0" style={{position: 'absolute'}}>
        <filter id={BLUR_ID} x="-10%" y="-20%" width="120%" height="140%">
          <feGaussianBlur stdDeviation={`2 ${blurY}`} />
        </filter>
      </svg>
      <Particles seed={`subject-${card.number}`} />
      <Sequence durationInFrames={BURST_FRAMES} layout="none">
        <FireBurst />
      </Sequence>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: 56}}>
        <div
          style={{
            width: BOX,
            height: BOX,
            transform: `scale(${enter * exitScale * squeezeX}, ${enter * exitScale})`,
            filter: boxFilter || undefined,
            position: 'relative',
            border: '12px solid #ffb02e',
            borderRadius: 10,
            overflow: 'hidden',
            boxShadow: [
              `0 0 ${18 + 22 * glow}px rgba(255,176,46,${0.9 * glow})`,
              `0 0 ${50 + 50 * glow}px rgba(255,90,20,${0.75 * glow})`,
              `0 0 ${110 + 60 * glow}px rgba(255,50,0,${0.45 * glow})`,
              `inset 0 0 ${24 + 16 * glow}px rgba(255,140,30,${0.8 * glow})`,
            ].join(', '),
          }}
        >
          {card.kind === 'video' ? (
            <Video src={src} muted trimBefore={card.clipOffset} objectFit="cover" style={{width: '100%', height: '100%'}} />
          ) : (
            <Img src={src} style={media} />
          )}
          <TextBlurs boxes={card.blurs} />
        </div>
        <div
          style={{
            fontFamily: ANTON,
            fontSize: 110,
            color: 'white',
            letterSpacing: 2,
            textAlign: 'center',
            maxWidth: 1000,
            lineHeight: 1.05,
            opacity: enter > 1.5 ? 0 : 1, // label nongol begitu box hampir di ukuran normal
            WebkitTextStroke: '6px black',
            paintOrder: 'stroke fill',
            textShadow: '0 6px 18px rgba(0,0,0,0.8)',
          }}
        >
          {card.label}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
