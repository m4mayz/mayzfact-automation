import React from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {Cursor, Thumb} from './Cta';
import {Celebration, ClickRipple, motionForStage} from './CtaMotion';
import {MONTSERRAT} from './fonts';
import {Honey} from './Honey';
import {Unicorn} from './Unicorn';
import type {CtaSceneData, CtaStage} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const shadow = '0 24px 70px rgba(0,0,0,.65)';
const center: React.CSSProperties = {position: 'absolute', left: 540, top: 810, translate: '-50% -50%'};

// SVG buatan sendiri: gunung, lava, asap dan lontaran bergerak dari frame, bukan timer browser.
const Volcano: React.FC<{frame: number}> = ({frame}) => (
  <svg data-volcano="true" width={880} height={840} viewBox="0 0 900 860" style={{overflow: 'visible', filter: 'drop-shadow(0 20px 30px #0008)', translate: `${Math.sin(frame * 1.5) * interpolate(frame, [0, 8, 20], [0, 5, 0], clamp)}px 0`}}>
    <defs>
      <linearGradient id="cta-rock" x2=".8" y2="1"><stop stopColor="#9b5345"/><stop offset="1" stopColor="#322c42"/></linearGradient>
      <linearGradient id="cta-lava" x2="0" y2="1"><stop stopColor="#fff6ae"/><stop offset=".35" stopColor="#ffb02e"/><stop offset="1" stopColor="#ef3e2e"/></linearGradient>
    </defs>
    <ellipse cx={450} cy={735} rx={395} ry={42} fill="#000" opacity={.25}/>
    <g opacity={interpolate(frame, [0, 8], [0, 1], clamp)}>
      {[0, 1, 2, 3, 4, 5, 6].map((i) => {
        const t = ((frame + i * 11) % 60) / 60;
        return <circle key={i} cx={450 + Math.sin(i * 2.4) * 110 * t} cy={405 - t * 300} r={35 + t * 85}
          fill={i % 2 ? '#f7c49d' : '#c4b8c6'} opacity={(1 - t) * .62}/>;
      })}
    </g>
    <path d="M60 720 L310 450 L375 420 L415 375 L490 375 L540 430 L610 470 L845 720 Z" fill="url(#cta-rock)" stroke="#e7a16d" strokeWidth={5} strokeLinejoin="round"/>
    <path d="M415 387 L363 520 L398 510 L342 650 L433 560 L465 470 L500 570 L553 595 L499 430 L490 387 Z" fill="url(#cta-lava)"/>
    <ellipse cx={452} cy={385} rx={52} ry={20} fill="#ffdb67" stroke="#ff5c30" strokeWidth={10}/>
    <path d={`M420 382 Q${392 + Math.sin(frame * .3) * 12} 288 438 210 Q430 290 455 310 Q478 260 480 220 Q${518 + Math.sin(frame * .25) * 14} 300 483 382 Z`}
      fill="url(#cta-lava)" opacity={interpolate(frame, [0, 6], [.2, 1], clamp)}/>
    {Array.from({length: 18}, (_, i) => {
      const t = ((frame * 1.4 + i * 7) % 44) / 44;
      const side = i % 2 ? 1 : -1;
      return <circle key={i} cx={452 + side * t * (120 + (i % 5) * 45)} cy={370 - 560 * t + 420 * t * t}
        r={7 + i % 4 * 3} fill={i % 3 ? '#ff7a27' : '#ffe88a'} opacity={Math.sin(t * Math.PI)}/>;
    })}
  </svg>
);

