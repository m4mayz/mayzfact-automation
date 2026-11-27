import React from 'react';
import {interpolate, Sequence, useCurrentFrame} from 'remotion';
import {Lottie} from '@remotion/lottie';
import {Cursor} from './Cta';
import {useLottieJson} from './Emojis';
import {Sticker} from './FaktaCuilStickers';
import {MONTSERRAT} from './fonts';
import type {FaktaCuilSceneData} from './types';

// Ditiru dari CTA tengah FaktaBor pJe_Qok8qDA (dicek 10 fps): pill gelap "LIKE" muncul di awal ajakan,
// kursor panah masuk, jadi tangan, klik di kata pemicu → pill biru "LIKED" ±0,7 detik, lalu stiker membesar.
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const PILL_X = 540;
const PILL_Y = 750; // ±39% tinggi frame
const LIKED_HOLD = 20;
const STICKER_GAP = 2;
const STICKER_SIZE = 440;
const STICKER_Y = 1030;
// Harus sama kayak FAKTACUIL_SUBSCRIBE_CLICK di mayzfact/steps/timeline.py.
const SUB_CLICK = 12;

const Arrow: React.FC<{x: number; y: number}> = ({x, y}) => (
  <svg width={62} height={86} viewBox="-3 -3 34 46" style={{position: 'absolute', left: x - 3, top: y - 3}}>
    <path d="M0 0 L0 34 L9 26 L15 40 L21 37 L15 24 L27 24 Z" fill="white" stroke="black" strokeWidth={2.4} strokeLinejoin="round"/>
  </svg>
);

// Tombol like Shorts sekarang hati, bukan jempol (blog YouTube, 25 Juni 2026): outline sebelum klik, penuh sesudahnya.
const HEART = 'M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z';

const Heart: React.FC<{size: number; filled: boolean; scale: number}> = ({size, filled, scale}) => (
  <svg data-cta-heart={filled ? 'filled' : 'outline'} width={size} height={size} viewBox="0 0 24 24"
    style={{overflow: 'visible', scale}}>
    <path d={HEART} fill={filled ? 'white' : 'none'} stroke="white" strokeWidth={filled ? 0 : 2.2} strokeLinejoin="round"/>
  </svg>
);

const Pill: React.FC<{kind: 'like' | 'subscribe'; label: string; bg: string; scale: number; opacity: number;
  liked?: boolean; heartScale?: number}> = ({kind, label, bg, scale, opacity, liked = false, heartScale = 1}) => (
  <div data-cta-pill={kind} style={{
    position: 'absolute', left: PILL_X, top: PILL_Y, translate: '-50% -50%', rotate: '-4deg', scale, opacity,
    display: 'flex', alignItems: 'center', gap: 26, height: 196, padding: '0 50px', borderRadius: 30,
    background: bg, boxShadow: '0 12px 32px rgba(0,0,0,.35)',
    fontFamily: MONTSERRAT, fontWeight: 800, fontSize: 92, color: 'white', whiteSpace: 'nowrap',
  }}>
    {kind === 'like' ? <Heart size={92} filled={liked} scale={heartScale}/> : null}
    {label}
  </div>
);

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
  // Ikut cue Python apa adanya; pill LIKED yang dipotong biar nggak nabrak pill SUBSCRIBE.
  const subFrom = subCue ? subCue.from - scene.from
    : subStage ? subStage.from - scene.from : null;
  const pillEnd = Math.min(clickAt + LIKED_HOLD, subFrom ?? scene.durationInFrames, scene.durationInFrames);
  const liked = frame >= clickAt;
  const pop = interpolate(frame, [0, 2, 4], [0.8, 1.05, 1], clamp) * interpolate(frame - clickAt, [0, 3, 6], [1, 1.1, 1], clamp);
  const arrowT = interpolate(frame, [clickAt - 10, clickAt - 3], [0, 1], clamp);
  const tipX = PILL_X + 90;
  const tipY = PILL_Y + 40;

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
      {/* Stiker/emoji digambar duluan; pill + kursor di atasnya biar asap stiker nggak nutup pill. */}
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
      {frame < pillEnd ? <>
        <Pill kind="like" label={liked ? 'LIKED' : 'LIKE'} bg={liked ? '#1468f0' : 'rgba(28,28,30,0.94)'}
          scale={pop} opacity={interpolate(frame, [0, 2], [0, 1], clamp)} liked={liked}
          heartScale={liked ? interpolate(frame - clickAt, [0, 3, 6], [0.6, 1.25, 1], clamp) : 1}/>
        {frame >= clickAt - 10 && frame < clickAt - 3 ?
          <Arrow x={interpolate(arrowT, [0, 1], [tipX + 200, tipX])} y={interpolate(arrowT, [0, 1], [tipY + 220, tipY])}/> : null}
        {frame >= clickAt - 3 ? <Cursor x={tipX} y={tipY} pressed={frame >= clickAt && frame < clickAt + 3}/> : null}
      </> : null}
      {subFrom !== null && frame >= subFrom && frame < subEnd ? <>
        <Pill kind="subscribe" label={subClicked ? 'SUBSCRIBED' : 'SUBSCRIBE'}
          bg={subClicked ? 'rgba(28,28,30,0.94)' : '#ff0000'}
          scale={interpolate(frame - subFrom, [0, 2, 4], [0.8, 1.05, 1], clamp)}
          opacity={interpolate(frame - subFrom, [0, 2], [0, 1], clamp)}/>
        {frame >= subFrom + subClickAt - 3 ?
          <Cursor x={tipX} y={tipY} pressed={subClicked && frame < subFrom + subClickAt + 3}/> : null}
      </> : null}
    </div>
  );
};

const Visual: React.FC<{scene: FaktaCuilSceneData}> = ({scene}) => <FaktaCuilCtaVisual scene={scene} frame={useCurrentFrame()}/>;

export const FaktaCuilCta: React.FC<{scene: FaktaCuilSceneData}> = ({scene}) => (
  <Sequence from={scene.from} durationInFrames={scene.durationInFrames} layout="none">
    <Visual scene={scene}/>
  </Sequence>
);
