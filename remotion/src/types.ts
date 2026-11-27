export type Shot = {
  src: string;
  kind: 'video' | 'photo';
  layout: 'full' | 'blur';
  from: number;
  durationInFrames: number;
  fgHeight?: number;
  blurs?: BlurBox[]; // kotak blur teks, piksel layar
  decorative?: boolean; // CTA: full-screen blur kuat, tanpa foreground tajam
  clipOffset?: number; // frame yang sudah dipakai dari background ini; boleh lebih dari satu loop
  loopFrames?: number;
  generated?: boolean; // fallback warna bergerak kalau belum ada video sebelumnya
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
  blurs?: BlurBox[]; // kotak blur teks, piksel di box 820x820
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

export type BlurBox = {
  x: number;
  y: number;
  w: number;
  h: number;
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

export type CtaStage = {
  kind: 'like' | 'transform' | 'subscribe' | 'comment';
  from: number;
  durationInFrames: number;
  timing: 'word' | 'structure';
  triggerAt?: number;
};

// Stiker FaktaCuil dipisah dari tema top3 biar stiker baru FaktaCuil nggak ikut ke top3 (D-061).
export type StickerTheme =
  | 'volcano' | 'unicorn' | 'honey' | 'puppy' | 'lion' | 'shark' | 'toilet' | 'cat' | 'zebra' | 'wheel' | 'chili';

export type CtaSceneData = {
  theme: Exclude<StickerTheme, 'wheel' | 'chili'>;
  commentText: string;
  from: number;
  durationInFrames: number;
  stages: CtaStage[];
  cues: {kind: CtaStage['kind']; from: number; word: string}[];
  style?: undefined; // top3 nggak pernah pakai gaya FaktaCuil
};

// Scene CTA FaktaCuil v2: tengah (lucky/subscribe) atau akhir (emoji). Lihat D-061.
export type FaktaCuilSceneData = {
  style: 'faktacuil';
  format: 'lucky' | 'subscribe' | 'emoji' | 'emoji_question';
  theme?: StickerTheme;
  emoji?: string;
  emojiSrc?: string; // Lottie Noto dari step timeline; tanpa ini CTA pakai emoji statis
  from: number;
  durationInFrames: number;
  stages: CtaStage[];
  cues: {kind: CtaStage['kind']; from: number; word: string}[];
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
  flashes?: Transition[];
  overlays?: Overlay[];
  emojis?: EmojiOverlay[];
  ctaScene?: CtaSceneData | FaktaCuilSceneData;
  captionStyle?: 'faktacuil';
};
