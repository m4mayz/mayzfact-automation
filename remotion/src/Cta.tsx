import React from 'react';
import {interpolate, random, Sequence, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {MONTSERRAT} from './fonts';
import type {CtaAction} from './types';

const CX = 540;
const CY = 1190; // tepat di atas caption, kayak di source
const BLUE = '#2563eb';
const BLUE_DARK = '#1d4ed8';
const RED = '#e3262c';
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Ikon jempol (path Material Icons "thumb_up", Apache-2.0), viewBox 24x24.
const THUMB = 'M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z';

const Thumb: React.FC<{size: number; color: string; style?: React.CSSProperties}> = ({size, color, style}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{overflow: 'visible', ...style}}>
    <path d={THUMB} fill={color} />
  </svg>
);

// Kursor tangan putih ber-outline hitam; ujung telunjuk di titik (0,0).
const Cursor: React.FC<{x: number; y: number; opacity?: number; pressed?: boolean}> = ({x, y, opacity = 1, pressed = false}) => (
  <svg
    width={70}
    height={90}
    viewBox="-8 -4 52 64"
    style={{position: 'absolute', left: x - 8, top: y - 4, opacity, transform: `scale(${pressed ? 0.88 : 1})`, transformOrigin: '8px 4px'}}
  >
    <path
      d="M10 2 c3 0 5 2 5 5 v14 h2 v-4 c0-3 5-3 5 0 v4 h2 v-2 c0-3 5-3 5 0 v3 h2 c0-3 5-3 5 0 v12 c0 10-6 16-15 16 h-4 c-6 0-9-3-12-8 l-6-11 c-2-3 2-6 5-3 l4 5 v-26 c0-3 2-5 4-5 z"
      fill="white"
      stroke="black"
      strokeWidth={2.6}
      strokeLinejoin="round"
    />
  </svg>
);

// Partikel kecil (jempol mini / segitiga confetti) yang terbang keluar dari satu titik.
const Burst: React.FC<{seed: string; frame: number; count: number; kind: 'thumb' | 'triangle'; spread: number}> = ({
  seed,
  frame,
  count,
  kind,
  spread,
}) => (
  <>
    {Array.from({length: count}, (_, i) => {
      const angle = (kind === 'triangle' ? -Math.PI * (0.15 + 0.7 * random(`${seed}-a-${i}`)) : random(`${seed}-a-${i}`) * Math.PI * 2);
      const speed = spread * (0.55 + 0.6 * random(`${seed}-s-${i}`));
      const t = frame / 10;
      const x = CX + Math.cos(angle) * speed * t;
      const y = CY - 40 + Math.sin(angle) * speed * t + (kind === 'triangle' ? 90 * t * t : 0);
      const size = (kind === 'triangle' ? 16 : 22) * (0.6 + 0.6 * random(`${seed}-z-${i}`));
      const color = i % 2 === 0 ? (kind === 'triangle' ? RED : BLUE) : 'white';
      const opacity = interpolate(frame, [0, 2, 9, 12], [0, 1, 1, 0], clamp);
      const spin = 360 * random(`${seed}-r-${i}`) + frame * 25;
      return kind === 'thumb' ? (
        <Thumb key={i} size={size} color={color} style={{position: 'absolute', left: x, top: y, opacity, transform: `rotate(${spin / 6}deg)`}} />
      ) : (
        <svg key={i} width={size} height={size} viewBox="0 0 10 10" style={{position: 'absolute', left: x, top: y, opacity, transform: `rotate(${spin}deg)`}}>
          <polygon points="5,0 10,10 0,10" fill={color} stroke="rgba(0,0,0,0.25)" strokeWidth={0.6} />
        </svg>
      );
    })}
  </>
);

// LIKE (16 frame, klik di frame 3): tombol bulat biru → klik → pecah → jempol biru gede naik → miring, mengecil, hilang.
const Like: React.FC<{action: CtaAction}> = ({action}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const click = action.clickAt;
  const end = action.durationInFrames;
  const button = frame < click ? spring({frame, fps, config: {damping: 12, stiffness: 260}, durationInFrames: 3}) : 0;
  const after = frame - click;
  const grow = interpolate(after, [0, 3, 8], [0.4, 1.35, 1.5], clamp);
  const fall = interpolate(frame, [end - 5, end], [0, 1], clamp);
  const bigScale = grow * (1 - 0.65 * fall);
  const bigOpacity = after < 0 ? 0 : interpolate(frame, [end - 2, end], [1, 0], clamp);
  const cursorX = interpolate(frame, [0, click], [CX + 90, CX + 18], clamp);
  const cursorY = interpolate(frame, [0, click], [CY + 110, CY + 22], clamp);
  return (
    <>
      {frame < click ? (
        <div
          style={{
            position: 'absolute',
            left: CX - 80,
            top: CY - 80,
            width: 160,
            height: 160,
            borderRadius: '50%',
            background: `radial-gradient(circle at 35% 30%, #4f8cff, ${BLUE} 60%, ${BLUE_DARK})`,
            boxShadow: '0 10px 24px rgba(0,0,0,0.45)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            transform: `scale(${button})`,
          }}
        >
          <Thumb size={84} color="white" />
        </div>
      ) : null}
      {after >= 0 ? <Burst seed={`like-${action.from}`} frame={after} count={10} kind="thumb" spread={260} /> : null}
      {after >= 0 ? (
        <div
          style={{
            position: 'absolute',
            left: CX - 90,
            top: CY - 150,
            width: 180,
            height: 180,
            opacity: bigOpacity,
            transform: `translate(${70 * fall}px, ${-30 * grow + 110 * fall}px) rotate(${-8 + 34 * fall}deg) scale(${bigScale})`,
            filter: `drop-shadow(7px 7px 0 ${BLUE_DARK}) drop-shadow(0 12px 18px rgba(0,0,0,0.45))`,
          }}
        >
          <Thumb size={180} color={BLUE} />
        </div>
      ) : null}
      <Cursor x={cursorX} y={cursorY} pressed={frame === click} opacity={interpolate(frame, [end - 4, end], [1, 0], clamp)} />
    </>
  );
};

