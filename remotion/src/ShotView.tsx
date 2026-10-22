import React from 'react';
import {Video} from '@remotion/media';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {TextBlurs} from './TextBlurs';
import type {Shot} from './types';

const cover: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover'};

const Media: React.FC<{shot: Shot; style?: React.CSSProperties}> = ({shot, style}) => {
  const src = staticFile(shot.src);
  return shot.kind === 'video' ? (
    // Video dari @remotion/media (rekomendasi Remotion, lebih ringan dari OffthreadVideo); object-fit lewat prop, bukan CSS
    <Video src={src} muted objectFit="cover" style={{width: '100%', height: '100%', ...style}} />
  ) : (
    <Img src={src} style={{...cover, ...style}} />
  );
};

export const ShotView: React.FC<{shot: Shot; photoZoom: number}> = ({shot, photoZoom}) => {
  const frame = useCurrentFrame();
  const zoom =
    shot.kind === 'photo'
      ? interpolate(frame, [0, Math.max(1, shot.durationInFrames - 1)], [1, photoZoom], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
      : 1;
  const zoomStyle: React.CSSProperties = {transform: `scale(${zoom})`};

  if (shot.layout === 'full') {
    return (
      <AbsoluteFill style={{overflow: 'hidden'}}>
        <Media shot={shot} style={zoomStyle} />
        <TextBlurs boxes={shot.blurs} style={zoomStyle} />
      </AbsoluteFill>
    );
  }

  // Layout blur: background media yang sama di-blur (diam), foreground kotak setinggi fgHeight di tengah.
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <AbsoluteFill>
        <Media shot={shot} style={{filter: 'blur(40px) brightness(0.7)', transform: 'scale(1.15)'}} />
      </AbsoluteFill>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{width: '100%', height: shot.fgHeight ?? 960, overflow: 'hidden'}}>
          <Media shot={shot} style={zoomStyle} />
        </div>
      </AbsoluteFill>
      {/* kotak blur pakai koordinat layar penuh; zoom foto di tengah layar, jadi skalanya sama */}
      <TextBlurs boxes={shot.blurs} style={zoomStyle} />
    </AbsoluteFill>
  );
};
