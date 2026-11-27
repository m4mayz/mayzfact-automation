import React, {useEffect, useMemo, useState} from 'react';
import {
  continueRender,
  delayRender,
  interpolate,
  interpolateColors,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {ARIMO, arimoReady} from './fonts';
import type {Caption} from './types';

// FaktaCuil "box" (D-069): kata muncul satu per satu dari tengah, kata sebelumnya geser halus ke posisi layout final.
const FONT_SIZE = 45; // 70% ukuran awal (Akmal: kiri-kanan jangan terlalu lebar)
const FIT_SIZES = [45, 41, 37, 33]; // turun kalau 1 tampilan butuh lebih dari 2 baris
const PAD_X = 13;
const PAD_Y = 4;
const BORDER = 2;
const LINE_HEIGHT = 1.2;
const boxHeight = (size: number) => Math.round(size * LINE_HEIGHT) + 2 * (PAD_Y + BORDER);
const GAP_X = 11;
const GAP_Y = 13;
const MAX_LINE = 630;
const SHIFT_FRAMES = 8;
const HIGHLIGHT_OUT_FRAMES = 4;
const DARK = '#1f1f23';
const LIME = '#a3e635';

// Lebar teks di FONT_SIZE; lebar kotak dihitung per ukuran font di fitLayout.
const measure = (texts: string[]): number[] => {
  const ctx = document.createElement('canvas').getContext('2d');
  if (!ctx) return texts.map((t) => t.length * FONT_SIZE * 0.6);
  ctx.font = `700 ${FONT_SIZE}px ${ARIMO}`;
  return texts.map((t) => ctx.measureText(t).width);
};

// Pecah baris kayak flex-wrap: kata masuk baris yang sama selama lebarnya masih <= MAX_LINE.
const breakLines = (widths: number[]): number[][] => {
  const lines: number[][] = [];
  let used = 0;
  widths.forEach((w, i) => {
    const line = lines[lines.length - 1];
    if (line && used + GAP_X + w <= MAX_LINE) {
      line.push(i);
      used += GAP_X + w;
    } else {
      lines.push([i]);
      used = w;
    }
  });
  return lines;
};

const fitLayout = (textWidths: number[]) => {
  for (const size of FIT_SIZES) {
    const widths = textWidths.map((t) => Math.ceil((t * size) / FONT_SIZE) + 2 * (PAD_X + BORDER));
    const lines = breakLines(widths);
    if (lines.length <= 2 || size === FIT_SIZES[FIT_SIZES.length - 1]) return {size, widths, lines};
  }
  throw new Error('FIT_SIZES kosong');
};

const BoxGroup: React.FC<{words: Caption[]; textWidths: number[]; start: number}> = ({words, textWidths, start}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {size, widths, lines} = useMemo(() => fitLayout(textWidths), [textWidths]);
  const boxH = boxHeight(size);
  const since = (i: number) => start + frame - words[i].from;
  const ease = (f: number, frames: number) => (f < 0 ? 0 : spring({frame: f, fps, config: {damping: 200}, durationInFrames: frames}));
  const placed = lines.flatMap((line, l) => {
    // Baris yang belum kelihatan nggak ikut dihitung, jadi blok tetap di tengah; tiap baris baru geser semuanya ke atas.
    const laterLines = lines.slice(l + 1).reduce((sum, next) => sum + ease(since(next[0]), SHIFT_FRAMES), 0);
    const y = (l / 2 - laterLines / 2) * (boxH + GAP_Y);
    let before = 0;
    return line.map((i, j) => {
      // Posisi pas kata ini baru muncul: nempel di kanan kata sebelumnya, lalu baris geser setengah lebarnya ke kiri.
      const self = j > 0 ? ((widths[i] + GAP_X) / 2) * (1 - ease(since(i), SHIFT_FRAMES)) : 0;
      const shift = line.slice(j + 1).reduce((sum, k) => sum + ((widths[k] + GAP_X) / 2) * ease(since(k), SHIFT_FRAMES), 0);
      const x = before / 2 + self - shift;
      before += widths[i] + GAP_X;
      return {i, x, y};
    });
  });
  return (
    <div style={{position: 'absolute', top: '75%', left: '50%', width: 0, height: 0}}>
      {placed.map(({i, x, y}) => {
        const f = since(i);
        if (f < 0) return null;
        const pop = spring({frame: f, fps, config: {damping: 14, stiffness: 300, mass: 0.5}});
        const active = i + 1 < words.length ? 1 - ease(since(i + 1), HIGHLIGHT_OUT_FRAMES) : 1;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: widths[i],
              height: boxH,
              boxSizing: 'border-box',
              zIndex: active > 0.5 ? 1 : 0,
              transform: `translate(-50%, -50%) translate(${x}px, ${y}px) rotate(${-4 * active}deg) scale(${pop * (1 + 0.06 * active)})`,
              opacity: interpolate(f, [0, 2], [0, 1], {extrapolateRight: 'clamp'}),
              background: interpolateColors(active, [0, 1], [DARK, LIME]),
              border: `${BORDER}px solid ${interpolateColors(active, [0, 1], ['#a1a1aa', '#ecfccb'])}`,
              borderRadius: 8,
              padding: `${PAD_Y}px ${PAD_X}px`,
              boxShadow: `4px 4px 0 rgba(0,0,0,0.9), 0 0 ${21 * active}px rgba(163,230,53,${0.8 * active})`,
              fontFamily: ARIMO,
              fontWeight: 700,
              fontSize: size,
              lineHeight: LINE_HEIGHT,
              textAlign: 'center',
              color: interpolateColors(active, [0, 1], [words[i].color, '#14290a']),
              WebkitTextStroke: `${4 * (1 - active)}px black`,
              paintOrder: 'stroke fill',
              whiteSpace: 'nowrap',
            }}
          >
            {words[i].text}
          </div>
        );
      })}
    </div>
  );
};

export const BoxCaptions: React.FC<{captions: Caption[]}> = ({captions}) => {
  const [handle] = useState(() => delayRender('Nunggu font Arimo buat ngukur caption box'));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    arimoReady().then(() => {
      setReady(true);
      continueRender(handle);
    });
  }, [handle]);
  const widths = useMemo(() => (ready ? measure(captions.map((c) => c.text)) : []), [ready, captions]);
  if (!ready) return null;
  const groups: number[][] = [];
  captions.forEach((caption, i) => {
    const last = groups[groups.length - 1];
    if (last && caption.group !== undefined && captions[last[0]].group === caption.group) last.push(i);
    else groups.push([i]);
  });
  return (
    <>
      {groups.map((idx) => {
        const words = idx.map((i) => captions[i]);
        const start = words[0].from;
        const end = Math.max(...words.map((word) => word.from + word.durationInFrames));
        return (
          <Sequence key={idx[0]} from={start} durationInFrames={Math.max(1, end - start)} layout="none">
            <BoxGroup words={words} textWidths={idx.map((i) => widths[i])} start={start} />
          </Sequence>
        );
      })}
    </>
  );
};
