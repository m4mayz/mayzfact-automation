import React from 'react';
import type {CtaSceneData} from './types';

// Stiker flat objek transformasi CTA FaktaCuil (viewBox 200x200), outline putih biar kebaca di atas video apa pun.
const Volcano: React.FC<{frame: number}> = ({frame}) => (
  <>
    {[0, 1, 2].map((i) => {
      const t = ((frame + i * 9) % 27) / 27;
      return <circle key={i} cx={86 + i * 14} cy={42 - t * 26} r={11 + t * 8} fill={i === 1 ? '#c9cbd0' : '#a3a8b0'} opacity={1 - t * .6}/>;
    })}
    <path d="M14 182 L78 74 Q100 62 122 74 L186 182 Z" fill="#7a4636"/>
    <path d="M104 66 Q114 68 122 74 L186 182 L126 182 Z" fill="#5c3127"/>
    <path d="M78 76 Q100 60 122 76 L117 96 Q111 86 107 108 Q101 92 95 112 Q89 88 84 98 Z" fill="#ff4d1f"/>
    <path d="M84 72 Q92 36 100 24 Q108 36 116 72 Q100 64 84 72 Z" fill="#ffb02e"/>
    {[0, 1, 2, 3].map((i) => {
      const t = ((frame * 1.3 + i * 8) % 30) / 30;
      const side = i % 2 ? 1 : -1;
      return <circle key={i} cx={100 + side * t * (34 + i * 8)} cy={46 - 70 * t + 90 * t * t} r={6 - i % 2 * 2}
        fill={i % 2 ? '#ff7a27' : '#ffd84a'} opacity={Math.sin(t * Math.PI)}/>;
    })}
  </>
);

const Honey: React.FC = () => (
  <>
    <ellipse cx={100} cy={126} rx={64} ry={56} fill="#f2a516"/>
    <ellipse cx={74} cy={112} rx={12} ry={22} fill="#fff" opacity={.35}/>
    <rect x={44} y={118} width={112} height={22} rx={8} fill="#a8560f"/>
    <rect x={62} y={58} width={76} height={20} rx={10} fill="#d9840a"/>
    <path d="M56 66 Q100 50 144 66 L144 80 Q136 100 128 82 Q120 108 110 84 Q100 96 92 82 Q82 104 74 82 Q66 94 56 80 Z" fill="#ffc93c"/>
    <rect x={118} y={14} width={12} height={70} rx={6} fill="#8a5a2b" transform="rotate(24 124 49)"/>
  </>
);

const Unicorn: React.FC = () => (
  <>
    <path d="M78 90 Q52 96 46 124 Q40 150 52 178 Q34 160 32 130 Q32 96 62 80 Q76 72 92 74 Z" fill="#9b6bff"/>
    <path d="M84 88 Q62 98 60 124 Q58 150 68 176 Q50 156 50 128 Q50 100 72 84 Z" fill="#ff7ac8"/>
    <path d="M66 182 Q58 124 82 94 Q100 72 126 74 Q150 76 162 98 L172 116 Q174 128 160 130 L140 128 Q128 132 124 146 L120 182 Z" fill="#fff" stroke="#e4dcf2" strokeWidth={4}/>
    <path d="M104 78 L110 54 L120 76 Z" fill="#fff" stroke="#e4dcf2" strokeWidth={4} strokeLinejoin="round"/>
    <path d="M120 78 L144 22 L134 82 Z" fill="#ffd23f"/>
    <path d="M124 66 L138 60 M127 52 L140 46" stroke="#e8a92a" strokeWidth={4} strokeLinecap="round"/>
    <circle cx={132} cy={100} r={7} fill="#3a2b5f"/>
    <circle cx={135} cy={97} r={2.5} fill="#fff"/>
    <circle cx={160} cy={118} r={3} fill="#c9b8e0"/>
    <circle cx={126} cy={118} r={8} fill="#ffb3d9" opacity={.8}/>
  </>
);

