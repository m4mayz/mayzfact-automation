# Per-run approved narration length

## Approved intent
Akmal approved a longer-than-30–40-second Top 3 for pG-Y-ICCAXQ to preserve source facts and qualifications, then approved continuation after reviewing the 131-word script. Preserve native VoiceStudio/Alex/CosyVoice speed 1.0 and the original ranking 3/2/1. Do not relax other checks or affect other videos.

## Bounded design
Add optional strict integer `Script.approved_word_count` (1–500). Only Top 3 uses it. When set, the shared `narration_word_range` returns that exact count for target/lower/upper. Missing field preserves existing budget; legacy source mode ignores it. Structure, overlap, per-beat words, media, keyword and CTA checks remain active. This is not blanket authorization: the operator sets it only after the user approves the longer script. The field records the exact count, not proof of human approval; this document records the approval context.

## Implementation plan and verification
1. Write JSON round-trip / exact-budget test; observe RED against existing implementation.
2. Add model field and shared budget branch; observe GREEN.
3. Check unchanged defaults, legacy behavior, invalid values and continued enforcement of other checks.
4. Set 131 only in this run and run both audit and CLI validation.
5. Run the full Python suite, generate voice, validate timing/plan, then open brief.

## Verified so far
Initial test failed with `(73, 70, 76)` instead of `(131, 131, 131)`. After implementation, all five focused tests passed. Operator audit returned `SEMUA OK`; CLI returned `OK: naskah lolos cek (131 kata, target 131)`. Full-suite result and voice/plan/brief are separate milestones, not established by these tests.
