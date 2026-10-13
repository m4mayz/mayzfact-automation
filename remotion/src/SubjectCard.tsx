import React from 'react';
import {AbsoluteFill, Img, interpolate, OffthreadVideo, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {ANTON} from './fonts';
import {Particles} from './Particles';
import type {CountdownCard} from './types';

const BOX = 820;

// Klip subjek di dalam frame menyala + label nama (gaya STURGEON di source i2xag).
export const SubjectCard: React.FC<{card: CountdownCard}> = ({card}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame, fps, config: {damping: 14, stiffness: 150}, durationInFrames: 10});
  const scale = interpolate(pop, [0, 1], [0.8, 1]);
  const glow = 0.65 + 0.35 * Math.sin((frame / fps) * Math.PI * 2.2);
  const src = staticFile(card.src);
  const media: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover'};
  return (
    <AbsoluteFill>
      <Particles seed={`subject-${card.number}`} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', flexDirection: 'column', gap: 56}}>
        <div
          style={{
            width: BOX,
            height: BOX,
            transform: `scale(${scale})`,
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
            <OffthreadVideo src={src} muted trimBefore={card.clipOffset} style={media} />
          ) : (
            <Img src={src} style={media} />
          )}
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
            transform: `scale(${scale})`,
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