const Puppy: React.FC = () => (
  <>
    <ellipse cx={46} cy={96} rx={22} ry={46} fill="#8a5a3b" transform="rotate(18 46 96)"/>
    <ellipse cx={154} cy={96} rx={22} ry={46} fill="#8a5a3b" transform="rotate(-18 154 96)"/>
    <circle cx={100} cy={106} r={62} fill="#e9b37a"/>
    <ellipse cx={122} cy={96} rx={20} ry={18} fill="#c98b55"/>
    <ellipse cx={100} cy={132} rx={34} ry={26} fill="#fff1df"/>
    <circle cx={80} cy={98} r={9} fill="#2b1d14"/>
    <circle cx={120} cy={98} r={9} fill="#2b1d14"/>
    <circle cx={83} cy={95} r={3} fill="#fff"/>
    <circle cx={123} cy={95} r={3} fill="#fff"/>
    <ellipse cx={100} cy={120} rx={12} ry={8} fill="#2b1d14"/>
    <path d="M100 128 Q100 140 90 142 M100 128 Q100 140 110 142" stroke="#2b1d14" strokeWidth={3.5} fill="none" strokeLinecap="round"/>
    <path d="M94 142 Q100 160 106 142 Z" fill="#ff6f8a"/>
  </>
);

const Lion: React.FC = () => (
  <>
    {Array.from({length: 12}, (_, i) => {
      const a = (i / 12) * Math.PI * 2;
      return <circle key={i} cx={100 + Math.cos(a) * 64} cy={104 + Math.sin(a) * 64} r={26} fill={i % 2 ? '#d8661a' : '#e98a2a'}/>;
    })}
    <circle cx={100} cy={104} r={66} fill="#d8661a"/>
    <circle cx={64} cy={64} r={15} fill="#ffc04d"/>
    <circle cx={136} cy={64} r={15} fill="#ffc04d"/>
    <circle cx={64} cy={64} r={7} fill="#e8963a"/>
    <circle cx={136} cy={64} r={7} fill="#e8963a"/>
    <circle cx={100} cy={108} r={50} fill="#ffc04d"/>
    <circle cx={83} cy={100} r={7} fill="#3a2412"/>
    <circle cx={117} cy={100} r={7} fill="#3a2412"/>
    <ellipse cx={100} cy={128} rx={25} ry={18} fill="#fff0c8"/>
    <path d="M90 114 L110 114 L100 126 Z" fill="#6b3a1f" strokeLinejoin="round"/>
    <path d="M100 126 Q100 136 90 138 M100 126 Q100 136 110 138" stroke="#6b3a1f" strokeWidth={3.5} fill="none" strokeLinecap="round"/>
  </>
);

const Shark: React.FC = () => (
  <>
    <path d="M26 110 L4 76 L16 110 L4 144 Z" fill="#6b8196"/>
    <path d="M92 82 L112 38 L126 84 Z" fill="#6b8196"/>
    <path d="M18 110 Q60 70 130 76 Q172 82 190 110 Q172 138 130 142 Q60 150 18 110 Z" fill="#7d93a8"/>
    <path d="M40 116 Q92 142 176 122 Q156 140 124 142 Q72 146 40 116 Z" fill="#eef3f7"/>
    <path d="M100 124 L82 150 L116 132 Z" fill="#6b8196"/>
    <circle cx={156} cy={100} r={6} fill="#1b2530"/>
    <path d="M128 96 Q124 106 128 116 M120 96 Q116 106 120 116" stroke="#5c7085" strokeWidth={3} fill="none" strokeLinecap="round"/>
    <path d="M148 124 Q166 128 182 118" stroke="#1b2530" strokeWidth={3} fill="none" strokeLinecap="round"/>
    <path d="M154 125 L157 131 L160 126 M164 125 L167 131 L170 124" fill="#fff" stroke="#fff" strokeWidth={2}/>
  </>
);

