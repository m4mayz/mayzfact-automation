import React from 'react';

// Ikon jempol (path Material Icons "thumb_up", Apache-2.0), viewBox 24x24.
const THUMB = 'M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z';

export const Thumb: React.FC<{size: number; color: string; style?: React.CSSProperties}> = ({size, color, style}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{overflow: 'visible', ...style}}>
    <path d={THUMB} fill={color} />
  </svg>
);

// Kursor tangan putih ber-outline hitam; ujung telunjuk di titik (0,0).
export const Cursor: React.FC<{x: number; y: number; opacity?: number; pressed?: boolean}> = ({x, y, opacity = 1, pressed = false}) => (
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
