import React from 'react';
import type {BlurBox} from './types';

// Kotak blur di atas teks yang kebaca di klip (watermark, username, subtitle bawaan). Posisi dari mayzfact/textblur.py.
export const TextBlurs: React.FC<{boxes?: BlurBox[]; style?: React.CSSProperties}> = ({boxes = [], style}) => {
  if (boxes.length === 0) {
    return null;
  }
  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', ...style}}>
      {boxes.map((box, index) => (
        <div
          key={index}
          style={{
            position: 'absolute',
            left: box.x,
            top: box.y,
            width: box.w,
            height: box.h,
            borderRadius: 10,
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            backgroundColor: 'rgba(0, 0, 0, 0.08)',
          }}
        />
      ))}
    </div>
  );
};
