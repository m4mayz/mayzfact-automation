import React from 'react';
import {Easing, interpolate} from 'remotion';
import {ARIMO} from './fonts';

// Like ala Shorts di HP (D-070): tombol hati bulat dari rail kanan + titik sentuh jari, bukan pill + kursor mouse.
// Ikon hati sesuai update Shorts (blog YouTube, 25 Juni 2026). Semua gerak murni dari frame biar bisa dites SSR.
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const out = Easing.out(Easing.cubic);
const HEART = 'M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z';
const RED = '#ff2d55';
const BUTTON = 270;
const ICON = 156;
const PARTICLE_COLORS = ['#ff2d55', '#ff8fab', '#ffd166'];
// Sudut + jarak tetap (bukan random) biar render tiap frame sama persis.
const PARTICLES = Array.from({length: 10}, (_, i) => ({angle: (i * 36 + 18) * (Math.PI / 180), dist: i % 2 ? 200 : 260}));
const FLOATERS = [{dx: -70, delay: 2}, {dx: 40, delay: 4}, {dx: -10, delay: 7}, {dx: 85, delay: 9}];

export const HeartSvg: React.FC<{size: number; fill: string; stroke?: string; strokeWidth?: number; id?: string}> = ({
  size, fill, stroke = 'none', strokeWidth = 0, id,
}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{overflow: 'visible', display: 'block'}}>
    {id ? (
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ff5c7a"/>
          <stop offset="1" stopColor="#ff0033"/>
        </linearGradient>
      </defs>
    ) : null}
    <path d={HEART} fill={id ? `url(#${id})` : fill} stroke={stroke} strokeWidth={strokeWidth} strokeLinejoin="round"/>
  </svg>
);

export const at = (x: number, y: number): React.CSSProperties => ({position: 'absolute', left: x, top: y, translate: '-50% -50%'});

// Titik sentuh jari ala rekaman layar HP: masuk dari kanan bawah, ketekan di frame tap, lalu ripple.
export const TouchTap: React.FC<{frame: number; clickAt: number; x: number; y: number}> = ({frame, clickAt, x, y}) => {
  const t = frame - clickAt;
  if (frame < clickAt - 12 || t >= 8) return null;
  const move = interpolate(frame, [clickAt - 12, clickAt - 1], [0, 1], {...clamp, easing: out});
  const ripple = interpolate(t, [0, 8], [45, 120], {...clamp, easing: out});
  return (
    <div data-cta-touch="true" style={{
      ...at(x + interpolate(move, [0, 1], [222, 0]), y + interpolate(move, [0, 1], [306, 0])),
      opacity: interpolate(frame, [clickAt - 12, clickAt - 9, clickAt + 4, clickAt + 8], [0, 1, 1, 0], clamp),
    }}>
      {t >= 0 ? (
        <div style={{
          ...at(0, 0), width: 2 * ripple, height: 2 * ripple, borderRadius: '50%',
          border: '5px solid rgba(255,255,255,0.9)', opacity: interpolate(t, [0, 8], [0.9, 0], clamp),
        }}/>
      ) : null}
      <div style={{
        ...at(0, 0), width: 96, height: 96, borderRadius: '50%', scale: interpolate(t, [-1, 0, 2, 4], [1, 0.72, 0.72, 1], clamp),
        background: 'rgba(255,255,255,0.55)', border: '5px solid white', boxShadow: '0 6px 20px rgba(0,0,0,.35)',
      }}/>
    </div>
  );
};

