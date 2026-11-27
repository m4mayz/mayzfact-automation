import React from 'react';
import {interpolate, Sequence, useCurrentFrame} from 'remotion';
import {Lottie} from '@remotion/lottie';
import {useLottieJson} from './Emojis';
import {MobileLike} from './FaktaCuilLike';
import {MobileSubscribe} from './FaktaCuilSubscribe';
import {Sticker} from './FaktaCuilStickers';
import type {FaktaCuilSceneData} from './types';

// Alur dari CTA tengah FaktaBor pJe_Qok8qDA: tombol like muncul di awal ajakan, di-tap di kata pemicu,
// tahan ±0,7 detik (LIKED_HOLD), lalu stiker membesar. Visual like-nya versi HP (FaktaCuilLike.tsx, D-070).
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const PILL_X = 540;
const PILL_Y = 750; // ±39% tinggi frame
const LIKE_Y_EMOJI = 560; // format emoji: emoji muncul barengan di STICKER_Y, tombol like naik biar nggak nutup
const LIKED_HOLD = 20;
const STICKER_GAP = 2;
const STICKER_SIZE = 440;
const STICKER_Y = 1030;
// Harus sama kayak FAKTACUIL_SUBSCRIBE_CLICK di mayzfact/steps/timeline.py.
const SUB_CLICK = 12;

type StickerMotion = {dx: number; dy: number; rotate: number; scale: number; opacity: number};

// Satu gerak stiker buat semua format CTA: pop lembut + goyang, pudar di frame terakhir scene.
const stickerMotion = (f: number, len: number): StickerMotion => {
  const fadeIn = interpolate(f, [0, 2], [0, 1], clamp);
  const fadeOut = interpolate(f, [len - 6, len], [1, 0], clamp);
  return {
    dx: 0, dy: 0, rotate: Math.sin(f / 6) * 4,
    scale: interpolate(f, [0, 3, 7], [0.2, 1.15, 1], clamp) * interpolate(f, [len - 6, len], [1, 0.4], clamp),
    opacity: fadeIn * fadeOut,
  };
};

// Emoji CTA pop masuk lalu tahan penuh sampai scene selesai (tanpa fade-out).
const emojiMotion = (f: number): StickerMotion => ({
  dx: 0, dy: 0, rotate: Math.sin(f / 6) * 4,
  scale: interpolate(f, [0, 3, 7], [0.2, 1.15, 1], clamp),
  opacity: interpolate(f, [0, 2], [0, 1], clamp),
});

// Font bawaan Windows mecah emoji ZWJ ini jadi kucing oranye dan kotak hitam.
const BlackCatEmoji: React.FC = () => (
  <svg role="img" aria-label="🐈‍⬛" width="100%" height="100%" viewBox="0 0 128 128">
    <path d="M88 96c23-11 36-36 20-49-7-6-17-4-21 3" fill="none" stroke="#1c1926" strokeWidth="11" strokeLinecap="round"/>
    <path d="M40 64c6-11 13-14 24-14 14 0 24 11 25 26l6 24c1 6-3 10-9 10H36c-6 0-10-4-8-9z" fill="#262331" stroke="#121019" strokeWidth="4"/>
    <path d="M26 53l-4-24c-1-4 3-5 6-3l19 13c9-3 18-3 26 0l17-13c4-3 7-1 6 4l-3 23c5 6 7 12 7 19 0 13-16 22-37 22-22 0-41-8-41-22 0-7 1-12 4-19z" fill="#302c3d" stroke="#121019" strokeWidth="4" strokeLinejoin="round"/>
    <path d="M31 40l2 12 10-7zm57 0-2 12-10-7z" fill="#865b79"/>
    <ellipse cx="46" cy="65" rx="8" ry="10" fill="#ffd46b"/><ellipse cx="76" cy="65" rx="8" ry="10" fill="#ffd46b"/>
    <path d="M46 58v14m30-14v14" stroke="#15121d" strokeWidth="4" strokeLinecap="round"/>
    <path d="M55 75h12l-6 6z" fill="#f39cba"/>
  </svg>
);

