import React, {useEffect, useState} from 'react';
import {Lottie, type LottieAnimationData} from '@remotion/lottie';
import {continueRender, delayRender, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {EmojiOverlay} from './types';

const SIZE = 370; // emoji yang kelihatan ±300px, kayak di source
const CENTER_Y = 1180; // tepat di atas caption (caption di 75% = 1440)
const FADE_FRAMES = 6;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Dimuat sekali per src; dipakai emoji overlay dan emoji CTA FaktaCuil.
export const useLottieJson = (src?: string): LottieAnimationData | null => {
  const [data, setData] = useState<LottieAnimationData | null>(null);
  // delayRender cuma kalau src ada: CTA emoji statis nggak perlu nunggu fetch
  const [handle] = useState<number | null>(() => (src ? delayRender(`emoji ${src}`) : null));
  useEffect(() => {
    if (!src) {
      return;
    }
    fetch(staticFile(src))
      .then((response) => response.json())
      .then((json: LottieAnimationData) => {
        // Server bisa balikin HTML/JSON lain: tanpa `layers` bukan Lottie, biar CTA pakai fallback statis.
        if (!Array.isArray((json as {layers?: unknown}).layers)) {
          console.error(`emoji ${src} bukan Lottie valid (nggak ada layers)`);
          if (handle !== null) {
            continueRender(handle);
          }
          return;
        }
        setData(json);
        if (handle !== null) {
          continueRender(handle);
        }
      })
      .catch((error) => {
        // File emoji rusak/hilang: emoji-nya dilewat, render jangan sampai nge-hang.
        console.error(`emoji ${src} gagal dimuat`, error);
        if (handle !== null) {
          continueRender(handle);
        }
      });
  }, [src, handle]);
  return data;
};

// Emoji animasi Noto (Lottie): pop masuk, animasinya jalan terus, fade di akhir.
const EmojiAnim: React.FC<{emoji: EmojiOverlay}> = ({emoji}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const data = useLottieJson(emoji.src);
  if (!data) {
    return null;
  }
  const pop = spring({frame, fps, config: {damping: 9, stiffness: 220}, durationInFrames: 8});
  const opacity = interpolate(frame, [emoji.durationInFrames - FADE_FRAMES, emoji.durationInFrames], [1, 0], clamp);
  return (
    <div
      style={{
        position: 'absolute',
        left: (emoji.x ?? 540) - SIZE / 2,
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
