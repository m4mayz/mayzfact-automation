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
  bgm?: Bgm | null;
  sfx?: Sfx[];
};
