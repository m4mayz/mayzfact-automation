import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {ShortVideo} from './ShortVideo';
import type {TimelineProps} from './types';

const defaultProps: TimelineProps = {
  fps: 30,
  width: 1080,
  height: 1920,
  durationInFrames: 30,
  audio: '',
  photoZoom: 1.08,
  shots: [],
  countdown: [],
  captions: [],
  bgm: null,
  sfx: [],
  intro: null,
  overlays: [],
  emojis: [],
  cta: [],
};

const calculateMetadata: CalculateMetadataFunction<TimelineProps> = async ({props}) => ({
  durationInFrames: props.durationInFrames,
  fps: props.fps,
  width: props.width,
  height: props.height,
});

export const RemotionRoot: React.FC = () => (
  <Composition
    id="ShortVideo"
    component={ShortVideo}
    durationInFrames={defaultProps.durationInFrames}
    fps={defaultProps.fps}
    width={defaultProps.width}
    height={defaultProps.height}
    defaultProps={defaultProps}
    calculateMetadata={calculateMetadata}
  />
);