export const FaktaCuilCtaVisual: React.FC<{scene: FaktaCuilSceneData; frame: number}> = ({scene, frame}) => {
  const lottie = useLottieJson(scene.emojiSrc);
  const likeCue = scene.cues.find((cue) => cue.kind === 'like');
  const likeStage = scene.stages.find((stage) => stage.kind === 'like');
  const clickAt = likeCue ? likeCue.from - scene.from
    : likeStage ? likeStage.from - scene.from + (likeStage.triggerAt ?? 12) : 12;
  const subCue = scene.cues.find((cue) => cue.kind === 'subscribe');
  const subStage = scene.stages.find((stage) => stage.kind === 'subscribe');
  // Ikut cue Python apa adanya; tombol like dipotong biar nggak nabrak tombol subscribe.
  const subFrom = subCue ? subCue.from - scene.from
    : subStage ? subStage.from - scene.from : null;
  const pillEnd = Math.min(clickAt + LIKED_HOLD, subFrom ?? scene.durationInFrames, scene.durationInFrames);

  const subDur = subStage ? subStage.durationInFrames : Math.max(0, scene.durationInFrames - (subFrom ?? 0));
  // Clamp sama kayak clickAt di _faktacuil_clicks supaya bunyi klik pas sama kursor.
  const subClickAt = Math.min(SUB_CLICK, Math.max(0, subDur - 1));
  const subClicked = subFrom !== null && frame >= subFrom + subClickAt;
  const subEnd = subFrom !== null ? Math.min(subFrom + subClickAt + LIKED_HOLD, scene.durationInFrames) : 0;

  const hasEmoji = scene.format === 'emoji' || scene.format === 'emoji_question';
  const stickerFrom = hasEmoji ? clickAt : pillEnd + STICKER_GAP;
  const stickerFrame = frame - stickerFrom;
  const stickerLen = scene.durationInFrames - stickerFrom;
  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
      {/* Stiker/emoji digambar duluan; tombol like/subscribe di atasnya biar asap stiker nggak nutup. */}
      {hasEmoji ? (
        stickerFrame >= 0 && stickerLen > 0 ? (() => {
          const m = emojiMotion(stickerFrame);
          const box = {
            position: 'absolute' as const, left: PILL_X + m.dx, top: STICKER_Y + m.dy, translate: '-50% -50%',
            rotate: `${m.rotate}deg`, scale: m.scale, opacity: m.opacity, width: STICKER_SIZE, height: STICKER_SIZE,
          };
          if (scene.emojiSrc && lottie) {
            return (
              <div data-cta-emoji="lottie" style={box}>
                <Lottie animationData={lottie} loop style={{width: STICKER_SIZE, height: STICKER_SIZE}}/>
              </div>
            );
          }
          return (
            <div data-cta-emoji="static" style={{
              ...box, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: STICKER_SIZE, lineHeight: 1,
              fontFamily: '"Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif',
            }}>{scene.format === 'emoji_question' && scene.emoji === '🐈‍⬛' ? <BlackCatEmoji/> : scene.emoji}</div>
          );
        })() : null
      ) : stickerFrame >= 0 && stickerLen > 0 && scene.theme ? (() => {
        const m = stickerMotion(stickerFrame, stickerLen);
        return (
          <div data-cta-sticker="true" data-cta-format={scene.format} style={{
            position: 'absolute', left: PILL_X + m.dx, top: STICKER_Y + m.dy, translate: '-50% -50%',
            rotate: `${m.rotate}deg`, scale: m.scale, opacity: m.opacity,
          }}>
            <Sticker theme={scene.theme} frame={stickerFrame} size={STICKER_SIZE}/>
          </div>
        );
      })() : null}
      {frame < pillEnd ? <MobileLike frame={frame} clickAt={clickAt} end={pillEnd} x={PILL_X} y={hasEmoji ? LIKE_Y_EMOJI : PILL_Y}/> : null}
      {subFrom !== null && frame >= subFrom && frame < subEnd ? (
        <MobileSubscribe frame={frame - subFrom} clickAt={subClickAt} end={subEnd - subFrom} x={PILL_X} y={PILL_Y}/>
      ) : null}
    </div>
  );
};

const Visual: React.FC<{scene: FaktaCuilSceneData}> = ({scene}) => <FaktaCuilCtaVisual scene={scene} frame={useCurrentFrame()}/>;

export const FaktaCuilCta: React.FC<{scene: FaktaCuilSceneData}> = ({scene}) => (
  <Sequence from={scene.from} durationInFrames={scene.durationInFrames} layout="none">
    <Visual scene={scene}/>
  </Sequence>
);
