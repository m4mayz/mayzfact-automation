import React from 'react';
import {interpolate, Sequence, staticFile, useVideoConfig} from 'remotion';
import {Audio} from '@remotion/media';
import type {Bgm, Sfx} from './types';

// Segmen BGM di-loop kalau lebih pendek, pudar di ujung segmennya; SFX tiap momen 1 Sequence.
// Timeline lama: bgm satu objek tanpa from = satu BGM sepanjang video.
const BgmTrack: React.FC<{bgm: Bgm; duration: number}> = ({bgm, duration}) => (
  <Audio
    src={staticFile(bgm.src)}
    loop
    loopVolumeCurveBehavior="extend"
    volume={(frame) =>
      interpolate(frame, [duration - bgm.fadeOutFrames, duration], [bgm.volume, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      })
    }
  />
);

export const SoundLayer: React.FC<{bgm: Bgm | Bgm[] | null; sfx: Sfx[]}> = ({bgm, sfx}) => {
  const {durationInFrames} = useVideoConfig();
  const tracks = bgm === null ? [] : Array.isArray(bgm) ? bgm : [bgm];
  return (
    <>
      {tracks.map((track, index) => {
        const from = track.from ?? 0;
        const duration = track.durationInFrames ?? durationInFrames - from;
        return (
          <Sequence key={`bgm-${index}`} from={from} durationInFrames={duration} layout="none">
            <BgmTrack bgm={track} duration={duration} />
          </Sequence>
        );
      })}
      {sfx.map((sound, index) => (
        <Sequence key={index} from={sound.from} layout="none">
          <Audio src={staticFile(sound.src)} volume={sound.volume} />
        </Sequence>
      ))}
    </>
  );
};