// Frame eksplisit bikin markup dapat dites tanpa Studio; cuma satu stage dominan pada satu waktu.
export const CtaSceneVisual: React.FC<{scene: CtaSceneData; stage: CtaStage; frame: number}> = ({scene, stage, frame}) => {
  const clickAt = stage.kind === 'subscribe' ? Math.min(Math.max(stage.triggerAt ?? 0, 10), Math.floor(stage.durationInFrames * .45)) : stage.triggerAt ?? 0;
  const pressed = stage.triggerAt !== undefined && frame >= clickAt;
  const pulse = stage.triggerAt === undefined ? 1 : interpolate(frame - clickAt, [0, 3, 8], [1, 1.1, 1], clamp);
  const typed = Math.floor(interpolate(frame, [3, Math.min(21, Math.max(6, stage.durationInFrames - 8))], [0, scene.commentText.length], clamp));
  const done = pressed && frame > clickAt + 6;
  const morph = interpolate(frame, [0, 8], [0, 1], clamp);
  const textStyle: React.CSSProperties = {fontFamily: MONTSERRAT, fontWeight: 800, color: 'white', textAlign: 'center'};
  let transformVisual: React.ReactNode = null;
  if (stage.kind === 'transform') {
    switch (scene.theme) {
      case 'volcano': transformVisual = <Volcano frame={frame}/>; break;
      case 'unicorn': transformVisual = <Unicorn frame={frame}/>; break;
      case 'honey': transformVisual = <Honey frame={frame}/>; break;
      // Kartu kata cuma untuk props legacy yang minta word secara eksplisit.
      case 'word':
        transformVisual = <div style={{...textStyle, width: 840, padding: '110px 36px', boxSizing: 'border-box', border: '8px solid #9adeff', borderRadius: 70,
          background: 'linear-gradient(135deg, #2563eb, #783bd2)', fontSize: Math.min(108, 1050/Math.max(1, scene.label.length)), boxShadow: shadow,
          rotate: `${Math.sin(frame / 12) * 2}deg`}}>{scene.label}</div>;
        break;
      default: {
        const unsupportedTheme: never = scene.theme;
        throw new Error(`Unsupported CTA transform theme: ${String(unsupportedTheme)}`);
      }
    }
  }
  return <div data-cta-stage={stage.kind} style={{position: 'absolute', inset: 0, pointerEvents: 'none', ...motionForStage(stage, frame)}}>
    {stage.kind === 'like' ? <div style={{...center, width: 600, height: 640, ...textStyle, scale: pulse, rotate: `${Math.sin(frame / 10) * 1.3}deg`}}>
      <div style={{margin: '0 auto', width: 540, height: 540, borderRadius: '50%', background: 'radial-gradient(circle at 35% 25%, #639eff, #2563eb 65%, #183dad)', boxShadow: shadow, display: 'grid', placeItems: 'center'}}>
        <Thumb size={320} color="white"/>
      </div>
      <div style={{fontSize: 96, marginTop: 24, textShadow: '0 8px 20px #0009', opacity: interpolate(frame, [2, 7], [0, 1], clamp), translate: `0 ${interpolate(frame, [2, 9], [28, 0], clamp)}px`}}>LIKE</div>
      {stage.triggerAt !== undefined ? <Cursor x={460} y={350 + interpolate(frame - clickAt, [-8, 0], [120, 0], clamp)} opacity={interpolate(frame, [2, 7], [0, 1], clamp)} pressed={pressed}/> : null}
    </div> : null}
    {stage.kind === 'like' && stage.triggerAt !== undefined ? <><ClickRipple frame={frame} at={clickAt}/><Celebration frame={frame} at={clickAt} thumbs/></> : null}
    {stage.kind === 'transform' ? <>
      {frame < 8 ? <div style={{...center, opacity: 1-morph, scale: 1-morph * .55, rotate: `${morph * 22}deg`, width: 540, height: 540, borderRadius: '50%', background: '#2563eb', display: 'grid', placeItems: 'center', boxShadow: shadow}}><Thumb size={320} color="white"/></div> : null}
      <div style={{...center, opacity: morph, scale: interpolate(frame, [0, 5, 10], [.45, 1.06, 1], clamp)}}>
        {transformVisual}
      </div>
    </> : null}
    {stage.kind === 'subscribe' ? <div style={{...center, ...textStyle, width: 860, height: 220, borderRadius: 40,
      background: done ? '#e3262c' : 'white', color: done ? 'white' : '#e3262c',
      display: 'grid', placeItems: 'center', fontSize: 96, boxShadow: shadow, scale: pulse,
      transform: `scaleX(${interpolate(frame, [0, 4, 8], [.2, 1.06, 1], clamp)})`,
      rotate: `${interpolate(frame - clickAt, [0, 2, 4, 6, 10], [0, -3, 3, -1, 0], clamp)}deg`}} aria-label={done ? 'SUBSCRIBED' : 'SUBSCRIBE'}>
      <div style={{whiteSpace: 'nowrap'}}>{(done ? 'SUBSCRIBED' : 'SUBSCRIBE').split('').map((letter, i) => <span key={i} style={{display: 'inline-block', opacity: done ? 1 : interpolate(frame, [i * .45, i * .45 + 3], [0, 1], clamp), translate: `0 ${done ? 0 : interpolate(frame, [i * .45, i * .45 + 5], [18, 0], clamp)}px`}}>{letter}</span>)}</div>
      {stage.triggerAt !== undefined ? <Cursor x={735 + interpolate(frame, [0, clickAt], [110, 0], clamp)} y={165 + interpolate(frame, [0, clickAt], [80, 0], clamp)} opacity={interpolate(frame, [2, 7], [0, 1], clamp)} pressed={pressed}/> : null}
    </div> : null}
    {stage.kind === 'subscribe' && stage.triggerAt !== undefined ? <Celebration frame={frame} at={clickAt}/> : null}
    {stage.kind === 'comment' ? <div style={{...center, ...textStyle, width: 860, minHeight: 400, boxSizing: 'border-box', padding: '58px 40px',
      borderRadius: 48, background: '#f7f9ff', color: '#15233d', boxShadow: shadow, scale: interpolate(frame, [0, 5, 10], [.85, 1.04, 1], clamp)}}>
      <div style={{fontSize: 42, letterSpacing: 7, color: '#56708f', marginBottom: 38}}>COMMENT</div>
      <div style={{fontSize: Math.min(112, 1120/Math.max(1, scene.commentText.length)), overflowWrap: 'anywhere', minHeight: 135}}>{scene.commentText.slice(0, typed)}<span style={{display: 'inline-block', marginLeft: 7, width: 5, height: '1em', verticalAlign: 'middle', background: '#2563eb', opacity: typed < scene.commentText.length || frame % 16 < 8 ? 1 : 0}}/></div>
      <svg width={90} height={55} viewBox="0 0 90 55" style={{position: 'absolute', bottom: -48, left: 90}}><path d="M0 0 H90 L0 55 Z" fill="#f7f9ff"/></svg>
    </div> : null}
  </div>;
};

const Stage: React.FC<{scene: CtaSceneData; stage: CtaStage}> = ({scene, stage}) => {
  const frame = useCurrentFrame();
  return <CtaSceneVisual scene={scene} stage={stage} frame={frame}/>;
};

export const CtaScene: React.FC<{scene: CtaSceneData}> = ({scene}) => (
  <Sequence from={scene.from} durationInFrames={scene.durationInFrames} layout="none">
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 42%, transparent 10%, rgba(4,8,18,.16) 85%)', pointerEvents: 'none'}}/>
    {scene.stages.map((stage) => <Sequence key={`${stage.kind}-${stage.from}`} from={stage.from-scene.from} durationInFrames={stage.durationInFrames} layout="none">
      <Stage scene={scene} stage={stage}/>
    </Sequence>)}
  </Sequence>
);
