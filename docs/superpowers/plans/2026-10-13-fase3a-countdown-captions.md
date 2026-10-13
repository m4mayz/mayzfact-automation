# Fase 3A Countdown + Captions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Number card dan subject card buat beat "Number X, subjek", plus caption per kata. Semuanya dirender Remotion dari `timeline.json`.

**Architecture:** Deteksi countdown, timing per kata, dan builder timeline ditulis di Python (pytest). Komponen visual ditulis di Remotion (tsc + render marker + review Studio).

**Tech Stack:** Python 3.14/uv, Remotion 4.0.534, `@remotion/google-fonts` (Anton).

**Spec:** [`docs/superpowers/specs/2026-10-13-fase3a-countdown-captions-design.md`](../specs/2026-10-13-fase3a-countdown-captions-design.md)

> **Ruling (eksekutor):** Akmal minta langsung plan + eksekusi (chat 2026-10-13: "just do the best … nanti gua review lewat studio"). Plan ini cuma nyantumin interface, test kunci, dan perintah. Kode lengkapnya ditulis TDD pas eksekusi. Angka, nama, dan format yang dipakai tetap ngikutin spec.

## Global Constraints

- **Branch:** `fase3a-countdown`.
- **Commit:** pakai skill `caveman-commit`, 1 baris, tanpa atribusi AI.
- **Test otomatis:** nggak boleh pakai network, browser, atau model.
- **Suara:** `voice.mp3` nggak boleh disentuh. `--from timeline` nggak boleh manggil ElevenLabs.
- **Mode `auto`:** perilakunya nggak boleh berubah, kecuali dua hal yang memang disengaja: caption/countdown sekarang ikut muncul di timeline, dan beat countdown nggak dipotong lagi.
- **Render:** jangan render final. Review dulu di Studio.

## Review Focus

1. Beat countdown yang angkanya nggak dikenal (misalnya "Number eleven"): nggak boleh ada card, shot tampil normal.
2. Teks dengan tanda kutip/apostrof ("It's"): caption-nya harus tetap utuh.
3. Alignment yang nggak cocok sama naskah: timeline tetap jadi, cuma tanpa caption.
4. `clipOffset` waktu card mulai di tengah shot.
5. Run lama yang shot countdown-nya kepotong 2 (dibikin sebelum aturan no-split): card ngambil shot yang nutup awal card.

---

### Task 1: `countdown.py` + `beat_subjects` + `split_shots`

- **Create:** `mayzfact/countdown.py` dengan `Countdown(number: int | None, subject: str, number_end: int)` dan `parse_countdown(text)`.
- **Modify:** `mayzfact/steps/clips.py`:
  - `beat_subjects` pakai `parse_countdown(...).subject.lower()`.
  - `split_shots`: `count = 1` kalau `parse_countdown(beat["text"])`.
- **Test:** `tests/test_countdown.py`, dan tambahan di `tests/test_clips_step.py` / `tests/test_clip_selection.py`.
  - `parse_countdown("Number five, horseshoe crab.") == Countdown(5, "horseshoe crab", 10)`
  - `"number 3: the platypus!"` → `(3, "platypus", 7)`
  - `"Number eleven, x."` → `number=None`, subjek `"x"`
  - `"It is old."` → `None`
  - `split_shots` buat beat countdown 6 detik dengan `max_shot_s=4` tetap jadi 1 slot.
- **Run:** `uv run pytest tests/test_countdown.py tests/test_clips_step.py tests/test_clip_selection.py -q`
- **Commit:** `feat: add countdown parser and keep countdown beats whole`

### Task 2: `word_timings`

- **Modify:** `mayzfact/timing.py`. Tambah `word_timings(alignment) -> list[dict]` dengan key `text`, `start_s`, `end_s`, `char_start`, `char_end`.
- **Test:** tambahan di `tests/test_timing.py`:
  - `"Hi there, it's ok."` jadi 4 kata dengan `char_start`/`char_end` yang benar.
  - Spasi ganda nggak bikin kata kosong.
- **Run:** `uv run pytest tests/test_timing.py -q`
- **Commit:** `feat: add word timings from alignment`

### Task 3: Builder timeline (captions + countdown) + pipeline

- **Modify:** `mayzfact/steps/timeline.py`:
  - `build_timeline(clips, audio_duration_s, fg_min_ratio, script=None, alignment=None)`
  - `run_timeline(paths, clips, tts, *, fg_min_ratio, script=None, log=print)`
- **Modify:** `mayzfact/pipeline.py`: kirim `script=read_json(paths.script_json)`.
- **Test:** tambahan di `tests/test_timeline.py`. Naskahnya 3 beat: biasa, countdown, biasa.
  - `countdown[0]` punya `number`, `label` huruf kapital, `numberFrom == to_frame(awal beat)`, dan `numberDuration`/`cardFrom` dari `end_s` token angka.
  - `cardFrom + cardDuration == to_frame(akhir beat)`. `src`/`clipOffset` dari shot yang nutup `cardFrom`.
  - `captions` nggak berisi kata dari beat countdown. Teksnya huruf kapital dan tanpa tanda baca.
  - Durasi caption maksimal sampai `end+0.4`, tapi nggak lewat awal kata berikutnya.
  - Warna: kata < 6 huruf putih. Kata ≥ 6 huruf, atau kata yang bagian dari subjek, dapat warna gantian.
  - Tanpa `script`, hasilnya `captions == countdown == []`. Kalau alignment nggak cocok, juga `[]` dan nggak raise.
  - "Number eleven, x.": nggak ada entry countdown, dan kata-katanya tetap muncul jadi caption.
- **Run:** `uv run pytest tests/test_timeline.py tests/test_pipeline.py -q`
- **Commit:** `feat: build captions and countdown cards in timeline`

### Task 4: Plan/brief nandain shot countdown

- **Modify:** `mayzfact/steps/plan.py`: shot dapat field `countdown`, isinya angka atau null.
- **Modify:** `mayzfact/brief/page.py`: shot countdown ditandai `CARD #N`.
- **Test:** tambahan di `tests/test_plan.py` dan `tests/test_brief_server.py`.
- **Run:** `uv run pytest tests/test_plan.py tests/test_brief_server.py -q`
- **Commit:** `feat: mark countdown shots in plan and brief`

### Task 5: Komponen Remotion

- **Install:** `cd remotion && npm i @remotion/google-fonts@4.0.534 --save-exact`
- **Create:** di `remotion/src/`: `fonts.ts`, `Particles.tsx`, `NumberCard.tsx`, `SubjectCard.tsx`, `Captions.tsx`.
- **Modify:**
  - `types.ts`: tambah `Caption`, `CountdownCard`, plus field `captions` dan `countdown` di `TimelineProps` (dua-duanya default `[]`).
  - `ShortVideo.tsx`: urutan layer shots → countdown → captions → audio.
  - `Root.tsx`: tambah `defaultProps`.
- **Test:** `tests/test_render.py`, fixture-nya ditambah 1 countdown + 2 caption.
- **Run:**
  - `cd remotion && npx tsc --noEmit`
  - `uv run pytest -m render -q`
- **Commit:** `feat: add number card, subject card and caption components`

### Task 6: E2E i2xag + Studio

- **Run:** `uv run mayzfact run i2xag_1OJfM --from timeline --no-render`. Expect exit 0, `timeline.json` punya 5 countdown + caption, dan `voice.mp3` nggak berubah.
- Restart Studio di port 3000, terus cek frame di sekitar tiap number card.
- Jalanin final review (Opus), terus fix Important.
- Update HANDOFF.
- **Commit:** `docs: record fase 3a`
