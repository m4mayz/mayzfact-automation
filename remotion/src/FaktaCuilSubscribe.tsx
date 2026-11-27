import React from 'react';
import {Easing, interpolate} from 'remotion';
import {at, TouchTap} from './FaktaCuilLike';
import {FaktaCuilAvatar} from './faktacuilAvatar';
import {ARIMO} from './fonts';

// Subscribe ala Shorts di HP (D-070): avatar + @FaktaCuil + pill putih "Subscribe" → tap → pill abu "Disubscribe".
// Label pakai versi YouTube bahasa Indonesia, sama kayak "Suka" di tombol like.
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const out = Easing.out(Easing.cubic);
const AVATAR = 116;
const PILL_W = 320;
const PILL_H = 96;
// Posisi tetap relatif ke tengah (x): avatar kiri, handle tengah, pill kanan; total ±760 px.
const AVATAR_DX = -305;
const HANDLE_DX = -230;
const PILL_DX = 220;
const CONFETTI_COLORS = ['#ff0033', '#ffffff', '#ffd166', '#2f8cff'];
const CONFETTI = Array.from({length: 14}, (_, i) => ({
  angle: ((i * 360) / 14 - 90 + (i % 2 ? 9 : -9)) * (Math.PI / 180),
  dist: 150 + (i % 3) * 45,
  spin: (i % 2 ? 1 : -1) * (180 + i * 20),
}));

const Bell: React.FC<{size: number; rotate: number}> = ({size, rotate}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{rotate: `${rotate}deg`, transformOrigin: '50% 10%', display: 'block'}}>
    <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" fill="white"/>
  </svg>
);

export const MobileSubscribe: React.FC<{frame: number; clickAt: number; end: number; x: number; y: number}> = ({
  frame, clickAt, end, x, y,
}) => {
  const t = frame - clickAt;
  const done = t >= 0;
  const enter = interpolate(frame, [0, 4, 7], [0.5, 1.06, 1], clamp);
  const rise = interpolate(frame, [0, 6], [40, 0], {...clamp, easing: out});
  const exit = interpolate(frame, [end - 3, end], [1, 0], clamp);
  const pillX = x + PILL_DX;
  // Pill ketekan pas jari nyentuh, lalu mantul sebelum balik normal.
  const pillScale = done
    ? interpolate(t, [0, 1, 4, 7], [0.88, 0.88, 1.1, 1], clamp)
    : interpolate(t, [-2, 0], [1, 0.92], clamp);
  const bellRotate = done ? Math.sin(t * 1.6) * 24 * Math.max(0, 1 - t / 14) : 0;
  return (
    <div data-cta-subscribe="mobile" style={{position: 'absolute', inset: 0, opacity: exit}}>
      {done ? (
        <>
          <div data-cta-sub-burst="true" style={{
            ...at(pillX, y), width: PILL_W + 2 * interpolate(t, [0, 9], [0, 70], {...clamp, easing: out}),
            height: PILL_H + 2 * interpolate(t, [0, 9], [0, 70], {...clamp, easing: out}), borderRadius: 999,
            border: `${interpolate(t, [0, 9], [10, 2], clamp)}px solid white`, opacity: interpolate(t, [0, 2, 9], [0, 0.85, 0], clamp),
          }}/>
          {CONFETTI.map((c, i) => {
            const d = interpolate(t, [0, 12], [40, c.dist], {...clamp, easing: out});
            const fall = interpolate(t, [4, 16], [0, 60], clamp); // gravitasi ringan biar kerasa confetti
            return (
              <div key={i} style={{
                ...at(pillX + Math.cos(c.angle) * d * 1.4, y + Math.sin(c.angle) * d + fall),
                width: i % 3 ? 22 : 16, height: i % 3 ? 12 : 16, borderRadius: i % 3 ? 3 : '50%',
                background: CONFETTI_COLORS[i % CONFETTI_COLORS.length], rotate: `${interpolate(t, [0, 16], [0, c.spin], clamp)}deg`,
                opacity: interpolate(t, [0, 2, 11, 16], [0, 1, 1, 0], clamp), boxShadow: '0 2px 6px rgba(0,0,0,.25)',
              }}/>
            );
          })}
        </>
      ) : null}
      {/* Satu grup biar avatar, handle, dan pill membesar bareng dari tengah baris. */}
      <div style={{position: 'absolute', left: x, top: y + rise, width: 0, height: 0, scale: enter}}>
        <div style={{
          ...at(0, 0), width: 800, height: PILL_H + 44, borderRadius: 999, background: 'rgba(0,0,0,0.45)',
          boxShadow: '0 14px 40px rgba(0,0,0,.3)',
        }}/>
        <div style={at(AVATAR_DX, 0)}><FaktaCuilAvatar size={AVATAR}/></div>
        <div style={{
          position: 'absolute', left: HANDLE_DX, top: 0, translate: '0 -50%',
          fontFamily: ARIMO, fontWeight: 700, fontSize: 46, color: 'white', textShadow: '0 3px 10px rgba(0,0,0,.6)',
          whiteSpace: 'nowrap',
        }}>@FaktaCuil</div>
        <div style={{...at(PILL_DX, 0), scale: pillScale}}>
          <div style={{
            width: PILL_W, height: PILL_H, borderRadius: 999, display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: 12, background: done ? 'rgba(255,255,255,0.24)' : 'white', border: done ? '3px solid rgba(255,255,255,0.35)' : 'none',
            boxShadow: done ? `0 0 ${interpolate(t, [0, 4, 16], [0, 40, 14], clamp)}px rgba(255,255,255,0.6)` : '0 8px 22px rgba(0,0,0,.3)',
            fontFamily: ARIMO, fontWeight: 700, fontSize: 42, color: done ? 'white' : '#0f0f0f', whiteSpace: 'nowrap',
          }}>
            {done ? <Bell size={44} rotate={bellRotate}/> : null}
            {done ? 'Disubscribe' : 'Subscribe'}
          </div>
        </div>
      </div>
      <TouchTap frame={frame} clickAt={clickAt} x={pillX + 118} y={y + 26}/>
    </div>
  );
};
