# Fase 3C-2 Emoji + CTA + Point Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** Emoji animasi, CTA like/subscribe, sama panah yang muncul cuma di beat `point`.
**Spec:** [`docs/superpowers/specs/2026-10-14-fase3c2-emoji-cta-design.md`](../specs/2026-10-14-fase3c2-emoji-cta-design.md)

> **Ruling (eksekutor):** Plan ini sengaja ringan, cuma interface sama test kunci, soalnya Akmal minta langsung dikerjain. Kodenya ditulis TDD.

## Global Constraints

- Branch: `fase3c2-emoji-cta`.
- Commit pakai `caveman-commit`, 1 baris, tanpa atribusi.
- Test otomatis nggak boleh pakai network beneran dan nggak boleh load model asli.
- `voice.mp3` nggak boleh disentuh. Buat i2xag cukup pakai anotasi, nggak perlu bikin suara baru.
- Jangan render final sebelum Akmal review di Studio.

## Review Focus

1. Naskah lama tanpa key `point` dan Gemini gagal: timeline tetap jadi, tanpa panah dan tanpa emoji.
2. `emoji_word` yang muncul 2 kali di beat yang sama, atau ada tanda baca nempel (contoh: "luck!").
3. Kata "like" dalam arti "mirip" (misalnya "looks like a tank") nggak boleh mancing CTA.
4. Emoji yang waktunya nabrak CTA atau card countdown.
5. Lottie gagal di-fetch di Remotion: render jangan nge-hang.

### Task 1: Penanda beat + aset emoji

Isinya:

- `models.Beat` dapat field `point`, `emoji`, `emoji_word`
- model `BeatMark` / `BeatMarks`
- `mayzfact/emoji.py`: `EMOJI`, `ensure_emoji`
- `mayzfact/marks.py`: `normalize_marks`, `beat_marks`, `prepare_marks`
- prompt `mark_beats.md`
- update `rewrite.md`, plus `generate_script` yang nempelin daftar emoji ke prompt

Test-nya: `tests/test_marks.py` dan tambahan di `tests/test_script_step.py`.

### Task 2: Timeline + overlay + pipeline

Isinya:

- `build_timeline(marks=)` ngisi `emojis`, `cta`, sama SFX `emoji` / `click`
- `prepare_overlays(point_beats=)`
- `Deps.marks`, terus `deps.overlay(paths, log, marks)`
- update `sfx.json` + `.gitignore`

Test-nya: `tests/test_timeline.py`, `tests/test_overlay.py`, `tests/test_pipeline.py`.

### Task 3: Remotion

Isinya:

- install `@remotion/lottie@4.0.534` dan `lottie-web@5.13.0`
- `Emojis.tsx`, `Cta.tsx`
- font Montserrat
- update types sama `ShortVideo`
- fixture test render

### Task 4: E2E i2xag + bandingin sama source + Studio + review + HANDOFF
