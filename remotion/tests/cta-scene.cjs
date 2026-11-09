// Tes markup nyata tanpa browser; animasi menerima frame eksplisit supaya bisa diulang.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {transformSync} = require('esbuild');
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
const {CtaSceneVisual} = require('../src/CtaScene.tsx');
const scene = {theme: 'volcano', commentText: 'ERUPTED', label: '', from: 0, durationInFrames: 300, stages: [], cues: []};
function markup(kind, frame, options = {}) {
  return renderToStaticMarkup(React.createElement(CtaSceneVisual, {scene: {...scene, ...options},
    stage: {kind, from: 0, durationInFrames: 90, triggerAt: 15, timing: 'word'}, frame}));
}
const like = markup('like', 10);
assert.match(like, /data-cta-stage="like"/);
assert.match(like, /LIKE/);
assert.doesNotMatch(like, /data-volcano|ERUPTED|SUBSCRIBE/);
const transform = markup('transform', 25);
assert.match(transform, /data-volcano="true"/);
assert.notEqual(transform, markup('transform', 26));
assert.equal(transform, markup('transform', 25));
const sub = markup('subscribe', 5);
assert.match(sub, /SUBSCRIBE/);
assert.doesNotMatch(sub, /data-volcano|ERUPTED/);
const comment = markup('comment', 25);
assert.match(comment, /ERUPTED/);
assert.match(comment, /COMMENT/);
assert.doesNotMatch(comment, /data-volcano|SUBSCRIBE/);
const word = markup('transform', 25, {theme: 'word', label: 'CRYSTAL'});
assert.match(word, /CRYSTAL/);
assert.doesNotMatch(word, /data-volcano/);
// Semua stage harus masuk/keluar halus, bukan muncul penuh pada frame pertama.
function rootOpacity(html) {
  const style = html.match(/^<div[^>]*style="([^"]+)"/)[1];
  const match = style.match(/(?:^|;)opacity:([\d.]+)/);
  return match ? Number(match[1]) : 1;
}
for (const kind of ['like', 'transform', 'subscribe', 'comment']) {
  assert.equal(rootOpacity(markup(kind, 0)), 0, `${kind} must enter from invisible`);
  assert.ok(rootOpacity(markup(kind, 18)) > .9, `${kind} must reach readable hold`);
  assert.ok(rootOpacity(markup(kind, 89)) < .05, `${kind} must exit before stage ends`);
}
assert.doesNotMatch(markup('comment', 1), /ERUPTED/, 'Comment must type in, not appear whole');
assert.match(markup('comment', 30), /ERUPTED/, 'Comment must finish typing');
assert.match(markup('like', 20), /data-cta-ripple/, 'Like click must have ripple');
assert.match(markup('subscribe', 25), /data-cta-confetti/, 'Subscribe click must have confetti');
const shotSource = fs.readFileSync(path.join(__dirname, '../src/ShotView.tsx'), 'utf8');
const decorative = shotSource.split('if (shot.decorative)')[1].split("if (shot.layout === 'full')")[0];
const blur = Number(decorative.match(/blur\(([\d.]+)px\)/)[1]);
const brightness = Number(decorative.match(/brightness\(([\d.]+)\)/)[1]);
assert.ok(blur <= 12, `Glass blur must retain visible footage, got ${blur}px`);
assert.ok(brightness >= 0.7, `Glass footage must remain visible, got brightness ${brightness}`);
const unicornOptions = {theme: 'unicorn', label: 'NOT A WORD CARD', commentText: 'MAGIC'};
const unicorn = markup('transform', 25, unicornOptions);
assert.match(unicorn, /<svg[^>]*data-unicorn="true"[^>]*width="880"[^>]*height="840"/);
for (const part of ['horn', 'mane', 'head', 'sparkles']) {
  assert.match(unicorn, new RegExp(`data-unicorn-${part}="true"`));
}
assert.doesNotMatch(unicorn, /NOT A WORD CARD|data-volcano|<text/);
assert.notEqual(unicorn, markup('transform', 26, unicornOptions));
assert.equal(unicorn, markup('transform', 25, unicornOptions));
// Kepala dan sparkle masing-masing bergerak, bukan sekadar wrapper yang bergoyang.
for (const part of ['head', 'sparkles']) {
  const partTag = new RegExp(`<g[^>]*data-unicorn-${part}="true"[^>]*>`);
  assert.notEqual(unicorn.match(partTag)[0], markup('transform', 26, unicornOptions).match(partTag)[0]);
}
assert.equal(rootOpacity(markup('transform', 0, unicornOptions)), 0);
assert.ok(rootOpacity(markup('transform', 18, unicornOptions)) > .9);
assert.ok(rootOpacity(markup('transform', 89, unicornOptions)) < .05);
const thumbMarkup = renderToStaticMarkup(React.createElement(require('../src/Cta.tsx').Thumb, {size: 320, color: 'white'}));
assert.ok(markup('transform', 0, unicornOptions).includes(thumbMarkup), 'Like thumb must remain during morph entrance');
assert.ok(!unicorn.includes(thumbMarkup), 'Like thumb must disappear once unicorn is fully transformed');
assert.equal(markup('like', 20, unicornOptions), markup('like', 20, {...unicornOptions, theme: 'word'}));
assert.equal(markup('subscribe', 25, unicornOptions), markup('subscribe', 25, {...unicornOptions, theme: 'word'}));
assert.equal(markup('comment', 25, unicornOptions), markup('comment', 25, {...unicornOptions, theme: 'word'}));
const honeyOptions = {theme: 'honey', label: 'HONEY', commentText: 'SWEET'};
const honey = markup('transform', 25, honeyOptions);
assert.match(honey, /<svg[^>]*data-honey="true"[^>]*width="880"[^>]*height="840"/);
for (const part of ['dipper', 'grooves', 'stream', 'drops', 'jar', 'fill']) {
  assert.match(honey, new RegExp(`data-honey-${part}="true"`));
}
assert.doesNotMatch(honey, /HONEY|data-volcano|data-unicorn|<text/);
assert.equal(honey, markup('transform', 25, honeyOptions), 'Honey must repeat identically at the same frame');
assert.notEqual(honey, markup('transform', 26, honeyOptions), 'Honey must animate between frames');
// Aliran dan tetesan harus bergerak sendiri, bukan cuma wrapper yang bergoyang.
for (const part of ['stream', 'drops']) {
  const partTag = new RegExp(`<[^>]*data-honey-${part}="true"[^>]*>`);
  assert.notEqual(honey.match(partTag)[0], markup('transform', 26, honeyOptions).match(partTag)[0]);
}
assert.equal(rootOpacity(markup('transform', 0, honeyOptions)), 0);
assert.ok(rootOpacity(markup('transform', 18, honeyOptions)) > .9);
assert.ok(rootOpacity(markup('transform', 89, honeyOptions)) < .05);
assert.ok(markup('transform', 0, honeyOptions).includes(thumbMarkup), 'Like thumb must remain during honey morph entrance');
assert.ok(!honey.includes(thumbMarkup), 'Like thumb must disappear once honey is fully transformed');
for (const [kind, frame] of [['like', 20], ['subscribe', 25], ['comment', 25]]) {
  assert.equal(markup(kind, frame, honeyOptions), markup(kind, frame, {...honeyOptions, theme: 'word'}), `${kind} must not depend on honey theme`);
}
const puppyOptions = {theme: 'puppy', label: 'PUPPY', commentText: 'WOOF'};
const puppy = markup('transform', 25, puppyOptions);
assert.match(puppy, /<svg[^>]*data-puppy="true"[^>]*width="880"[^>]*height="840"/);
for (const part of ['head', 'ears', 'tail', 'tongue', 'collar', 'paws']) {
  assert.match(puppy, new RegExp(`data-puppy-${part}="true"`));
}
assert.doesNotMatch(puppy, /PUPPY|WOOF|data-volcano|data-unicorn|data-honey|<text/);
assert.equal(puppy, markup('transform', 25, puppyOptions), 'Puppy must repeat identically at the same frame');
assert.notEqual(puppy, markup('transform', 26, puppyOptions), 'Puppy must animate between frames');
for (const part of ['head', 'ears', 'tail']) {
  const partTag = new RegExp(`<[^>]*data-puppy-${part}="true"[^>]*>`);
  assert.notEqual(puppy.match(partTag)[0], markup('transform', 26, puppyOptions).match(partTag)[0]);
}
assert.equal(rootOpacity(markup('transform', 0, puppyOptions)), 0);
assert.ok(rootOpacity(markup('transform', 18, puppyOptions)) > .9);
assert.ok(rootOpacity(markup('transform', 89, puppyOptions)) < .05);
assert.ok(markup('transform', 0, puppyOptions).includes(thumbMarkup), 'Like thumb must remain during puppy morph entrance');
assert.ok(!puppy.includes(thumbMarkup), 'Like thumb must disappear once puppy is fully transformed');
for (const [kind, frame] of [['like', 20], ['subscribe', 25], ['comment', 25]]) {
  assert.equal(markup(kind, frame, puppyOptions), markup(kind, frame, {...puppyOptions, theme: 'word'}), `${kind} must not depend on puppy theme`);
}
const lionOptions = {theme: 'lion', label: 'LION', commentText: 'ROAR'};
const lion = markup('transform', 25, lionOptions);
assert.match(lion, /<svg[^>]*data-lion="true"[^>]*width="880"[^>]*height="840"/);
for (const part of ['head', 'mane', 'ears', 'jaw', 'whiskers', 'roar-waves']) {
  assert.match(lion, new RegExp(`data-lion-${part}="true"`));
}
assert.doesNotMatch(lion, /LION|ROAR|data-volcano|data-unicorn|data-honey|data-puppy|<text/);
assert.equal(lion, markup('transform', 25, lionOptions), 'Lion must repeat identically at the same frame');
assert.notEqual(lion, markup('transform', 26, lionOptions), 'Lion must animate between frames');
for (const part of ['head', 'mane', 'jaw', 'whiskers']) {
  const partTag = new RegExp(`<[^>]*data-lion-${part}="true"[^>]*>`);
  assert.notEqual(lion.match(partTag)[0], markup('transform', 26, lionOptions).match(partTag)[0]);
}
assert.equal(rootOpacity(markup('transform', 0, lionOptions)), 0);
assert.ok(rootOpacity(markup('transform', 18, lionOptions)) > .9);
assert.ok(rootOpacity(markup('transform', 89, lionOptions)) < .05);
assert.ok(markup('transform', 0, lionOptions).includes(thumbMarkup), 'Like thumb must remain during lion morph entrance');
assert.ok(!lion.includes(thumbMarkup), 'Like thumb must disappear once lion is fully transformed');
for (const [kind, frame] of [['like', 20], ['subscribe', 25], ['comment', 25]]) {
  assert.equal(markup(kind, frame, lionOptions), markup(kind, frame, {...lionOptions, theme: 'word'}), `${kind} must not depend on lion theme`);
}
const sharkOptions = {theme: 'shark', label: 'SHARK', commentText: 'SHARK'};
const shark = markup('transform', 25, sharkOptions);
assert.match(shark, /<svg[^>]*data-shark="true"[^>]*width="880"[^>]*height="840"/);
for (const part of ['body', 'fin', 'tail', 'jaw', 'bubbles']) {
  assert.match(shark, new RegExp(`data-shark-${part}="true"`));
}
assert.doesNotMatch(shark, /SHARK|data-volcano|data-unicorn|data-honey|data-puppy|data-lion|<text/);
assert.equal(shark, markup('transform', 25, sharkOptions), 'Shark must repeat identically at the same frame');
assert.notEqual(shark, markup('transform', 26, sharkOptions), 'Shark must animate between frames');
for (const part of ['body', 'fin', 'tail', 'jaw']) {
  const partTag = new RegExp(`<[^>]*data-shark-${part}="true"[^>]*>`);
  assert.notEqual(shark.match(partTag)[0], markup('transform', 26, sharkOptions).match(partTag)[0]);
}
assert.equal(rootOpacity(markup('transform', 0, sharkOptions)), 0);
assert.ok(rootOpacity(markup('transform', 18, sharkOptions)) > .9);
assert.ok(rootOpacity(markup('transform', 89, sharkOptions)) < .05);
assert.ok(markup('transform', 0, sharkOptions).includes(thumbMarkup), 'Like thumb must remain during shark morph entrance');
assert.ok(!shark.includes(thumbMarkup), 'Like thumb must disappear once shark is fully transformed');
for (const [kind, frame] of [['like', 20], ['subscribe', 25], ['comment', 25]]) {
  assert.equal(markup(kind, frame, sharkOptions), markup(kind, frame, {...sharkOptions, theme: 'word'}), `${kind} must not depend on shark theme`);
}
// Props JSON lama tetap boleh word, tapi theme asing tidak boleh diam-diam jadi kartu teks.
for (const theme of ['dragon', '', undefined, null, 'toString', '__proto__']) {
  for (const frame of [0, 25]) {
    assert.throws(() => markup('transform', frame, {theme, label: 'DO NOT RENDER'}), {
      name: 'Error', message: `Unsupported CTA transform theme: ${String(theme)}`,
    });
  }
  for (const [kind, frame] of [['like', 20], ['subscribe', 25], ['comment', 25]]) {
    assert.equal(markup(kind, frame, {theme}), markup(kind, frame, {theme: 'word'}));
  }
}
console.log('11 CTA visual cases passed (like, animated deterministic volcano, subscribe, comment, alternate word theme, animated deterministic unicorn, animated deterministic honey, animated deterministic puppy, animated deterministic lion, animated deterministic shark, unknown transform theme rejection)');
