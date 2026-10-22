import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';

// Klip pertama habis box subjek masuk dari zoom dekat + blur, nyambung sama box yang nge-zoom keluar (SubjectCard).
export const ZoomIn: React.FC<{durationInFrames: number; children: React.ReactNode}> = ({durationInFrames, children}) => {
  const frame = useCurrentFrame();
  const opts = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)} as const;
  const scale = interpolate(frame, [0, durationInFrames], [1.45, 1], opts);
  const blur = interpolate(frame, [0, durationInFrames], [12, 0], opts);
  // Struktur elemen selalu sama biar video di dalamnya nggak ke-remount (kedip hitam) pas efeknya selesai.
  return (
    <AbsoluteFill style={{transform: `scale(${scale})`, filter: blur > 0.1 ? `blur(${blur}px)` : 'none'}}>
      {children}
    </AbsoluteFill>
  );
};
