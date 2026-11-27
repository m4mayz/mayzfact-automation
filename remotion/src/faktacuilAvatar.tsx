import React from 'react';
import {Img} from 'remotion';

// Dipisah biar test SSR bisa nge-mock (Img butuh context composition, import.meta.url nggak ada di CJS).
const src = new URL('../../assets/channels/faktacuil/avatar.png', import.meta.url).href;

export const FaktaCuilAvatar: React.FC<{size: number}> = ({size}) => (
  <Img src={src} alt="" style={{width: size, height: size, borderRadius: '50%', border: '4px solid white', display: 'block'}}/>
);
