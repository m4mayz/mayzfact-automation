import React from 'react';
import {Video} from '@remotion/media';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame} from 'remotion';
import fire from './assets/fire-burst.mp4';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Ledakan api biru pas angka countdown (di atas angka) dan box foto subjek (di belakang box) masuk, niru source
// i2xag (#3 platypus 37.65-38.05 dtk): api rapet di tengah, ngembang jadi cincin dengan tengah gelap, terus pudar.
// Sumbernya "Blue Fire Powers Pack" blackscreen (youtube.com/watch?v=Q46O_LHNDns), diputer 90° jadi portrait biar
// menuhin layar tanpa di-crop. 50 frame: frame 0-9 ledakannya kecepatan normal (detik 64,8-65,13) biar barengan
// SFX fire whoosh (puncaknya frame 4-9 kartu), frame 10-49 sisanya diperlambat 0,25x pakai minterpolate (detik
// 65,13-65,45). Blend `screen` bikin hitamnya ilang.
export const FIRE_RING_AT = 10; // ledakan selesai, cincin apinya seukuran box foto subjek
export const FIRE_WHITE_AT = 38; // dari sini klipnya makin putih menuhin layar
export const FIRE_FRAMES = 50;
const FADE_FRAMES = 10;

// Bagian klip [startAt, endAt) dimainin pas `durationInFrames` frame. Ledakan (sebelum FIRE_RING_AT) selalu
// kecepatan normal, sisanya playbackRate-nya nyesuaiin panjang kartu.
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
  const burst = Math.max(0, Math.min(FIRE_RING_AT - startAt, durationInFrames - 1));
  const tailFrom = startAt + burst;
  // opacity ditaruh di Video-nya sendiri; kalau di wrapper jadi grup terisolasi dan blend `screen`-nya nggak kena
  // background (hitamnya keliatan)
  const style: React.CSSProperties = {width: '100%', height: '100%', opacity: fadeIn * fade, mixBlendMode: 'screen'};
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {burst > 0 ? (
        <Sequence durationInFrames={burst} layout="none">
          <Video src={fire} muted trimBefore={startAt} objectFit="contain" style={style} />
        </Sequence>
      ) : null}
      <Sequence from={burst} durationInFrames={durationInFrames - burst} premountFor={burst}>
        <Video
          src={fire}
          muted
          trimBefore={tailFrom}
          playbackRate={(endAt - tailFrom) / (durationInFrames - burst)}
          objectFit="contain"
          style={style}
        />
      </Sequence>
    </AbsoluteFill>
  );
};
