import React from 'react';
import {AbsoluteFill, Sequence, staticFile} from 'remotion';
import {Audio} from '@remotion/media';
import {ShotView} from './ShotView';
import type {TimelineProps} from './types';

export const ShortVideo: React.FC<TimelineProps> = ({audio, shots, photoZoom}) => (
  <AbsoluteFill style={{backgroundColor: 'black'}}>
    {shots.map((shot) => (
      <Sequence key={shot.src} from={shot.from} durationInFrames={shot.durationInFrames}>
        <ShotView shot={shot} photoZoom={photoZoom} />
      </Sequence>
    ))}
    {audio ? <Audio src={staticFile(audio)} /> : null}
  </AbsoluteFill>
);