const Toilet: React.FC<{frame: number}> = ({frame}) => {
  const ripple = (frame % 24) / 24;
  return (
    <>
      <path d="M6 46 H194 L186 178 Q100 192 14 178 Z" fill="#e3ebf0" stroke="#c6d5dd" strokeWidth={4}/>
      <g transform="rotate(-5 46 40)"><rect x={18} y={22} width={124} height={34} rx={12} fill="#cddbe3" stroke="#a9bcc7" strokeWidth={3}/><rect x={30} y={31} width={8} height={16} rx={3} fill="#a9bcc7"/><rect x={52} y={31} width={8} height={16} rx={3} fill="#a9bcc7"/><rect x={74} y={31} width={8} height={16} rx={3} fill="#a9bcc7"/><rect x={96} y={31} width={8} height={16} rx={3} fill="#a9bcc7"/><rect x={118} y={31} width={8} height={16} rx={3} fill="#a9bcc7"/></g>
      <g transform="rotate(5 46 158)"><rect x={18} y={142} width={124} height={34} rx={12} fill="#cddbe3" stroke="#a9bcc7" strokeWidth={3}/><rect x={30} y={151} width={8} height={16} rx={3} fill="#a9bcc7"/><rect x={52} y={151} width={8} height={16} rx={3} fill="#a9bcc7"/><rect x={74} y={151} width={8} height={16} rx={3} fill="#a9bcc7"/><rect x={96} y={151} width={8} height={16} rx={3} fill="#a9bcc7"/><rect x={118} y={151} width={8} height={16} rx={3} fill="#a9bcc7"/></g>
      <path d="M24 70 H156 Q176 70 176 100 Q176 130 156 130 H24 Q14 130 14 100 Q14 70 24 70 Z" fill="#fbfdfe" stroke="#b9cbd5" strokeWidth={4}/>
      <path d="M30 78 H150 Q166 78 166 100 Q166 122 150 122 H30 Q22 122 22 100 Q22 78 30 78 Z" fill="#dbe6ec"/>
      <path d="M30 86 H120 Q132 86 132 100 Q132 118 118 118 H30 Q24 118 24 100 Q24 86 30 86 Z" fill="#8fd6f5" stroke="#e7f8ff" strokeWidth={3}/>
      <ellipse cx={70} cy={100} rx={10 + ripple * 22} ry={4 + ripple * 9} fill="none" stroke="#dff3ff" strokeWidth={2.5} opacity={1 - ripple}/>
      <ellipse cx={136} cy={100} rx={8} ry={6} fill="#3f7593" stroke="#dff3ff" strokeWidth={2}/>
      <path d="M156 68 Q192 72 192 100 Q192 128 156 132 L156 118 Q174 114 174 100 Q174 86 156 82 Z" fill="#f4fafc" stroke="#b9cbd5" strokeWidth={4}/>
      <path d="M156 82 Q176 88 176 100 Q176 112 156 118" fill="none" stroke="#a9bcc7" strokeWidth={3}/>
      {[0, 1, 2].map((i) => {
        const t = ((frame + i * 8) % 24) / 24;
        return <circle key={i} cx={44 + t * 96} cy={100 - 4 - (i - 1) * 4} r={3.5 - (i % 2)} fill="#dff3ff" opacity={Math.sin(t * Math.PI) * .9}/>;
      })}
    </>
  );
};

export const Sticker: React.FC<{theme: CtaSceneData['theme']; frame: number; size: number}> = ({theme, frame, size}) => {
  let body: React.ReactNode;
  switch (theme) {
    case 'volcano': body = <Volcano frame={frame}/>; break;
    case 'honey': body = <Honey/>; break;
    case 'unicorn': body = <Unicorn/>; break;
    case 'puppy': body = <Puppy/>; break;
    case 'lion': body = <Lion/>; break;
    case 'shark': body = <Shark/>; break;
    case 'toilet': body = <Toilet frame={frame}/>; break;
    default: {
      const unsupported: never = theme;
      throw new Error(`Unsupported FaktaCuil sticker: ${String(unsupported)}`);
    }
  }
  return (
    <svg data-sticker={theme} width={size} height={size} viewBox="0 0 200 200"
      style={{overflow: 'visible', filter: 'drop-shadow(0 10px 18px rgba(0,0,0,.45))'}}>
      <defs>
        <filter id="fc-sticker-outline" x="-15%" y="-15%" width="130%" height="130%">
          <feMorphology in="SourceAlpha" operator="dilate" radius={6} result="grown"/>
          <feFlood floodColor="#fff"/>
          <feComposite in2="grown" operator="in" result="outline"/>
          <feMerge><feMergeNode in="outline"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <g filter="url(#fc-sticker-outline)">{body}</g>
    </svg>
  );
};
