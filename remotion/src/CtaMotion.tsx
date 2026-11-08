import React from 'react';
import {interpolate, spring} from 'remotion';
import type {CtaStage} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Entrance/exit dibatasi durasi stage supaya ajakan singkat tetap terbaca.
export const motionForStage = (stage: CtaStage, frame: number): React.CSSProperties => {
  const end = Math.max(1, stage.durationInFrames - 1);
  const enter = Math.min(8, Math.max(1, end * .2));
  const exit = Math.min(6, Math.max(1, end * .15));
  const incoming = interpolate(frame, [0, enter], [0, 1], clamp);
  const outgoing = interpolate(frame, [end - exit, end], [1, 0], clamp);
  const settle = spring({frame, fps: 30, config: {damping: 17, stiffness: 240, mass: .65}});
  return {
    opacity: Math.min(incoming, outgoing),
    translate: `0 ${interpolate(incoming, [0, 1], [95, 0]) - (1 - outgoing) * 38}px`,
    scale: (.72 + settle * .28) * (.92 + outgoing * .08),
    filter: `blur(${(1 - incoming) * 5}px)`,
    transformOrigin: '540px 810px',
  };
};

export const ClickRipple: React.FC<{frame: number; at: number}> = ({frame, at}) => {
  const t = frame - at;
  if (t < 0 || t > 19) return null;
  return <div data-cta-ripple="true" style={{position: 'absolute', left: 540, top: 810,
    translate: '-50% -50%', width: 540, height: 540, border: '9px solid #9ed5ff',
    borderRadius: '50%', boxSizing: 'border-box', pointerEvents: 'none',
    opacity: interpolate(t, [0, 3, 19], [.8, .9, 0], clamp),
    scale: interpolate(t, [0, 19], [.75, 1.8], clamp)}}/>;
};

// Trajektori deterministik: render ulang memberi partikel identik.
export const Celebration: React.FC<{frame: number; at: number; thumbs?: boolean}> = ({frame, at, thumbs = false}) => {
  const t = frame - at;
  if (t < 0 || t > 24) return null;
  return <div data-cta-confetti="true" style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
    {Array.from({length: 18}, (_, i) => {
      const a = i * 2.399963;
      const distance = (100 + i % 5 * 34) * t / 12;
      const x = 540 + Math.cos(a) * distance;
      const y = 810 + Math.sin(a) * distance - t * 8 + t * t * .4;
      return <div key={i} style={{position: 'absolute', left: x, top: y,
        opacity: interpolate(t, [0, 3, 19, 24], [0, 1, 1, 0], clamp),
        rotate: `${i * 31 + t * (i % 2 ? 9 : -9)}deg`,
        scale: interpolate(t, [0, 3, 24], [.3, 1, .4], clamp),
        width: thumbs ? 42 : 17, height: thumbs ? 42 : 30,
        color: i % 2 ? '#9ac9ff' : 'white', fontSize: 38,
        background: thumbs ? undefined : ['#ff676b', '#ffcf53', '#83c8ff', '#fff'][i % 4],
        borderRadius: thumbs ? 0 : 4, boxShadow: thumbs ? undefined : '0 2px 6px #0004'}}>
        {thumbs ? <svg width={38} height={38} viewBox="0 0 24 24"><path fill="currentColor" d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg> : null}
      </div>;
    })}
  </div>;
};
