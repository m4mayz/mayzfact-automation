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

---

# Handoff — Metode manual (klip dicari Akmal)

- **Updated:** 2026-10-13 14:30 WIB, Claude Code (Opus 5.5)
- **Goal & scope:**
  - Sesuai [spec metode manual](superpowers/specs/2026-10-13-manual-clip-source-design.md), termasuk bagian 10 dan revisinya, plus [plan](superpowers/plans/2026-10-13-manual-clip-source.md).
  - Keputusan: D-019 sampai D-021.
- **Workspace:** `E:\APROJECT\mayzfact-automation`, `master`.

## Selesai

- **Mode `CLIP_SOURCE=manual`** (default): `source → script → tts → plan → fetch → timeline → (Studio) → render`. Mode `auto` (Fase 2) tetap ada.
- **`plan`:**
  - shot dikelompokin per konteks: semua hook jadi 1 kelompok, sisanya per subjek
  - frame referensi per shot hook
  - 3 frame source per kelompok isi, diambil dari rentang waktu subjek disebut di transcript
  - keyword en/zh (zh diterjemahin Gemini)
- **Brief `mayzfact brief <id>`** (127.0.0.1:3100):
  - 1 card per kelompok, textarea 1 baris = 1 link, upload file
  - panel progress fetch live
  - keamanan: Host allowlist (DNS rebinding), Origin check (CSRF), path confinement, limit upload, rendering pakai `textContent`
- **`fetch`:** yang diterima file upload, URL langsung, yt-dlp, dan resolver:
  - Douyin (ttwid + SSR + WAF PoW + iteminfo)
  - RedNote (`__INITIAL_STATE__`)
  - TikTok (tiktokio.com, pendekatan scrapr)
  - og
- **Pemilihan klip di `fetch`:**
  - pakai SigLIP
  - hook 1 video diputer nyambung
  - klip yang udah tampil nggak dipakai lagi (D-021)
  - kelompok yang belum lengkap → `AwaitingInput` (exit 3)
- **Review:**
  - final review Opus buat versi per shot: 5 Important udah di-fix
  - review kedua buat revisi per kelompok: 4 Important udah di-fix (file lock di Windows, progress nyangkut, rentang transcript, spec vs D-021)

## Verifikasi E2E (i2xag_1OJfM)

- `--from plan --no-render`: exit 3, 16 shot jadi 6 kelompok (HOOK 1–3, horseshoe crab 4–6, nautilus 7–8, platypus 9–11, sturgeon 12–13, tardigrade 14–16). Frame source 5 kelompok isi cocok semua sama subjeknya. `voice.mp3` nggak berubah.
- **Akmal ngisi 18 link TikTok.**
  - yt-dlp langsung ke TikTok gagal: butuh impersonation TLS, yang sengaja nggak dipakai. Lewat tiktokio, ke-18 link berhasil.
  - 1 link sempat gagal SSL handshake. Pas fetch diulang, berhasil.
- **Hasil akhir:**
  - 14 entry `clips.json`: 1 hook nyambung (skor 0.909, mulai dari detik 5.0) + 13 shot isi, semuanya dari video yang beda.
  - Skor teks shot isi 0.08–0.17. Shot 16 dapat peringatan skor rendah.
- **Review Akmal di Studio (2026-10-13):** dari review ini muncul tiga revisi: hook nggak dipotong-potong, no-reuse, number card. Render final belum diminta.

## Masalah terbuka

1. **Tes link beneran (2026-10-13):**
   - **Douyin** `v.douyin.com/LryWqP-HufY`: yt-dlp gagal, resolver Douyin berhasil. Hasilnya video 720×1280, 6 detik, tanpa watermark.
   - **RedNote** `xhslink.com/o/44jNwnYztNq`: diarahkan ke `/login`, jadi note itu butuh login. Sekarang muncul pesan "upload file". Sebelumnya fallback og malah ngambil logo 小红书 sebagai foto; udah di-fix.
   - **Kesimpulan:** RedNote dihapus dari sumber link (D-022). Klip dari RedNote cuma bisa masuk lewat upload.
2. **Number card** "Number X" (D-021) belum diimplementasi. Rencananya komponen Remotion: angka chrome di background gelap berpartikel, terus gambar subjek dalam frame menyala.
3. TikTok bergantung ke tiktokio.com. Kalau situs itu mati, pilihannya upload manual atau port downloader scrapr yang lain (snaptik, ssstik, savetik).
4. Minor yang ditunda dari 2 review:
   - **Link & brief:**
     - URL yang nempel langsung ke huruf CJK tanpa spasi ikut kebawa.
     - `/files` baca seluruh file ke RAM.
     - `links.json` format lama per shot diabaikan tanpa log.
   - **Fetch:**
     - Frame cuma di-sample dari 60 detik pertama video.
     - Mode nyambung (`_continuous`) belum ngasih peringatan skor rendah.
   - **TikTok:** parser tiktokio masih rapuh (urutan atribut, class tambahan, div bersarang).
   - **Plan lama:** plan yang dibikin sebelum ada kelompok bikin `KeyError`. Harusnya muncul pesan "jalanin ulang --from plan".

