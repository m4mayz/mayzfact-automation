# CTA motion revision — approved bounded design

## Intent and scope
Akmal selected the latest Alex voice and requested richer CTA animation without sudden appearances. Preserve the audio, spoken cues, clips, glass blur, and caption area; do not add SFX or change timing/schema/provider.

## Approved motion
- Like: rise + spring entrance, approaching cursor, click pulse/ripple and thumb particles.
- Transformation: circular like shrinks/fades into growing volcano, animated eruption/smoke and brief shake.
- Subscribe: expand horizontally, stagger letters, approaching cursor, click and SUBSCRIBED + confetti.
- Comment: slide/pop card, type ERUPTED, cursor, shrink/fade before Number one.
- Every stage enters from zero opacity and exits within its existing duration. All animation is deterministic and frame-driven. The like stage does not begin before the existing spoken invitation.

## Bounded implementation plan
1. RED: static-markup test for every stage's zero-opacity first frame, readable hold and zero-opacity last frame; typed comment, click ripple and confetti.
2. GREEN: shared motion/particle helpers plus scoped CtaScene changes; retain existing word-timing tests and glass-background limits.
3. Verify Node markup cases, TypeScript, offline pytest, then render the actual Alex preview. No new TTS, fetch changes or visual audit sweep.

## Verification so far
RED observed: `like must enter from invisible` (1 !== 0). Focused Node animation assertions and TypeScript subsequently passed. Final offline/render result is reported by the parent execution.
