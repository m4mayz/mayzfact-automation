import React from 'react';
import {AbsoluteFill, Sequence, staticFile, useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';
import {ShotView} from './ShotView';
import type {TimelineProps} from './types';

export const ShortVideo: React.FC<TimelineProps> = ({audio, shots, photoZoom}) => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      {shots.map((shot) => (
        // premountFor: shot dimuat 1 detik sebelum tayang, biar preview Studio nggak kedip hitam.
        <Sequence key={shot.src} from={shot.from} durationInFrames={shot.durationInFrames} premountFor={fps}>
          <ShotView shot={shot} photoZoom={photoZoom} />
        </Sequence>
      ))}
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};
