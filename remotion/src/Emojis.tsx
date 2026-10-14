import React, {useEffect, useState} from 'react';
import {Lottie, type LottieAnimationData} from '@remotion/lottie';
import {continueRender, delayRender, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {EmojiOverlay} from './types';

const SIZE = 370; // emoji yang kelihatan ±300px, kayak di source
const CENTER_Y = 1180; // tepat di atas caption (caption di 75% = 1440)
const FADE_FRAMES = 6;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Emoji animasi Noto (Lottie): pop masuk, animasinya jalan terus, fade di akhir.
const EmojiAnim: React.FC<{emoji: EmojiOverlay}> = ({emoji}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const [data, setData] = useState<LottieAnimationData | null>(null);
  const [handle] = useState(() => delayRender(`emoji ${emoji.src}`));
  useEffect(() => {
    fetch(staticFile(emoji.src))
      .then((response) => response.json())
      .then((json) => {
        setData(json);
        continueRender(handle);
      })
      .catch((error) => {
        // File emoji rusak/hilang: emoji-nya dilewat, render jangan sampai nge-hang.
        console.error(`emoji ${emoji.src} gagal dimuat`, error);
        continueRender(handle);
      });
  }, [emoji.src, handle]);
  if (!data) {
    return null;
  }
  const pop = spring({frame, fps, config: {damping: 9, stiffness: 220}, durationInFrames: 8});
  const opacity = interpolate(frame, [emoji.durationInFrames - FADE_FRAMES, emoji.durationInFrames], [1, 0], clamp);
  return (
    <div
      style={{
        position: 'absolute',
        left: 540 - SIZE / 2,
        top: CENTER_Y - SIZE / 2,
        width: SIZE,
        height: SIZE,
        transform: `scale(${pop})`,
        opacity,
        filter: 'drop-shadow(0 8px 14px rgba(0,0,0,0.45))',
      }}
    >
      <Lottie animationData={data} loop style={{width: SIZE, height: SIZE}} />
    </div>
  );
};

export const Emojis: React.FC<{emojis: EmojiOverlay[]}> = ({emojis}) => {
  const {fps} = useVideoConfig();
  return (
    <>
      {emojis.map((emoji, index) => (
        // premount: JSON Lottie dimuat duluan biar nggak telat muncul di preview Studio.
        <Sequence key={index} from={emoji.from} durationInFrames={emoji.durationInFrames} premountFor={fps}>
          <EmojiAnim emoji={emoji} />
        </Sequence>
      ))}
    </>
  );
};
