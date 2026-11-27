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
    if (file.endsWith(`${path.sep}faktacuilAvatar.tsx`)) {
      mod.exports = {FaktaCuilAvatar: () => require('react').createElement('img', {src: 'avatar.png'})};
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

// Like ala HP (D-070): tombol hati bulat kayak rail kanan Shorts + titik sentuh, bukan pill + kursor mouse.
const beforeClick = markup({format: 'lucky', theme: 'shark'}, 5);
const afterClick = markup({format: 'lucky', theme: 'shark'}, 15);
assert.match(beforeClick, /data-cta-like="mobile"[\s\S]*data-cta-heart="outline"/);
assert.match(beforeClick, /data-cta-touch="true"/);
assert.match(afterClick, /data-cta-like="mobile"[\s\S]*data-cta-heart="filled"/);
assert.match(afterClick, /data-cta-burst="true"/);
assert.match(afterClick, /data-cta-plus-one="true"/);
assert.doesNotMatch(beforeClick + afterClick, /data-cta-pill="like"/, 'pill LIKE desktop udah diganti');
assert.doesNotMatch(beforeClick + afterClick, /M0 0 L0 34 L9 26/, 'kursor panah mouse nggak dipakai buat like');
assert.doesNotMatch(beforeClick + afterClick, /M1 21h4V9H1v12z/, 'ikon jempol nggak boleh muncul lagi');
assert.doesNotMatch(markup({format: 'lucky', theme: 'shark'}, 31), /data-cta-like="mobile"/, 'tombol like hilang setelah LIKED_HOLD');

const chili = {format: 'lucky', theme: 'chili'};
assert.doesNotMatch(markup(chili, 9), /data-sticker="chili"/);
assert.match(markup(chili, 40), /<svg[^>]*data-sticker="chili"/);
assert.match(markup(chili, 40), /<path[^>]*data-chili-body="true"/);
assert.match(markup(chili, 40), /<path[^>]*data-chili-stem="true"/);

// subscribe ala HP (D-070): avatar + @FaktaCuil + pill putih "Subscribe", cue di 50, tap di 62 (50 + 12 = klik Python).
const sub = {format: 'subscribe', theme: 'shark', cues: [...base.cues, {kind: 'subscribe', from: 50, word: 'subscribe'}]};
const sub55 = markup(sub, 55);
assert.match(sub55, /data-cta-subscribe="mobile"[\s\S]*@FaktaCuil[\s\S]*>Subscribe</);
assert.match(sub55, /data-cta-touch="true"/);
assert.match(sub55, /src="avatar.png"/);
assert.doesNotMatch(markup(sub, 61), /Disubscribe/);
assert.match(markup(sub, 62), /Disubscribe/);
assert.match(markup(sub, 64), /data-cta-sub-burst="true"/);
assert.match(markup(sub, 64), /data-cta-sticker="true"/);
assert.doesNotMatch(sub55 + markup(sub, 64), /data-cta-pill=|SUBSCRIBED|viewBox="-8 -4 52 64"/, 'pill + kursor desktop udah diganti');
// Tombol subscribe + titik sentuh harus di atas stiker: di markup, muncul setelah elemen stiker.
const sub64 = markup(sub, 64);
assert.ok(sub64.indexOf('data-cta-subscribe="mobile"') > sub64.indexOf('data-cta-sticker="true"'),
  'tombol subscribe harus dirender setelah stiker');

const wheel = markup({...sub, theme: 'wheel'}, 64);
assert.match(wheel, /data-sticker="wheel"/);
assert.match(wheel, /<circle[^>]*data-wheel-tire="true"/);
assert.match(wheel, /<g[^>]*data-wheel-rim="true"/);
assert.match(wheel, /Disubscribe/);

// emoji: tanpa emojiSrc → statis, pop-in tepat pas klik (cue like = kata "emoji"), ada karakternya,
// nggak ada stiker, dan masih tampil penuh di frame terakhir.
const emo = {format: 'emoji', emoji: '🍯'};
assert.doesNotMatch(markup(emo, 9), /data-cta-emoji/);
assert.match(markup(emo, 12), /data-cta-emoji="static"/);
assert.match(markup(emo, 40), /data-cta-emoji="static"[\s\S]*🍯/);
assert.doesNotMatch(markup(emo, 40), /data-cta-sticker/);
assert.match(markup(emo, 149), /data-cta-emoji="static"[^>]*opacity:\s?1[;"]/);

const question = {format: 'emoji_question', emoji: '🐈‍⬛'};
assert.doesNotMatch(markup(question, 9), /data-cta-emoji/);
assert.match(markup(question, 10), /data-cta-emoji="static"[\s\S]*🐈‍⬛/);
assert.match(markup(question, 149), /data-cta-emoji="static"[^>]*opacity:\s?1[;"]/);
assert.doesNotMatch(markup(question, 149), /data-cta-sticker/);
assert.match(markup(question, 12), /data-cta-emoji="static"[\s\S]*<svg[^>]*aria-label="🐈‍⬛"/);

// format lama udah nggak ada di source
assert.doesNotMatch(fs.readFileSync(path.join(__dirname, '../src/FaktaCuilCta.tsx'), 'utf8'), /escalate|escape|reveal/);
console.log('faktacuil cta: OK');
