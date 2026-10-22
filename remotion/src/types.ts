export type Shot = {
  src: string;
  kind: 'video' | 'photo';
  layout: 'full' | 'blur';
  from: number;
  durationInFrames: number;
  fgHeight?: number;
};

export type Caption = {
  text: string;
  from: number;
  durationInFrames: number;
  color: string;
};

export type CountdownCard = {
  number: number;
  label: string;
  numberFrom: number;
  numberAt: number;
  numberDuration: number;
  cardFrom: number;
  cardDuration: number;
  src: string;
  kind: 'video' | 'photo';
  clipOffset: number;
};

export type Sfx = {
  src: string;
  from: number;
  volume: number;
};

export type Bgm = {
  src: string;
  volume: number;
  fadeOutFrames: number;
  from?: number; // segmen BGM (hook / utama); tanpa from = satu BGM sepanjang video (timeline lama)
  durationInFrames?: number;
};

export type Transition = {
  from: number;
  durationInFrames: number;
};

export type OverlayKeyframe = {
  frame: number;
  x: number;
  y: number;
  w: number;
  h: number;
};

export type Overlay = {
  type: 'arrow' | 'circle';
  color: string;
  from: number;
  durationInFrames: number;
  keyframes: OverlayKeyframe[];
};

export type EmojiOverlay = {
  src: string;
  from: number;
  durationInFrames: number;
  x?: number; // pusat horizontal; default 540 (tengah)
};

export type CtaAction = {
  kind: 'like' | 'subscribe';
  from: number;
  durationInFrames: number;
  clickAt: number;
};

export type Intro = {
  durationInFrames: number;
};

// Pakai `type`, bukan `interface`: props Remotion harus cocok sama Record<string, unknown>.
export type TimelineProps = {
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  audio: string;
  photoZoom: number;
  shots: Shot[];
  countdown?: CountdownCard[];
  captions?: Caption[];
  bgm?: Bgm | Bgm[] | null;
  sfx?: Sfx[];
  intro?: Intro | null;
  transitions?: Transition[];
  overlays?: Overlay[];
  emojis?: EmojiOverlay[];
  cta?: CtaAction[];
};
