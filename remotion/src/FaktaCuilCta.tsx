import React from 'react';
import {interpolate, Sequence, useCurrentFrame} from 'remotion';
import {Cursor, Thumb} from './Cta';
import {Sticker} from './FaktaCuilStickers';
import {MONTSERRAT} from './fonts';
import type {CtaSceneData} from './types';

// Ditiru dari CTA tengah FaktaBor pJe_Qok8qDA (dicek 10 fps): pill gelap "LIKE" muncul di awal ajakan,
// kursor panah masuk, jadi tangan, klik di kata "like" → pill biru "LIKED" ±0,7 detik, lalu stiker objek membesar.
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const PILL_X = 540;
const PILL_Y = 750; // ±39% tinggi frame
const LIKED_HOLD = 20;
const STICKER_GAP = 2;
const STICKER_SIZE = 440;
const STICKER_Y = 1030;

const Arrow: React.FC<{x: number; y: number}> = ({x, y}) => (
  <svg width={62} height={86} viewBox="-3 -3 34 46" style={{position: 'absolute', left: x - 3, top: y - 3}}>
    <path d="M0 0 L0 34 L9 26 L15 40 L21 37 L15 24 L27 24 Z" fill="white" stroke="black" strokeWidth={2.4} strokeLinejoin="round"/>
  </svg>
);

const Pill: React.FC<{liked: boolean; scale: number; opacity: number}> = ({liked, scale, opacity}) => (
  <div style={{
    position: 'absolute', left: PILL_X, top: PILL_Y, translate: '-50% -50%', rotate: '-4deg', scale, opacity,
    display: 'flex', alignItems: 'center', gap: 26, height: 196, padding: '0 50px', borderRadius: 30,
    background: liked ? '#1468f0' : 'rgba(28,28,30,0.94)', boxShadow: '0 12px 32px rgba(0,0,0,.35)',
    fontFamily: MONTSERRAT, fontWeight: 800, fontSize: 98, color: 'white', whiteSpace: 'nowrap',
  }}>
    <Thumb size={92} color="white"/>
    {liked ? 'LIKED' : 'LIKE'}
  </div>
);

export const FaktaCuilCtaVisual: React.FC<{scene: CtaSceneData; frame: number}> = ({scene, frame}) => {
  const likeCue = scene.cues.find((cue) => cue.kind === 'like');
  const likeStage = scene.stages.find((stage) => stage.kind === 'like');
  const clickAt = likeCue ? likeCue.from - scene.from
    : likeStage ? likeStage.from - scene.from + (likeStage.triggerAt ?? 12) : 12;
  const pillEnd = Math.min(clickAt + LIKED_HOLD, scene.durationInFrames);
  const stickerFrom = pillEnd + STICKER_GAP;
  const stickerFrame = frame - stickerFrom;
  const stickerLen = scene.durationInFrames - stickerFrom;
  const liked = frame >= clickAt;
  const pop = interpolate(frame, [0, 2, 4], [0.8, 1.05, 1], clamp) * interpolate(frame - clickAt, [0, 3, 6], [1, 1.1, 1], clamp);
  const arrowT = interpolate(frame, [clickAt - 10, clickAt - 3], [0, 1], clamp);
  const tipX = PILL_X + 90;
  const tipY = PILL_Y + 40;
  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
      {frame < pillEnd ? <>
        <Pill liked={liked} scale={pop} opacity={interpolate(frame, [0, 2], [0, 1], clamp)}/>
        {frame >= clickAt - 10 && frame < clickAt - 3 ?
          <Arrow x={interpolate(arrowT, [0, 1], [tipX + 200, tipX])} y={interpolate(arrowT, [0, 1], [tipY + 220, tipY])}/> : null}
        {frame >= clickAt - 3 ? <Cursor x={tipX} y={tipY} pressed={frame >= clickAt && frame < clickAt + 3}/> : null}
      </> : null}
      {stickerFrame >= 0 && stickerLen > 0 ? (
        <div data-cta-sticker="true" style={{
          position: 'absolute', left: PILL_X, top: STICKER_Y, translate: '-50% -50%',
          rotate: `${Math.sin(stickerFrame / 6) * 4}deg`,
          scale: interpolate(stickerFrame, [0, 3, 7], [0.2, 1.15, 1], clamp) * interpolate(stickerFrame, [stickerLen - 6, stickerLen], [1, 0.4], clamp),
          opacity: interpolate(stickerFrame, [0, 2], [0, 1], clamp) * interpolate(stickerFrame, [stickerLen - 6, stickerLen], [1, 0], clamp),
        }}>
          <Sticker theme={scene.theme} frame={stickerFrame} size={STICKER_SIZE}/>
        </div>
      ) : null}
    </div>
  );
};

const Visual: React.FC<{scene: CtaSceneData}> = ({scene}) => <FaktaCuilCtaVisual scene={scene} frame={useCurrentFrame()}/>;

export const FaktaCuilCta: React.FC<{scene: CtaSceneData}> = ({scene}) => (
  <Sequence from={scene.from} durationInFrames={scene.durationInFrames} layout="none">
    <Visual scene={scene}/>
  </Sequence>
);