## Delivery

- Di-merge ke `master` (2026-10-13, `3093e90`). Belum di-push. Backup hasil Fase 2 ada di `runs/_backup_fase2_i2xag/`.
- Next: number card (pembuka Fase 3), atau tes resolver Douyin/RedNote pakai link beneran.

---

# Handoff — Fase 3A (number card, subject card, caption per kata)

- **Updated:** 2026-10-13 16:00 WIB, Claude Code (Opus 5.5)
- **Goal & scope:** [spec 3A](superpowers/specs/2026-10-13-fase3a-countdown-captions-design.md), [plan](superpowers/plans/2026-10-13-fase3a-countdown-captions.md). Fase 3 dipecah jadi 3: 3A (countdown + caption), 3B (audio), 3C (overlay + CTA).
- **Workspace:** `master` (merge `4f32ba1`). Belum di-push.

## Selesai

- **Countdown:**
  - `mayzfact/countdown.py`: parse "Number five, horseshoe crab.", termasuk em dash dan angka 1–99. Beat countdown nggak dipotong jadi beberapa shot.
  - Timeline nulis `countdown` (number card + subject card) dan `captions` (1 kata per tampilan, warna putih/cyan/hijau/kuning).
- **Remotion:**
  - `NumberCard`: angka chrome Anton di background partikel.
  - `SubjectCard`: klip kelompok dalam frame menyala + label.
  - `Captions`: posisi 75%, shadow tebal, animasi masuk blur horizontal 3 frame (ngikutin source frame per frame).
  - Shot yang ketutup card nggak dirender, biar nggak tembus.
- **Final review Opus:** 2 Important udah di-fix (em dash, klip card lebih pendek di run lama).
- **Review Akmal di Studio (2026-10-13):** oke, setelah 3 revisi: caption shadow + animasi, caption turun, video tembus di belakang card. Redesain card ala source (plasma biru) ditolak, desain awal dipertahankan.

## Masalah terbuka

1. **Font Anton** di-load dari Google Fonts, jadi pas render butuh internet.
2. **Minor yang ditunda:**
   - kata pendek di nama subjek ikut berwarna
   - card bisa kedip 1 frame kalau alignment aneh
   - caption overlap 1 frame kalau 2 kata mulai di frame yang sama
   - partikel nggak muter balik di card yang panjang
   - angka 2 digit bisa kelebaran pas animasi masuk

## Delivery

- Next: 3B audio. SFX dari myinstants.com (pilihan Akmal).

---

# Handoff — Fase 3B (BGM + SFX + pembuka)

- **Updated:** 2026-10-13 23:05 WIB, Claude Code (Opus 5.5)
- **Goal & scope:** [spec 3B](superpowers/specs/2026-10-13-fase3b-audio-design.md), [plan](superpowers/plans/2026-10-13-fase3b-audio.md).
- **Workspace:** `master` (merge `528da5c`). Belum di-push.

## Selesai

- **BGM:**
  - File-nya di `assets/bgm/<mood>.mp3`. Daftar mood: mystery, suspense, dark, epic, space, tech, nature, playful, funny, inspiring, sad, energetic.
  - Gemini milih mood sesuai naskah. Kalau cuma ada 1 file, langsung dipakai.
  - Pilihannya disimpen di `runs/<id>/audio.json`. Kalau mau ganti, edit file itu terus jalanin `--from timeline`.
  - Volume 0.12, fade out 1 detik di akhir.
- **SFX:**
  - `assets/sfx/sfx.json` (pilihan Akmal dari myinstants): hook `awkward-moment.mp3`, number `quick-ting.mp3`, subject `pop_7e9Is8L.mp3`.
  - Nggak ada SFX di pergantian shot.
  - File audio di-gitignore. Yang di-commit cuma `sfx.json`.
- **Pembuka:** efek "masuk" dari transisi antar scene di source. Gambar mulai putih dengan blur vertikal, cepat tajam, terus terangnya pudar. Durasi 7 frame, barengan SFX hook.
- **Final review Opus:** 2 Important udah di-fix.
  - myinstants yang lambat bikin pipeline nunggu lama. Sekarang ada timeout 10 detik, dan kalau gagal langsung berhenti.
  - Error di audio bikin timeline crash. Sekarang timeline tetap jadi tanpa audio.
- **Review Akmal di Studio (2026-10-13):** oke, setelah beberapa revisi:
  - SFX diganti pakai pilihan Akmal.
  - Pembuka diulang 3 kali sampai sama kayak source: white flash → cover + zoom → whip flash.
  - Kedip hitam di frame 7 di-fix. Penyebabnya struktur elemen intro berubah di tengah video.

## Masalah terbuka

1. **Minor yang ditunda:**
   - belum ada cara buat maksa "tanpa BGM" per run
   - file lama di `runs/<id>/audio/` nggak dibersihin
   - nama BGM case-sensitive
2. **myinstants:** download SFX tergantung situs pihak ketiga.

## Delivery

- Next: 3C overlay (panah, lingkaran, emoji) + CTA subscribe.
