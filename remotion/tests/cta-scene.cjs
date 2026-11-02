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
const shotSource = fs.readFileSync(path.join(__dirname, '../src/ShotView.tsx'), 'utf8');
const decorative = shotSource.split('if (shot.decorative)')[1].split("if (shot.layout === 'full')")[0];
const blur = Number(decorative.match(/blur\(([\d.]+)px\)/)[1]);
const brightness = Number(decorative.match(/brightness\(([\d.]+)\)/)[1]);
assert.ok(blur <= 12, `Glass blur must retain visible footage, got ${blur}px`);
assert.ok(brightness >= 0.7, `Glass footage must remain visible, got brightness ${brightness}`);
console.log('5 CTA visual cases passed (like, animated deterministic volcano, subscribe, comment, alternate word theme)');
