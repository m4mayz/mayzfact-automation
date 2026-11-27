import React from 'react';
import {Video} from '@remotion/media';
import {AbsoluteFill, Img, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {TextBlurs} from './TextBlurs';
import type {Shot} from './types';

const cover: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover'};

// audible: cuma satu salinan klip per shot yang bunyi (layout blur punya 2), sisanya selalu mute.
const Media: React.FC<{shot: Shot; style?: React.CSSProperties; audible?: boolean}> = ({shot, style, audible = false}) => {
  const src = staticFile(shot.src);
  const volume = audible ? shot.volume ?? 0 : 0;
  return shot.kind === 'video' ? (
    // Video dari @remotion/media (rekomendasi Remotion, lebih ringan dari OffthreadVideo); object-fit lewat prop, bukan CSS
    <Video src={src} muted={volume <= 0} volume={volume > 0 ? volume : undefined} objectFit="cover"
      style={{width: '100%', height: '100%', ...style}} />
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

  if (shot.decorative) {
    const offset = shot.loopFrames ? (shot.clipOffset ?? 0) % shot.loopFrames : 0;
    return <AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#172239'}}>
      {shot.generated ? <AbsoluteFill style={{
        background: `radial-gradient(ellipse at ${35 + Math.sin((frame + (shot.clipOffset ?? 0))/50)*20}% 45%, #315778, #151c38 70%)`,
      }}/> : <AbsoluteFill style={{filter: 'blur(10px) brightness(0.78) saturate(0.95)', scale: 1.06}}>
        <Sequence from={-offset} layout="none">
          <Video src={staticFile(shot.src)} muted loop={Boolean(shot.loopFrames)} trimAfter={shot.loopFrames}
            objectFit="cover" style={{width: '100%', height: '100%'}}/>
        </Sequence>
      </AbsoluteFill>}
    </AbsoluteFill>;
  }

  if (shot.layout === 'full') {
    return (
      <AbsoluteFill style={{overflow: 'hidden'}}>
        <Media shot={shot} style={zoomStyle} audible />
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
          <Media shot={shot} style={zoomStyle} audible />
        </div>
      </AbsoluteFill>
      {/* kotak blur pakai koordinat layar penuh; zoom foto di tengah layar, jadi skalanya sama */}
      <TextBlurs boxes={shot.blurs} style={zoomStyle} />
    </AbsoluteFill>
  );
};