export const MobileLike: React.FC<{frame: number; clickAt: number; end: number; x: number; y: number}> = ({
  frame, clickAt, end, x, y,
}) => {
  const t = frame - clickAt; // < 0 sebelum tap
  const liked = t >= 0;
  const enter = interpolate(frame, [0, 4, 7], [0.4, 1.08, 1], clamp);
  const exit = interpolate(frame, [end - 3, end], [1, 0], clamp);
  const bob = liked ? 0 : Math.sin(frame / 5) * 6;
  // Hati ketekan pas jari nyentuh, lalu mantul lebih besar dari semula sebelum balik normal.
  const heartScale = liked
    ? interpolate(t, [0, 1, 4, 7, 10], [0.8, 0.8, 1.32, 0.94, 1], clamp)
    : interpolate(t, [-2, 0], [1, 0.86], clamp);
  const glow = liked ? interpolate(t, [0, 4, 16], [0, 1, 0.45], clamp) : 0;

  return (
    <div data-cta-like="mobile" style={{position: 'absolute', inset: 0, opacity: exit}}>
      {liked ? (
        <>
          <div data-cta-burst="true" style={{
            ...at(x, y), width: 2 * interpolate(t, [0, 10], [80, 235], {...clamp, easing: out}),
            height: 2 * interpolate(t, [0, 10], [80, 235], {...clamp, easing: out}), borderRadius: '50%',
            border: `${interpolate(t, [0, 10], [14, 2], clamp)}px solid ${RED}`, opacity: interpolate(t, [0, 3, 10], [0, 0.9, 0], clamp),
          }}/>
          {PARTICLES.map((p, i) => {
            const d = interpolate(t, [0, 12], [60, p.dist], {...clamp, easing: out});
            const size = interpolate(t, [0, 12], [44, 20], clamp);
            return (
              <div key={i} style={{
                ...at(x + Math.cos(p.angle) * d, y + Math.sin(p.angle) * d), rotate: `${(p.angle * 180) / Math.PI + 90}deg`,
                opacity: interpolate(t, [0, 2, 9, 14], [0, 1, 1, 0], clamp),
              }}>
                {i % 2 ? (
                  <div style={{width: size * 0.7, height: size * 0.7, borderRadius: '50%', background: PARTICLE_COLORS[i % 3]}}/>
                ) : (
                  <HeartSvg size={size} fill={PARTICLE_COLORS[i % 3]}/>
                )}
              </div>
            );
          })}
          {FLOATERS.map((f, i) => {
            const ft = t - f.delay;
            if (ft < 0) return null;
            return (
              <div key={i} style={{
                ...at(x + f.dx + Math.sin(ft / 3 + i) * 18, y - 60 - interpolate(ft, [0, 16], [0, 300], {...clamp, easing: out})),
                scale: interpolate(ft, [0, 4], [0.4, 1], clamp), rotate: `${Math.sin(ft / 4 + i) * 14}deg`,
                opacity: interpolate(ft, [0, 2, 10, 16], [0, 0.95, 0.8, 0], clamp),
              }}>
                <HeartSvg size={66} fill={i % 2 ? '#ff8fab' : RED}/>
              </div>
            );
          })}
        </>
      ) : null}
      <div style={{...at(x, y + bob), scale: enter}}>
        <div style={{
          width: BUTTON, height: BUTTON, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(16,16,18,0.55)', border: '3px solid rgba(255,255,255,0.22)',
          boxShadow: `0 14px 40px rgba(0,0,0,.35), 0 0 ${70 * glow}px rgba(255,45,85,${0.75 * glow})`,
        }}>
          <div data-cta-heart={liked ? 'filled' : 'outline'} style={{scale: heartScale}}>
            {liked ? <HeartSvg size={ICON} fill={RED} id="fc-like-red"/> : <HeartSvg size={ICON} fill="none" stroke="white" strokeWidth={2}/>}
          </div>
        </div>
        <div style={{
          position: 'absolute', left: '50%', top: BUTTON + 18, translate: '-50% 0', fontFamily: ARIMO, fontWeight: 700,
          fontSize: 58, color: 'white', textShadow: '0 3px 10px rgba(0,0,0,.65)', whiteSpace: 'nowrap',
        }}>Suka</div>
      </div>
      {liked ? (
        <div data-cta-plus-one="true" style={{
          ...at(x + 175, y - 130 - interpolate(t, [2, 18], [0, 90], {...clamp, easing: out})),
          scale: interpolate(t, [2, 5, 7], [0.3, 1.2, 1], clamp), opacity: interpolate(t, [2, 4, 14, 18], [0, 1, 1, 0], clamp),
          fontFamily: ARIMO, fontWeight: 700, fontSize: 76, color: RED, WebkitTextStroke: '8px white', paintOrder: 'stroke fill',
          textShadow: '0 6px 16px rgba(0,0,0,.35)',
        }}>+1</div>
      ) : null}
      <TouchTap frame={frame} clickAt={clickAt} x={x + 68} y={y + 74}/>
    </div>
  );
};
