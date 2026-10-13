import React from 'react';
import {AbsoluteFill, Sequence, staticFile, useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';
import {Captions} from './Captions';
import {NumberCard} from './NumberCard';
import {ShotView} from './ShotView';
import {SubjectCard} from './SubjectCard';
import type {TimelineProps} from './types';

export const ShortVideo: React.FC<TimelineProps> = ({audio, shots, photoZoom, countdown = [], captions = []}) => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      {shots.map((shot) => (
        // premountFor: shot dimuat 1 detik sebelum tayang, biar preview Studio nggak kedip hitam.
        <Sequence key={shot.src} from={shot.from} durationInFrames={shot.durationInFrames} premountFor={fps}>
          <ShotView shot={shot} photoZoom={photoZoom} />
        </Sequence>
      ))}
      {countdown.map((card) => (
        // Card opaque di atas shot beat countdown: number card dulu, terus subject card.
        <React.Fragment key={`card-${card.number}-${card.numberFrom}`}>
          <Sequence from={card.numberFrom} durationInFrames={card.numberDuration}>
            <NumberCard number={card.number} durationInFrames={card.numberDuration} />
          </Sequence>
          <Sequence from={card.cardFrom} durationInFrames={card.cardDuration} premountFor={fps}>
            <SubjectCard card={card} />
          </Sequence>
        </React.Fragment>
      ))}
      <Captions captions={captions} />
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};