const PILL_W = 520;
const PILL_H = 110;
const WORD_IN = 'SUBSCRIBE';
const WORD_DONE = 'SUBSCRIBED';

// SUBSCRIBE (27 frame, klik di frame 13): kotak putih melebar → huruf merah mantul masuk → kursor naik → klik +
// confetti → flip jadi merah "SUBSCRIBED" gede, goyang → flip lagi → ukuran normal → hilang.
const Subscribe: React.FC<{action: CtaAction}> = ({action}) => {
  const frame = useCurrentFrame();
  const click = action.clickAt;
  const end = action.durationInFrames;
  const done = frame >= click + 1;
  const widen = interpolate(frame, [0, 2], [0.05, 1], clamp);
  // Flip pertama (klik): putih → merah; flip kedua: merah gede → merah normal.
  const flip1 = interpolate(frame, [click, click + 1, click + 2], [1, 0, 1], clamp);
  const flip2 = interpolate(frame, [click + 8, click + 10, click + 11], [1, 0, 1], clamp);
  const flipY = frame < click + 2 ? flip1 : flip2;
  const big = done ? interpolate(frame, [click + 2, click + 8, click + 10], [1.18, 1.22, 1], clamp) : interpolate(frame, [click, click + 1], [1, 0.94], clamp);
  const tilt = done
    ? interpolate(frame, [click + 1, click + 4, click + 6, click + 8, click + 10], [-6, 0, -8, -4, 0], clamp)
    : interpolate(frame, [click, click + 1], [0, -4], clamp);
  const opacity = interpolate(frame, [end - 2, end], [1, 0], clamp);
  const cursorY = interpolate(frame, [4, click], [CY + 220, CY + 18], clamp);
  const pillLeft = CX - PILL_W / 2 + 40;
  return (
    <>
      <div style={{position: 'absolute', left: pillLeft - 92, top: CY - 36, opacity}}>
        <Thumb size={72} color={BLUE} style={{filter: `drop-shadow(3px 3px 0 ${BLUE_DARK})`}} />
      </div>
      <div
        style={{
          position: 'absolute',
          left: pillLeft,
          top: CY - PILL_H / 2,
          width: PILL_W,
          height: PILL_H,
          opacity,
          transformOrigin: done ? '50% 50%' : '0% 50%',
          transform: `rotate(${tilt}deg) scale(${big * (done ? 1 : 1)}) scaleX(${done ? 1 : widen}) scaleY(${flipY})`,
          background: done ? RED : 'white',
          borderRadius: 18,
          boxShadow: '0 10px 22px rgba(0,0,0,0.45)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          fontFamily: MONTSERRAT,
          fontWeight: 800,
          fontSize: done ? 62 : 64,
          letterSpacing: 1,
          color: done ? 'white' : RED,
        }}
      >
        {done
          ? WORD_DONE
          : WORD_IN.split('').map((letter, i) => {
              const appear = 1 + i * 0.45;
              const pop = interpolate(frame, [appear, appear + 1, appear + 2], [0, 1.35, 1], clamp);
              return (
                <span key={i} style={{display: 'inline-block', transform: `scale(${pop})`}}>
                  {letter}
                </span>
              );
            })}
      </div>
      {frame >= click ? <Burst seed={`sub-${action.from}`} frame={frame - click} count={16} kind="triangle" spread={300} /> : null}
      {frame >= 4 ? (
        <Cursor x={CX + 120} y={cursorY} pressed={frame === click} opacity={interpolate(frame, [click + 7, click + 10], [1, 0], clamp)} />
      ) : null}
    </>
  );
};

// CTA like/subscribe pas narasinya nyebut kata itu (timing dari timeline.json, ngikutin source i2xag).
export const Cta: React.FC<{actions: CtaAction[]}> = ({actions}) => (
  <>
    {actions.map((action, index) => (
      <Sequence key={index} from={action.from} durationInFrames={action.durationInFrames} layout="none">
        {action.kind === 'like' ? <Like action={action} /> : <Subscribe action={action} />}
      </Sequence>
    ))}
  </>
);
