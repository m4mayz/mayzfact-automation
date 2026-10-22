import React from 'react';
import {Video} from '@remotion/media';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import fire from './assets/fire-burst.mp4';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Ledakan api biru pas angka countdown (di atas angka) dan box foto subjek (di belakang box) masuk, niru source
// i2xag (#3 platypus 37.65-38.05 dtk): api rapet di tengah, ngembang jadi cincin dengan tengah gelap, terus pudar.
// Sumbernya "Blue Fire Powers Pack" blackscreen (youtube.com/watch?v=Q46O_LHNDns, detik 64,7-65,45), diperlambat
// 0,5x pakai minterpolate dan diputer 90° jadi portrait biar menuhin layar tanpa di-crop. 46 frame.
// Blend `screen` bikin hitamnya ilang.
export const FIRE_RING_AT = 24; // frame klip pas cincin apinya seukuran box foto subjek
export const FIRE_WHITE_AT = 38; // dari sini klipnya makin putih menuhin layar
export const FIRE_FRAMES = 46;
const FADE_FRAMES = 10;

// Bagian klip [startAt, endAt) dimainin pas `durationInFrames` frame (playbackRate nyesuaiin panjang kartu).
export const FireBurst: React.FC<{durationInFrames: number; startAt?: number; endAt?: number; fadeOut?: boolean}> = ({
  durationInFrames,
  startAt = 0,
  endAt = FIRE_FRAMES,
  fadeOut = false,
}) => {
  const frame = useCurrentFrame();
  const fadeIn = startAt === 0 ? interpolate(frame, [0, 1], [0.6, 1], clamp) : 1;
  // pudarnya cuma sampai setengah: api masih keliatan sampai kartu ganti
  const fade = fadeOut ? interpolate(frame, [durationInFrames - FADE_FRAMES, durationInFrames], [1, 0.5], clamp) : 1;
  // opacity ditaruh di Video-nya sendiri; kalau di wrapper jadi grup terisolasi dan blend `screen`-nya nggak kena
  // background (hitamnya keliatan)
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <Video
        src={fire}
        muted
        trimBefore={startAt}
        playbackRate={(endAt - startAt) / durationInFrames}
        objectFit="contain"
        style={{width: '100%', height: '100%', opacity: fadeIn * fade, mixBlendMode: 'screen'}}
      />
    </AbsoluteFill>
  );
};
