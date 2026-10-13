import React from 'react';
import {interpolate, Sequence, staticFile, useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';
import type {Bgm, Sfx} from './types';

// BGM nyala terus (di-loop kalau lebih pendek), pudar di akhir video; SFX tiap momen 1 Sequence.
export const SoundLayer: React.FC<{bgm: Bgm | null; sfx: Sfx[]}> = ({bgm, sfx}) => {
  const {durationInFrames} = useVideoConfig();
  return (
    <>
      {bgm ? (
        <Audio
          src={staticFile(bgm.src)}
          loop
          loopVolumeCurveBehavior="extend"
          volume={(frame) =>
            interpolate(frame, [durationInFrames - bgm.fadeOutFrames, durationInFrames], [bgm.volume, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            })
          }
        />
      ) : null}
      {sfx.map((sound, index) => (
        <Sequence key={index} from={sound.from} layout="none">
          <Audio src={staticFile(sound.src)} volume={sound.volume} />
        </Sequence>
      ))}
    </>
  );
};
