import React from 'react';
import {interpolate, random, Sequence, useCurrentFrame} from 'remotion';
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
const Burst: React.FC<{seed: string; frame: number; count: number; kind: 'thumb' | 'triangle'; spread: number; life?: number}> = ({
  seed,
  frame,
  count,
  kind,
  spread,
  life = 12,
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
      const opacity = interpolate(frame, [0, 2, life - 3, life], [0, 1, 1, 0], clamp);
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

// Ujung kursor di akhir like = di awal subscribe, jadi kursornya nyambung kayak di source.
const CURSOR_REST = {x: CX + 135, y: CY + 97};

// LIKE (16 frame, klik di frame 4), ngikutin source i2xag frame per frame: tombol bulat biru + tulisan LIKE →
// klik: jempol putih → jadi jempol biru gede + jempol mini muncrat → miring searah jarum jam → kebalik
// (jempol ke bawah) → mengecil jadi ikon jempol yang dipakai subscribe.
const Like: React.FC<{action: CtaAction}> = ({action}) => {
  const frame = useCurrentFrame();
  const click = action.clickAt;
  const end = action.durationInFrames;
  const after = frame - click;
  const white = after < 3;
  const down = frame === end - 2;
  const small = frame >= end - 1;
  const tilt = down || small ? 0 : interpolate(frame, [end - 6, end - 5, end - 4, end - 3], [0, 20, 55, 85], clamp);
  const scale = small ? 0.4 : down ? 1.2 : interpolate(after, [0, 1, 2, 3, 4], [0.55, 0.95, 1.15, 1.3, 1.5], clamp);
  const cursorX = interpolate(frame, [end - 3, end - 2], [CX + 30, CURSOR_REST.x], clamp);
  const cursorY = interpolate(frame, [end - 3, end - 2], [CY + 10, CURSOR_REST.y], clamp);
  return (
    <>
      {after < 0 ? (
        <div
          style={{
            position: 'absolute',
            left: CX - 82,
            top: CY - 82,
            width: 164,
            height: 164,
            borderRadius: '50%',
            background: `radial-gradient(circle at 35% 30%, #4f8cff, ${BLUE} 60%, ${BLUE_DARK})`,
            boxShadow: '0 10px 24px rgba(0,0,0,0.45)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
          }}
        >
          <Thumb size={84} color="white" />
        </div>
      ) : null}
      {after <= 0 ? (
        // Tulisan LIKE di bawah tombol; pas diklik gepeng, habis itu hilang.
        <div
          style={{
            position: 'absolute',
            left: CX - 150,
            top: CY + 92,
            width: 300,
            textAlign: 'center',
            fontFamily: MONTSERRAT,
            fontWeight: 800,
            fontSize: 66,
            lineHeight: 1,
            color: 'white',
            textShadow: '0 4px 12px rgba(0,0,0,0.55)',
            transform: `scaleY(${after === 0 ? 0.25 : 1})`,
          }}
        >
          LIKE
        </div>
      ) : null}
      {after >= 3 ? <Burst seed={`like-${action.from}`} frame={after - 3} count={10} kind="thumb" spread={800} life={6} /> : null}
      {after >= 0 ? (
        <div
          style={{
            position: 'absolute',
            left: CX - 90,
            top: CY - 90,
            width: 180,
            height: 180,
            transform: `rotate(${tilt}deg) scale(${scale}) scaleY(${down ? -1 : 1})`,
            filter: `drop-shadow(7px 7px 0 ${white ? '#cbd5e1' : BLUE_DARK}) drop-shadow(0 12px 18px rgba(0,0,0,0.45))`,
          }}
        >
          <Thumb size={180} color={white ? 'white' : BLUE} />
        </div>
      ) : null}
      <Cursor x={cursorX} y={cursorY} pressed={frame === click} />
    </>
  );
};

const PILL_W = 470;
const PILL_H = 94;
const THUMB_GAP = 64; // jarak pusat ikon jempol ke sisi kiri tombol
const WORD_IN = 'SUBSCRIBE';
const WORD_DONE = 'SUBSCRIBED';

// SUBSCRIBE (27 frame, klik di frame 14), ngikutin source i2xag frame per frame: tombol putih melebar dari tengah
// (ikon jempol nempel di kirinya) → huruf merah mantul masuk → kursor naik → klik + confetti → flip 360° jadi merah
// "SUBSCRIBED" gede, goyang → flip 360° lagi, balik ke ukuran normal.
const Subscribe: React.FC<{action: CtaAction}> = ({action}) => {
  const frame = useCurrentFrame();
  const c = action.clickAt;
  const widen = interpolate(frame, [0, 1, 2, 3], [0.06, 0.55, 0.95, 1], clamp);
  // Flip di sumbu X: scaleY = cos(sudut), jadi di 180° tulisannya kebalik kayak di source.
  const angle =
    frame < c + 8
      ? interpolate(frame, [c - 1, c, c + 1, c + 2, c + 3], [0, 20, 180, 250, 360], clamp)
      : interpolate(frame, [c + 8, c + 9, c + 10, c + 11, c + 12], [0, 80, 180, 315, 360], clamp);
  const done = frame >= c + 3;
  const scale = interpolate(frame, [c, c + 1, c + 3, c + 8, c + 9, c + 10, c + 11, c + 12], [1, 1.3, 1.42, 1.38, 1.35, 1.24, 1.08, 1], clamp);
  const tilt = interpolate(
    frame,
    [c - 1, c, c + 1, c + 2, c + 3, c + 4, c + 5, c + 6, c + 7, c + 8, c + 9, c + 10, c + 11, c + 12],
    [0, 3, 0, -15, 5, -1, -4, -6, -7, -6, -3, -1, -2, 0],
    clamp,
  );
  const cursorX = interpolate(frame, [5, 6], [CURSOR_REST.x, CX + 146], clamp);
  const cursorY = interpolate(frame, [5, 7, 8, 9], [CURSOR_REST.y, CY + 85, CY + 60, CY + 32], clamp);
  return (
    <>
      <div style={{position: 'absolute', left: CX - (PILL_W / 2) * widen - THUMB_GAP - 36, top: CY - 36}}>
        <Thumb size={72} color={BLUE} style={{filter: `drop-shadow(3px 3px 0 ${BLUE_DARK})`}} />
      </div>
      <div
        style={{
          position: 'absolute',
          left: CX - PILL_W / 2,
          top: CY - PILL_H / 2,
          width: PILL_W,
          height: PILL_H,
          transform: `rotate(${tilt}deg) scale(${scale}) scaleX(${widen}) scaleY(${Math.cos((angle * Math.PI) / 180)})`,
          background: done ? RED : 'white',
          borderRadius: 16,
          boxShadow: '0 10px 22px rgba(0,0,0,0.45)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          fontFamily: MONTSERRAT,
          fontWeight: 800,
          fontSize: done ? 56 : 62,
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
      {frame >= c ? <Burst seed={`sub-${action.from}`} frame={frame - c} count={16} kind="triangle" spread={300} /> : null}
      <Cursor x={cursorX} y={cursorY} pressed={frame === c} />
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
