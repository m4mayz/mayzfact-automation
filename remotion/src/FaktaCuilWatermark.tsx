import React from 'react';
import {Img} from 'remotion';
import {FREDOKA} from './fonts';

const logo = new URL('../../assets/channels/faktacuil/watermark.png', import.meta.url).href;

export const FaktaCuilWatermark: React.FC = () => (
  <div style={{
    position: 'absolute',
    top: '10.625%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    opacity: 0.64,
    color: '#fff',
    fontFamily: FREDOKA,
    fontWeight: 600,
    fontSize: 48,
    lineHeight: 1,
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
  }}>
    <Img src={logo} alt="" style={{width: 60, height: 60}} />
    <span>FaktaCuil</span>
  </div>
);