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
- Setelah prompt diperketat (commit 7549001), dijalanin ulang pakai `--new-voice`:
  - Naskah: 16 beat (≤10 kata), countdown "Number five … Number one" rapi, overlap 0.029.
  - Video: 49.3 detik, 32 shot (22 video + 10 foto), shot terpanjang 1.93 detik.
  - ElevenLabs: 696 karakter. Gemini sempat 503 lagi 1x.
- Contact sheet PNG besar sempat kelihatan "pecah warna". Setelah dicek per tahap (file mentah → klip normalisasi → final.mp4 per frame), file-nya bersih. Yang pecah cuma tampilan dari tool viewer agent, bukan videonya.
- **Review Akmal (DoD 8): oke** (chat 2026-10-03). Fase 1 selesai.

## Temuan dari run beneran

- **Relevansi klip lemah buat hewan langka.** Horseshoe crab dapat pasir/siput, nautilus dapat gua/kura-kura, platypus dapat kanguru/dekorasi, tardigrade dapat ilmuwan + clipart. Ini keterbatasan Fase 1 (spec 10). Pencocokan visual masuk Fase 2.
- **Beat dari Gemini kepanjangan** (7 beat, ±6 detik per beat), padahal prompt minta 1.5–3.5 detik. Pacing tetap aman karena beat dipecah jadi shot ≤2.5 detik. Tapi tiap beat cuma pakai 1 query, jadi beberapa shot berturut-turut isinya mirip.
- Urutan countdown di naskah nggak konsisten ("First… Next… Then… At number two… Finally").
- Default voice ElevenLabs (termasuk Liam) dimatiin 2026-12-31. Penggantinya "Lawrence - Bright and Informative", tapi ID-nya belum ketemu karena key nggak punya izin `voices_read`.

## Delivery

- Fase 1 udah di-merge ke `master` (2026-10-03). Push/merge tunggu Akmal.

## Sisa kerjaan / next

1. ~~Akmal nonton `final.mp4`~~ udah oke (2026-10-03).
2. Minor yang di-defer dari final review (ada di ledger `.superpowers/sdd/2026-09-30-fase1-pipeline/progress.md`):
   - error non-PipelineError
   - backup `script.json` sebelum `--new-voice`
   - limit query Pixabay
   - cek durasi klip
   - transcript `en-US`/`en-GB`
   - normalisasi NFC
3. ~~Perketat prompt~~ udah dikerjain (beat ≤10 kata, countdown, query per shot, backoff Gemini 5/10/20s). Relevansi klip buat hewan langka masih meleset (horseshoe crab → ghost crab, tardigrade → preparat), jadi tetap butuh Fase 2.
4. Gemini `gemini-3.8-flash` sering 503 "high demand". Kalau makin sering, pertimbangkan model cadangan.
5. ~~Fase 2 (hook matching)~~ dikerjain, lihat section Fase 2 di bawah.

---

# Handoff — Fase 2 hook matching

- **Updated:** 2026-10-03 10:30 WIB, Claude Code (Opus 5.5)
- **Goal & scope:** sesuai [spec Fase 2](superpowers/specs/2026-10-03-fase2-hook-matching-design.md) dan [plan](superpowers/plans/2026-10-03-fase2-hook-matching.md). Keputusannya D-011 sampai D-015.
- **Workspace:** `E:\APROJECT\mayzfact-automation`, branch `fase2-hook`. Belum di-merge ke `master`.

## Selesai

- Step `hook`: download source (yt-dlp), deteksi cut, frame per segmen, query dari Gemini vision, cari kandidat di TikTok/Douyin/RedNote/Pinterest + stock, seleksi SigLIP 2 tahap, dan tulis `hook.json`.
- Rerank SigLIP (teks beat vs thumbnail) buat shot non-hook, dengan cache embedding.
- Command `mayzfact login <platform>` (plus warm-up captcha di halaman search) dan `mayzfact login --check`.
- Final review (subagent Opus): 1 Critical + 4 Important di-fix pakai TDD. Detailnya di ledger `.superpowers/sdd/2026-10-03-fase2-hook-matching/progress.md`.

## Verifikasi

- `uv run pytest`: 205 lolos. `-m clip` (SigLIP asli) dan `-m render` juga lolos.
- Status login (2026-10-03):

  | Platform | Hasil |
  | --- | --- |
  | Pinterest | jalan, 25 kandidat |
  | TikTok | jalan setelah warm-up captcha (24 kandidat), tapi captcha muncul lagi setelah beberapa search |
  | Douyin | selalu kena captcha di search |
  | RedNote | belum login beneran. Halaman search minta login, padahal `--check` bilang login |

- `uv run mayzfact run i2xag_1OJfM --from hook`: sukses, `final.mp4` 49.3 detik, mtime `voice.mp3` sama (ElevenLabs nggak dipanggil).
- `hook.json`: 6 segmen, semua punya pemenang, label semua `similar` (skor 0.66–0.78).
  - Sumber pemenang: 5 dari Pinterest, 1 dari Pexels.
  - Platform yang di-skip: Douyin (captcha), RedNote (captcha/login), TikTok (context browser ketutup di tengah run).
- `runs/i2xag_1OJfM/hook_compare.jpg` (source vs pemenang):
  - 3 dari 6 segmen subjeknya sama (pterosaurus, mammoth, cowok di mall H&M).
  - Segmen 1–3 (burung monster di menara radio) cuma mirip tema.
  - Nggak ada yang klip persis sama.
- `runs/i2xag_1OJfM/contact_sheet_fase2.jpg`: shot non-hook lebih relevan dari Fase 1. Horseshoe crab sekarang asli, nautilus dan sturgeon pas, tardigrade jadi mikroorganisme di bawah mikroskop.
- `HOOK_EXACT_THRESHOLD` tetap 0.85, karena belum ada pasangan klip yang persis sama buat kalibrasi (D-015).
- **Review Akmal:** oke via Remotion Studio (2026-10-12), setelah revisi D-016/D-017 (shot 4 detik, Pinterest buat klip, relevansi pakai nama subjek, hook cuma ke shot yang selesai di area hook). Render final 49.3 detik, 16 shot.

## Masalah terbuka

1. Captcha TikTok/Douyin. Warm-up cuma bertahan sebentar. Nggak ada trik buat ngakalin deteksi bot (D-014).
2. RedNote: penanda login (`web_session`) salah, karena cookie itu juga ada di sesi yang belum login. Perlu cookie dari sesi login asli buat nentuin penanda yang benar.
3. Context TikTok ketutup di tengah run ("Target page, context or browser has been closed"). Penyebabnya belum ketemu: bisa crash, bisa juga jendelanya ketutup manual.
4. Satu foto Pinterest gagal dibuka ("bukan gambar"). Kemungkinan formatnya nggak didukung PIL.
5. Minor dari final review (lihat ledger): nama cache thumbnail, `close()`, waktu tunggu ±41 detik, thumbnail CDN.

## Delivery

- Di-merge ke `master` (2026-10-12). Belum di-push.
- Next: metode manual buat semua shot (Douyin/RedNote dicari Akmal sendiri, link diinput lewat halaman brief lokal). Bilibili di-skip. Fase 3 ditahan.
