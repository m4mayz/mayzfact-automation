# Fase 3A: number card, subject card, caption per kata

- **Tanggal:** 2026-10-13
- **Status:** disetujui lewat chat (3 bagian design). Akmal minta langsung plan + eksekusi, review lewat Studio.
- **Referensi:** D-001 (scope Fase 3), D-021 (number card), [spec metode manual](2026-10-13-manual-clip-source-design.md).

## 1. Tujuan

Fase 3 dipecah jadi tiga:

- **3A (spec ini):** countdown + caption.
- **3B:** audio, yaitu BGM + SFX.
- **3C:** overlay panah/lingkaran/emoji + CTA.

Target 3A, mengikuti source `i2xag`:

- Pas narasi "Number five, horseshoe crab." yang tampil itu number card "5", terus subject card. Bukan klip biasa.
- Caption muncul 1 kata per tampilan, sinkron sama suara.

## 2. Arsitektur

- Python ngitung semua timing dan nulis hasilnya ke `timeline.json`. Remotion cuma render dari props.
- Modul baru `mayzfact/countdown.py`, dipakai mode `manual` maupun `auto`:
  - Fungsi `parse_countdown(text) -> Countdown | None`.
  - `Countdown` berisi `number: int | None`, `subject: str`, dan `number_end: int` (index karakter terakhir token angka di teks beat).
  - Pola yang dicocokin: `^\s*number\s+(\w+)\s*[,:.\-–]\s*(?:the\s+)?(.+?)\s*[.!?]*\s*$`, nggak peduli huruf besar/kecil.
  - Konversi angka: `one…ten`, atau digit `1–99`. Selain itu `number=None`, jadi card nggak dibikin, tapi subjeknya tetap dipakai `beat_subjects`.
- `clips.beat_subjects` pakai `parse_countdown` (ganti `_COUNTDOWN`).
- `clips.split_shots` nggak motong beat countdown, jadi 1 beat = 1 shot. Aturan ini berlaku di kedua mode.
- `timing.word_timings(alignment) -> [{"text", "start_s", "end_s", "char_start", "char_end"}]`:
  - Kata = deretan karakter non-spasi.
  - `start_s` diambil dari karakter pertama, `end_s` dari karakter terakhir.
- `plan` nambahin `countdown: <angka> | null` di tiap shot. Brief nampilin "CARD #5" di daftar shot kelompok.
- Fetch nggak berubah: shot countdown dapat klip dari kelompok subjeknya, kayak shot lain.

## 3. `timeline.json`

Ada dua field baru. `shots` tetap sama.

```json
"captions": [{"text": "CHECK", "from": 0, "durationInFrames": 9, "color": "#ffffff"}],
"countdown": [{"number": 5, "label": "HORSESHOE CRAB", "numberFrom": 341, "numberDuration": 24,
               "cardFrom": 365, "cardDuration": 50, "src": "clips/shot_06.mp4", "kind": "video", "clipOffset": 24}]
```

**`countdown`:** 1 entry per beat countdown yang `number`-nya ketemu.

- Number card: dari awal beat sampai `end_s` karakter terakhir token angka.
- Subject card: dari situ sampai akhir beat.
- `src`/`kind` diambil dari shot yang nutup awal subject card. `clipOffset` = `cardFrom - shot.from`.
- Card dirender di atas shot, background-nya opaque, jadi frame tetap nyambung.

**`captions`:** semua kata, kecuali yang ada di dalam rentang beat countdown.

- Teks: huruf kapital, tanda baca di ujung kata dibuang.
- Durasi: sampai kata berikutnya mulai, maksimal `end_s + 0.4`, minimal 1 frame.
- Warna:
  - Default putih.
  - Kata yang bagian dari nama subjek mana pun, atau kata dengan panjang ≥ 6 huruf, dapat warna gantian `#22d3ee` → `#4ade80` → `#facc15`.

`build_timeline(clips, audio_duration_s, fg_min_ratio, script=None, alignment=None)`:

- Kalau `script`/`alignment` nggak ada, `captions` dan `countdown` jadi `[]`.
- Kalau alignment nggak cocok sama teks, `captions` dan `countdown` jadi `[]` plus log peringatan. Timeline tetap ditulis.

## 4. Remotion

- `@remotion/google-fonts@4.0.534`, font Anton.
- **`Particles`:** background hitam kebiruan dengan gradien radial, plus 40 partikel. Posisinya pakai `random(seed)` Remotion, gerak pelan ke atas.
- **`NumberCard`:**
  - Angka Anton ±900px dengan gradien chrome yang di-clip ke teks, outline tipis, dan drop shadow.
  - Masuk pakai spring scale 1.4 → 1.0 + fade. Selama tampil, zoom 1.0 → 1.05.
- **`SubjectCard`:**
  - `Particles`, kotak 820×820 di tengah yang isinya klip (`objectFit: cover`, video mulai di `clipOffset`).
  - Border 12px oranye-kuning dengan glow `box-shadow` yang berdenyut (sinus).
  - Label Anton ±110px putih dengan outline hitam di bawah kotak.
  - Masuk pakai spring scale 0.8 → 1.0.
- **`Captions`:**
  - Tiap caption 1 `Sequence`. Teks Anton ±120px di tengah horizontal, posisi top 68%, outline hitam 8px + shadow.
  - Pop 0.85 → 1.0 dalam ±4 frame.
- **Urutan layer di `ShortVideo`:** shots → countdown → captions → audio.

## 5. Testing & DoD

- **Pytest:**
  - `parse_countdown` (angka kata/digit, `the`, angka nggak dikenal)
  - `word_timings`
  - `split_shots` (beat countdown nggak dipotong)
  - `beat_subjects` (perilaku lama tetap)
  - builder timeline: captions, warna, rentang countdown, `clipOffset`, fallback tanpa script
- `npx tsc --noEmit`. Fixture test render marker ditambahin 1 countdown + captions.
- **DoD:**
  1. Run i2xag di Studio nampilin 5 number card (5→1). Tiap card diikutin subject card dengan klip kelompoknya yang menyala.
  2. Caption per kata sinkron.
  3. Semua test lolos, termasuk mode `auto`. Render cuma dijalanin setelah Akmal oke.
