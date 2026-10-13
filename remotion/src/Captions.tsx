import React from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {ANTON} from './fonts';
import type {Caption} from './types';

const Word: React.FC<{caption: Caption}> = ({caption}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 4], [0.85, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{alignItems: 'center'}}>
      <div
        style={{
          position: 'absolute',
          top: '68%',
          transform: `translateY(-50%) scale(${scale})`,
          fontFamily: ANTON,
          fontSize: 120,
          color: caption.color,
          WebkitTextStroke: '8px black',
          paintOrder: 'stroke fill',
          textShadow: '0 6px 14px rgba(0,0,0,0.7)',
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
    {captions.map((caption) => (
      <Sequence key={`${caption.from}-${caption.text}`} from={caption.from} durationInFrames={caption.durationInFrames} layout="none">
        <Word caption={caption} />
      </Sequence>
    ))}
  </>
);
