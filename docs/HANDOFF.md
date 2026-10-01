# Handoff — Fase 1 pipeline

- **Updated:** 2026-10-01 ±11:00 WIB, Claude Code (Opus 5.5)
- **Goal & scope:** Fase 1 sesuai [spec](superpowers/specs/2026-09-30-fase1-pipeline-design.md). Belum masuk Fase 2–4 (lihat [DECISIONS](DECISIONS.md) D-001):
  - hook matching
  - TikTok/Douyin/RedNote
  - caption, musik, SFX, overlay
  - upload
- **Workspace:** `E:\APROJECT\mayzfact-automation`, branch `fase1-pipeline` (dari `master` df60555). `transcript.py` sengaja nggak di-commit (file lama punya Akmal).

## Selesai

- CLI `uv run mayzfact run <id|url> [--from STEP] [--new-voice]` dan `uv run mayzfact voices`.
- Step pipeline:
  - `mayzfact/steps/source.py`: transcript
  - `script.py`: Gemini rewrite + cek otomatis
  - `tts.py`: ElevenLabs with-timestamps
  - `clips.py`: Pexels + Pixabay, video + foto, normalisasi
  - `timeline.py`: hitung frame + layout full/blur
  - `render.py`: Remotion
- Remotion composition `ShortVideo` di `remotion/src/`. Isinya layout full/blur dan zoom pelan buat foto.
- Aturan kunci naskah + suara (spec 3.4). Suara cuma dibuat ulang lewat `--new-voice`.
- Multi API key: `GEMINI_API_KEYS` dan `ELEVENLABS_API_KEYS` (D-008, D-010).
- Voice yang dipakai Liam (`TX3LPaxmHKxFdv7VOQHJ`) dengan model `eleven_v3` (D-009).
- Perbaikan dari final review:
  - Audio yang udah dibayar nggak ditagih ulang kalau ffprobe gagal.
  - TTS nggak di-retry pas read timeout.
  - Output basi dihapus sebelum step diulang.
  - Link mati atau file rusak diganti kandidat berikutnya.

## Verifikasi (2026-10-01, commit a365e37 + docs ini)

- `uv run pytest` → 138 passed (render test di-skip by default).
- `uv run pytest -m render` → 1 passed. Frame fixture udah dicek visual: full, blur 50%, dan zoom foto.
- `npx tsc --noEmit` di `remotion/` → lolos.
- Run beneran `i2xag_1OJfM`:
  - Format: `final.mp4` H.264 1080x1920 30fps + AAC, 41.47 detik.
  - Naskah: 7 beat, 117 kata, overlap 4-gram 0.123.
  - Visual: 19 shot (13 video, 6 foto) dari Pexels + Pixabay, shot terpanjang 2.43 detik, klip unik, credit lengkap.
  - ElevenLabs: 723 karakter, dipanggil 1x.
  - Gemini sempat 503 "high demand" 2x (gangguan sementara Google). Run ketiga sukses.
- Run ulang `--from clips` dengan `ELEVENLABS_API_KEYS` dan `GEMINI_API_KEYS` dikosongin → sukses, mtime `voice.mp3` nggak berubah.
- Contact sheet `runs/i2xag_1OJfM/contact_sheet.png`: nggak ada frame hitam, semua shot portrait full. Shot blur nggak muncul di run ini karena semua klip yang kepilih portrait.
- **Review Akmal (DoD 8): belum.** Fase 1 belum dianggap selesai sampai Akmal nonton `runs/i2xag_1OJfM/final.mp4`.

## Temuan dari run beneran

- **Relevansi klip lemah buat hewan langka.** Horseshoe crab dapat pasir/siput, nautilus dapat gua/kura-kura, platypus dapat kanguru/dekorasi, tardigrade dapat ilmuwan + clipart. Ini keterbatasan Fase 1 (spec 10). Pencocokan visual masuk Fase 2.
- **Beat dari Gemini kepanjangan** (7 beat, ±6 detik per beat), padahal prompt minta 1.5–3.5 detik. Pacing tetap aman karena beat dipecah jadi shot ≤2.5 detik. Tapi tiap beat cuma pakai 1 query, jadi beberapa shot berturut-turut isinya mirip.
- Urutan countdown di naskah nggak konsisten ("First… Next… Then… At number two… Finally").
- Default voice ElevenLabs (termasuk Liam) dimatiin 2026-12-31. Penggantinya "Lawrence - Bright and Informative", tapi ID-nya belum ketemu karena key nggak punya izin `voices_read`.

## Delivery

- Semua udah di-commit di branch `fase1-pipeline`. Belum di-push dan belum di-merge ke `master`. Push/merge tunggu Akmal.

## Sisa kerjaan / next

1. Akmal nonton `final.mp4` dan kasih feedback.
2. Minor yang di-defer dari final review (ada di ledger `.superpowers/sdd/2026-09-30-fase1-pipeline/progress.md`):
   - error non-PipelineError
   - backup `script.json` sebelum `--new-voice`
   - limit query Pixabay
   - cek durasi klip
   - transcript `en-US`/`en-GB`
   - normalisasi NFC
3. Opsional sebelum Fase 2: perketat prompt biar beat lebih pendek dan pakai query berbeda per shot, plus benerin urutan countdown.
4. Fase 2 (hook matching): mulai lagi dari brainstorming.
