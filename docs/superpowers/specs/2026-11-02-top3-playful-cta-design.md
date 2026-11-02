# Top 3 playful CTA — approved bounded revision

Status: bounded design approved by Akmal in chat; implementation delegated with strict RED→GREEN, no commit. Supersedes only the Top 3 CTA length/style and CTA-derived total budget in D-045. Source mode and existing paid-audio resume remain unchanged.

## Intent and authoring contract

Keep hook → original source ranks 3 → 2 → CTA → 1, all non-CTA narration unchanged when revising a run. New CTA opens with a transition before number one, invites a like, asks about a playful topic-specific fictional button transformation, makes subscribe conditional on it working, and invites a comment. Example (not a reusable volcano template):

1. `But before number one, try tapping like.`
2. `Did the button turn into a volcano?`
3. `Subscribe if it worked,`
4. `and comment 'erupted'.`

The transformation is entertainment, not an implemented platform feature or a claim of tested real behavior. Adapt it to each topic. No religious threats, prizes, or withholding number one. These semantic requirements belong in authoring instructions, not brittle semantic regex validation. Old valid CTA forms remain structurally supported.

## Shared structural contract

- One contiguous block of 1–4 beats immediately before Number one; each beat stays ≤10 words. Every CTA beat has empty subject and point=false; no CTA beat counts as explanation or hook.
- Keep `cta_beat_indices(beats)` as the single detector for validator, word budget, plan, timeline and operator audit. Detect explicit invitation beats, plus a structural `But before number one` / `Before number one` lead-in. Within each countdown-delimited section, fill the span between its first and last CTA anchors, including no-trigger transition/question beats. Do not bridge countdown headings. Preserve detached invitation indices so invalid placement is rejected rather than hidden.
- The detector cannot infer arbitrary prose intent. A non-CTA body beat inserted between CTA anchors is part of that candidate block; normal subject/point constraints and the 4-beat cap reject annotated body intrusion. Do not silently absorb trailing body text after the last CTA anchor. Document this deterministic boundary instead of introducing schema metadata or guessing thematic semantics.
- Recognize invitational `tapping like` without broadening descriptive `like`/similes. Timeline keeps existing real-word alignment logic: animate like/subscribe on their actual invitation tokens in spoken order, finish before Number one; comment stays narration/caption. No transformation animation or feature is added.

## Bounded budget

Retain the existing speed-scaled Top 3 base tuple, `(80, 76, 84)` at 1.1x. Add `max(0, actual CTA words - 10)` to target, low and high, using shared detector and tokenizer. Do not scale that actual-word delta again. The CTA is at most 40 words because of the 4×10 beat bounds: at 1.1x the largest valid total tuple is `(110, 106, 114)`, not unlimited. Source word_range is untouched. Invalid CTA blocks must still fail structural validation even if their word budget fits.

The 30–40 second final target remains the body/baseline goal; the added CTA may extend it. Report measured audio duration / speed after an authorized TTS operation; do not alter speed/provider, discard paid audio, or regenerate automatically.

## Verification / exclusions

Strict vertical RED→GREEN slices: invitation detection; complete CTA span and structural guards; shared budget boundaries/CLI; plan/timeline/audit integration. Cover old CTA compatibility, exact approved four-beat example, separate triggerless lead-in, question exclusion from explanation, wrong placement, detached/gapped blocks, 5 beats, >10 words, empty subject/no point, source mode and protected resume. Run full offline suite and external audit regressions. Do not generate TTS, render, upload, push, modify production runs/audio, or start brief. Parent separately backs up/updates Q0zEnOUT3mM, revoices with paid audio preserved, then rebuilds plan/brief after review.
