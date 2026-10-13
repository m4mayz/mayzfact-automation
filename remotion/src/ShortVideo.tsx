import React from 'react';
import {AbsoluteFill, Sequence, staticFile, useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';
import {Captions} from './Captions';
import {IntroCover, IntroZoom} from './Intro';
import {NumberCard} from './NumberCard';
import {ShotView} from './ShotView';
import {SoundLayer} from './SoundLayer';
import {SubjectCard} from './SubjectCard';
import type {TimelineProps} from './types';

export const ShortVideo: React.FC<TimelineProps> = ({audio, shots, photoZoom, countdown = [], captions = [], bgm = null, sfx = [], intro = null}) => {
  const {fps} = useVideoConfig();
  // Shot yang seluruh durasinya ketutup card countdown nggak dirender, biar videonya nggak tembus di belakang card.
  // Klip shot itu tetap tampil di dalam subject card.
  const coveredByCard = (from: number, duration: number) =>
    countdown.some((card) => card.numberFrom <= from && from + duration <= card.cardFrom + card.cardDuration);
  return (
    <AbsoluteFill style={{backgroundColor: 'black'}}>
      <IntroCover intro={intro}>
      <IntroZoom intro={intro}>
      {shots.filter((shot) => !coveredByCard(shot.from, shot.durationInFrames)).map((shot) => (
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
      </IntroZoom>
      <Captions captions={captions} />
      </IntroCover>
      {audio ? <Audio src={staticFile(audio)} /> : null}
      <SoundLayer bgm={bgm} sfx={sfx} />
    </AbsoluteFill>
  );
};
