import React from 'react';
import {Video} from '@remotion/media';
import {AbsoluteFill} from 'remotion';
import burst from './assets/number-burst.mp4';

// Ledakan energi biru di belakang angka countdown (gantiin api SVG). Efek pertama dari pack VFX green screen
// youtube.com/shorts/jTju4qze75E, di-key ke background hitam (ffmpeg chromakey + despill), 34 frame.
// Blend `screen` bikin hitamnya ilang di atas background kartu, yang kelihatan cuma energinya.
export const BURST_FRAMES = 34;
const SIZE = 2000; // ledakan selebar layar kayak api di source

export const NumberFlame: React.FC = () => (
  <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', pointerEvents: 'none'}}>
    <Video src={burst} muted objectFit="cover" style={{width: SIZE, height: SIZE, mixBlendMode: 'screen'}} />
  </AbsoluteFill>
);
