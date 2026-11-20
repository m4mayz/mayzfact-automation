// Tes markup nyata FaktaCuilCta v2: lucky, subscribe, emoji (tanpa format lama).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const {transformSync} = require('esbuild');

// lottie-web butuh DOM; di SSR cukup komponen kosong.
const load = Module._load;
Module._load = function (request, parent, isMain) {
  if (request === '@remotion/lottie') {
    return {Lottie: () => null};
  }
  return load.apply(this, arguments);
};

for (const ext of ['.ts', '.tsx']) {
  require.extensions[ext] = (mod, file) => {
    if (file.endsWith(`${path.sep}fonts.ts`)) {
      mod.exports = {MONTSERRAT: 'Montserrat', ANTON: 'Anton'};
      return;
    }
    mod._compile(transformSync(fs.readFileSync(file, 'utf8'), {loader: ext === '.tsx' ? 'tsx' : 'ts', format: 'cjs'}).code, file);
  };
}
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const {FaktaCuilCtaVisual} = require('../src/FaktaCuilCta.tsx');

const base = {
  style: 'faktacuil', from: 0, durationInFrames: 150,
  stages: [{kind: 'like', from: 0, durationInFrames: 60, timing: 'word', triggerAt: 10}],
  cues: [{kind: 'like', from: 10, word: 'like'}],
};
const markup = (scene, frame) => renderToStaticMarkup(
  React.createElement(FaktaCuilCtaVisual, {scene: {...base, ...scene}, frame}));

// lucky: stiker tampil di frame 40, format ikut scene, posisi akhir top 1030px.
const lucky = markup({format: 'lucky', theme: 'shark'}, 40);
assert.match(lucky, /data-cta-sticker="true" data-cta-format="lucky"/);
assert.match(lucky, /top:\s?1030px/);
assert.doesNotMatch(lucky, /data-cta-emoji/);

// subscribe: cue subscribe di 50 → pill SUBSCRIBE di 55, SUBSCRIBED di 62 (50 + 12 = klik Python), stiker tetap ada.
const sub = {format: 'subscribe', theme: 'shark', cues: [...base.cues, {kind: 'subscribe', from: 50, word: 'subscribe'}]};
assert.match(markup(sub, 55), /data-cta-pill="subscribe"[^>]*>[\s\S]*SUBSCRIBE/);
assert.match(markup(sub, 61), /data-cta-pill="subscribe"[^>]*>[\s\S]*SUBSCRIBE/);
assert.doesNotMatch(markup(sub, 61), /SUBSCRIBED/);
assert.match(markup(sub, 62), /SUBSCRIBED/);
assert.match(markup(sub, 64), /data-cta-sticker="true"/);

// emoji: tanpa emojiSrc → statis, pop-in tepat pas klik (cue like = kata "emoji"), ada karakternya,
// nggak ada stiker, dan masih tampil penuh di frame terakhir.
const emo = {format: 'emoji', emoji: '🍯'};
assert.doesNotMatch(markup(emo, 9), /data-cta-emoji/);
assert.match(markup(emo, 12), /data-cta-emoji="static"/);
assert.match(markup(emo, 40), /data-cta-emoji="static"[\s\S]*🍯/);
assert.doesNotMatch(markup(emo, 40), /data-cta-sticker/);
assert.match(markup(emo, 149), /data-cta-emoji="static"[^>]*opacity:\s?1[;"]/);

// format lama udah nggak ada di source
assert.doesNotMatch(fs.readFileSync(path.join(__dirname, '../src/FaktaCuilCta.tsx'), 'utf8'), /escalate|escape|reveal/);
console.log('faktacuil cta: OK');
