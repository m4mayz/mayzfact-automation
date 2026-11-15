// Tes markup nyata FaktaCuilCta: tiap format harus punya gerak stiker sendiri.
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
const {FaktaCuilCtaVisual} = require('../src/FaktaCuilCta.tsx');

const base = {
  theme: 'shark', commentText: 'HIU', from: 0, durationInFrames: 150,
  stages: [{kind: 'like', from: 0, durationInFrames: 60, triggerAt: 10}],
  cues: [{kind: 'like', from: 10, word: 'like'}],
};
const markup = (format, frame) => renderToStaticMarkup(
  React.createElement(FaktaCuilCtaVisual, {scene: {...base, format}, frame}));

const formats = ['question', 'reveal', 'escape', 'escalate'];
// Frame 40 = stiker udah tampil (pill LIKED 10..30, stiker mulai 32).
const stickerAt = (format) => markup(format, 40).match(/<div data-cta-sticker="true" data-cta-format="(\w+)"[^>]*style="([^"]+)"/);
for (const format of formats) {
  const found = stickerAt(format);
  assert.ok(found, `${format}: stiker harus tampil di frame 40`);
  assert.equal(found[1], format, `${format}: data-cta-format harus ikut scene`);
}
// Gerak tiap format beda di frame yang sama.
const styles = formats.map((f) => stickerAt(f)[2]);
assert.equal(new Set(styles).size, formats.length, 'tiap format harus punya gaya stiker berbeda');
// reveal: naik ke posisi akhir, scale mendekati 1 setelah pop.
assert.match(stickerAt('reveal')[2], /top:\s?1030px/);
// escape: bergeser jauh ke kanan bawah di akhir scene.
const escapeEnd = markup('escape', 149).match(/left:\s?([\d.]+)px/);
assert.ok(Number(escapeEnd[1]) > 900, 'escape harus keluar frame di akhir');
// escalate: makin besar, bukan menyusut.
const scaleOf = (html) => Number(html.match(/scale:\s?([\d.]+)/)[1]);
assert.ok(scaleOf(markup('escalate', 145)) > scaleOf(markup('escalate', 40)), 'escalate harus membesar');
// question default kalau format kosong (naskah lama).
const legacy = renderToStaticMarkup(React.createElement(FaktaCuilCtaVisual, {scene: base, frame: 40}));
assert.match(legacy, /data-cta-format="question"/);
console.log('faktacuil cta: OK');
