# Handoff — Format FaktaCuil (D-051)

- **Updated:** 2026-11-10 malam, Claude Code. **Branch:** `fase-faktacuil-format` (worktree `mayzfact-automation-wt/faktacuil-format`), belum di-merge dan belum di-push.
- **Status:** plan Task 1–12 selesai dan ter-commit (1 golden top3 `160964e`, 2 voice-sample `fd3b647`, 3 schema `21acd45`, 4 detektor CTA `620d9e3`, 5 aturan naskah `d456141`, 6 settings per format `1043c0c`, 7 plan `6b675e3`, 8 scene CTA `9a64a09`, 9 timeline `7d62ed8`, 10 BGM lokal `dfc295b`, 11 caption Fredoka `7165031`, 12 upload/slot `5ff9819`). Task 13 (skill `bikin-faktacuil`, `AGENTS.md`, `bikin-short`) dan Task 14 (D-051, HANDOFF ini, update spec + plan) baru ditulis, belum di-commit. Review code oleh reviewer sedang jalan.
- **Fix review (T13):** kata "like" di beat jawaban yang nempel ke blok CTA sekarang ditolak `check-script` (`Beat N uses 'like' outside the CTA`); `check-script` pakai `settings_for_mode` (rentang kata sama kayak pipeline); upload top3 nolak `language: "id"`; keyword berpunctuation (`madu?`) tetap kuning; hint login token FaktaCuil nyebut `--channel faktacuil`.
- **Hasil terakhir:** `uv run pytest -q` setelah Task 12: **794 passed, 3 skipped, 4 deselected, 0 failed** (`npm ci` sudah jalan di worktree, jadi test node ikut lolos). `npx tsc --noEmit -p .` bersih. `uvx ruff check --select F,I` bersih di file yang diubah. Golden top3 hijau di tiap task.
- **Dibangun:** `narration_mode: "faktacuil"` + `Beat.keyword`; aturan naskah F1–F11 di `check-script`; detektor CTA like Indonesia; scene CTA like + transform; timeline tanpa panah/emoji/card/intro/flash dengan `captionStyle: "faktacuil"`; caption Fredoka pop di Remotion; BGM 1 lagu lokal; voice Eric default + VoiceStudio opsional; shot maks 2,0 detik; upload ke channel FaktaCuil lewat token kedua dengan cek akun; slot 12.00/18.00 WIB maks 2 per hari. Angka: `FAKTACUIL_RAW_WPS = 2.27`, rentang kata 50–74 (target 62) di speed 1.1.
- **Belum dites:**
  - TTS beneran untuk naskah FaktaCuil utuh (baru sampel 40 kata Eric); bagaimana ElevenLabs membaca "like" dan "like-mu".
  - Render beneran FaktaCuil dari awal sampai `final.mp4`. Caption Fredoka baru di-still di latar hitam (outline hitam tidak terlihat); lebar kata terpanjang ±830 dari 960 px.
  - `login youtube --channel faktacuil` dan upload ke YouTube beneran (semua test pakai fake; respons `channels().list` asli belum pernah dilihat).
  - VoiceStudio bahasa Indonesia: profil belum ada, jadi jalur `faktacuil_tts_provider = "voicestudio"` baru dites dengan fake.
  - Lagu: file "Welcome to Bullworth" belum ada di `assets/channels/faktacuil/bgm/` (lead/Akmal yang menaruh), jadi BGM sementara `main.mp3`. Rawan Content ID.
- **Langkah Akmal setelah merge:**
  1. Taruh lagu pilihan di `assets/channels/faktacuil/bgm/` (folder lokal, tidak ke-commit).
  2. `uv run mayzfact login youtube --channel faktacuil`, pilih akun channel FaktaCuil di browser, lalu catat judul + ID channel (`UC...`) yang di-print.
  3. Isi `Settings.faktacuil_youtube_channel_id` dengan ID itu (di `mayzfact/config.py`). Tanpa ini upload FaktaCuil sengaja ditolak.
  4. Opsional, kalau mau VoiceStudio: isi `faktacuil_tts_provider`, `faktacuil_voicestudio_voice` (profil bahasa Indonesia), `faktacuil_voicestudio_instruct` di `settings.local.json`.
  5. Video pertama: minta agent pakai skill `bikin-faktacuil`.
- **Masalah terbuka:**
  - Run FaktaCuil baru menjalankan step `source` sebelum naskah ada, jadi memakai `hook_seconds` 10 dan men-download `source.mp4` + frame `seg_*` yang tidak dipakai. Belum diperbaiki (dicatat lead).
  - ~~Hint login `youtube.service` tanpa `--channel`~~: beres di fix review T13 (`service(token, channel="faktacuil")` nyebut `--channel faktacuil`).
  - 1,15 yang di-set eksplisit sebagai `video_speed` MayzFact voicestudio ikut turun ke 1,1 untuk FaktaCuil ElevenLabs (tidak bisa dibedakan dari auto-bump).
  - Beat jawaban yang nempel ke CTA dan punya "like" + `transform_word` sekaligus (contoh "warnanya berubah, rasanya like permen." dengan `transform_word` "berubah") masih lolos `check-script` (`mayzfact/faktacuil.py:122-124`, `has_trigger`). Saran: trigger transform cuma dihitung kalau beat-nya juga pola gimmick (diakhiri `?` dan ada `jadi <noun>`).
  - `FAKTACUIL_RAW_WPS` dari satu sampel; kalibrasi ulang kalau naskah asli jauh beda tempo.
- **Pertanyaan spec yang belum dijawab Akmal (pakai default):** Q2 `video_speed` khusus FaktaCuil (tetap 1.1), Q3 source listicle (boleh 1 item), Q5 TikTok (tidak dibuat), Q7 SFX click CTA (sama). Q1, Q4, Q8 sudah dijawab; Q6 menunggu langkah 3 di atas.
- **Spec/plan:** `docs/superpowers/specs/2026-11-10-faktacuil-format-design.md` (bagian 13 = deviasi), `docs/superpowers/plans/2026-11-10-faktacuil-format.md`.

# Handoff — Honey illustration + guard objek CTA (D-049)

- Desain bounded disetujui Akmal: honey harus ilustrasi, bukan teks; guard berlaku untuk naskah baru. Root cause: script memilih word dan renderer menjadikan tema tak dikenal fallback ke kartu kata.
- Schema menambah honey; validator pra-TTS menolak word dan mencocokkan objek pertanyaan transformasi dengan tema. Legacy word tetap terbaca. Renderer memakai switch exhaustive dan error pada tema tak dikenal. Skill penulisan repo diperbarui supaya objek belum didukung harus dibuat ilustrasinya sebelum suara.
- Honey SVG memakai dipper, stream, drops, jar kaca, riak deterministik; like/subscribe/comment tidak berubah. Strict RED→GREEN guard, schema honey, object mismatch serta renderer honey/unknown theme dijalankan. Full offline suite: 671 passed, 1 skipped, 4 deselected. Node SSR 8 kasus dan TypeScript dilaporkan subagent; parent mengulang lewat launcher native sebelum menerima fixture.
- Fixture produksi terisolasi `out/honey-cta-fixture/` hanya mengubah theme pada salinan timeline. Transform frame1034–1069, 1.2detik. Hash sumber tersimpan di verification.json; belum berarti produksi sudah dipromosikan atau render penuh selesai. Launcher Git Bash background node/npx memunculkan `stdin is not a tty`; gunakan Python subprocess dengan node.exe native dan CREATE_NO_WINDOW.
- Final guard menolak instruksi comment dan quoted text sebagai dasar objek; RED 9failed/15passed →24passed. Review independen ulang lolos, enam repro langsung juga lolos. Full suite final: **689 passed, 1 skipped, 4 deselected**, check-script produksi 131kata lolos. Hasil ini menggantikan hitungan tes awal di atas.
- Promosi metadata sudah dijalankan: theme saja word→honey pada script/plan/timeline. Hash voice.wav, voice.mp3, tts.json, links.json, clips.json identik; seluruh timestamp/cue/stage/shot tidak berubah. Backup: `D:/akmal/_notes/runs/pG-Y-ICCAXQ/backups/pre-honey-20261104-223340`. Audit `SEMUA OK`, check-script 131kata lolos. Fixture native sukses: TypeScript + 8 node cases; H.264 1080×1920, 1.216detik. Contact sheet diperiksa: dipper/aliran/jar terlihat besar, bukan kartu HONEY; caption terpisah. Preview penuh belum dirender ulang pada saat catatan ini. Output fixture tidak ikut Git.

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

- **Mode `CLIP_SOURCE=manual`** (default): `source → script → tts → plan → fetch → timeline → (Studio) → render`. Mode `auto` (Fase 2) tetap ada *(dihapus di D-031)*.
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
  - (Diubah D-028:) mood dipilih agent pas nulis naskah, field `bgm` di `script.json`. Kalau mau ganti, edit field itu terus jalanin `--from timeline`. `runs/<id>/audio.json` cuma dipakai naskah lama yang belum punya field `bgm`.
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

---

# Handoff — Fase 3C-1 (panah + lingkaran, timing suara)

- **Updated:** 2026-10-14, Claude Code (Opus 5.5)
- **Goal & scope:** [spec 3C-1](superpowers/specs/2026-10-13-fase3c1-arrows-design.md) + revisi D-023, [plan](superpowers/plans/2026-10-13-fase3c1-arrows.md).

## Selesai

- **Model ML di project.** Folder `models/` (di-gitignore, `MODELS_DIR`) isinya SigLIP (778 MB, dipindah dari C:) sama OWLv2 `google/owlv2-base-patch16-ensemble` revisi `cfd3195b` (621 MB). Dua-duanya bisa jalan offline.
- **Deteksi subjek per shot.** `mayzfact/detect.py` + `overlay.py`:
  - Frame dicek tiap 1 detik. Query-nya nama subjek, atau 2 kata pertama keyword kalau shot-nya nggak punya subjek.
  - Kotak hasil deteksi diubah ke koordinat layar 1080×1920, ngikutin layout full/blur.
  - Hasilnya di-cache di `runs/<id>/overlays.json`. Kecepatan ±3,8 detik per frame di CPU, jadi ±3 menit per video kalau belum ke-cache.
- **Panah/lingkaran:**
  - Muncul 6 frame setelah shot mulai, barengan `quick-ting` (volume 0,35), dan selesai fade 0,5 detik sebelum ganti klip.
  - Panah nyapu 1× setengah putaran (kanan → atas → kiri) sambil nunjuk subjek.
  - Tiap overlay ke-5 jadi lingkaran.
  - Warna gantian merah/kuning.
- **Timing ikut suara asli.** `voice_onset.py` geser awal kata ke energi `voice.mp3`, karena alignment ElevenLabs kecepetan 0,1–0,9 detik di awal kalimat. Efeknya:
  - Caption kata pertama nggak kecepetan lagi.
  - Angka countdown melesat masuk pas "Number" kedengeran, barengan puncak `whoosh-clean.mp3`.
  - Subject card mulai pas nama subjek disebut.
- **Review Akmal di Studio (2026-10-13/14):** oke, setelah beberapa revisi:
  - Durasi panah/lingkaran.
  - Gerak panah: sempat muter terus, akhirnya jadi 1 sapuan.
  - Volume quick-ting.
  - Panah hook sempat nunjuk menara. Penyebabnya query kepanjangan.
- **Final review Opus:** 1 Important udah di-fix. Sebelumnya, kalau 1 klip error, hasil deteksi klip lain ikut hilang dan deteksinya keulang terus. Sekarang cache ditulis per klip, dan klip yang error dilewat.
- **Workspace:** `master` (merge `39bb668`). Belum di-push.

## Masalah terbuka

1. **D-023 #4:** panah/lingkaran harusnya dipicu script (misalnya "look at this"), bukan muncul di tiap shot. Ini butuh perubahan logic script, jadi dikerjain nanti. *(Udah dikerjain di 3C-2, lihat D-024.)*
2. **Minor yang ditunda:**
   - angka bisa nggak tampil kalau `numberAt` ≥ durasi number card (kasus clamp yang jarang)
   - snap awal kata bisa telat 1–3 frame di konsonan
   - overlay masih tajam di 1 frame terakhir intro
   - label error `extract_frame` masih "hook"
   - potong 2 kata keyword bisa jadi "a giant"
   - frame `runs/<id>/overlay/*.jpg` nggak dibersihin
3. **Cache deteksi:** `overlays.json` di run i2xag dibikin sebelum cache key ikut `fg_min_ratio`, jadi `--from timeline` berikutnya bakal deteksi ulang sekali (±3 menit).

## Delivery

- Next: 3C-2, yaitu emoji + CTA subscribe. Bisa dibahas bareng D-023 #4.

---

# Handoff — Fase 3C-2 (emoji animasi, CTA like/subscribe, panah dipicu naskah)

- **Updated:** 2026-10-14, Claude Code (Opus 5.5)
- **Goal & scope:** [spec 3C-2](superpowers/specs/2026-10-14-fase3c2-emoji-cta-design.md), [plan](superpowers/plans/2026-10-14-fase3c2-emoji-cta.md), keputusan D-024.

## Selesai

- **Tanda per beat** (`point`, `emoji`, `emoji_word`):
  - Naskah baru dapat tanda dari prompt rewrite (`rewrite.md` + daftar emoji yang boleh).
  - Naskah lama ditandain Gemini tanpa ganti suara (`mayzfact/marks.py`, prompt `mark_beats.md`). Hasilnya di-cache di `runs/<id>/annotations.json` dengan key hash teks naskah.
  - Kalau Gemini gagal, semua beat jadi tanpa tanda dan hasilnya nggak di-cache.
- **Emoji animasi Noto (Lottie, CC BY 4.0):**
  - `mayzfact/emoji.py` download 28 emoji yang boleh ke `assets/emoji/` (di-gitignore), terus di-copy ke `runs/<id>/emoji/`.
  - Tampil di atas caption (box 370px). Pop masuk barengan `pop_7e9Is8L.mp3`, fade 6 frame.
  - Timing-nya lihat D-024 #3.
- **CTA like/subscribe** (`remotion/src/Cta.tsx`) ngikutin source i2xag frame per frame. Klik pakai `mouse-click-by-ek6_VR0O6PL.mp3`.
- **Panah/lingkaran cuma di beat `point`.** OWLv2 juga cuma jalan di klip yang nutup beat itu. Ini nutup D-023 #4.
- **Review Akmal:** Studio oke, `final.mp4` i2xag oke (2026-10-14).
- **Final review Opus:** semua temuan udah di-fix.
  - 1 Critical: tanda dari prompt rewrite kebuang di `normalize_script`.
  - 1 Important: "like" yang artinya "mirip" ikut dianggap CTA.
  - 6 Minor: like dobel, CTA kepotong di akhir video, cache annotations nggak dibersihin, `emoji_word` di kata ber-hyphen, `overlays.json` ngebuang hasil lama, download emoji lama kalau offline.
- **Workspace:** `master` (merge `8974d33`). Belum di-push.

## Verifikasi

- 361 test lolos, render test lolos, `tsc` bersih.
- E2E i2xag (naskah lama, jadi lewat jalur Gemini):
  - Beat `point`: 0, 4, 7, 9, 14. Hasilnya 5 panah/lingkaran.
  - Emoji: 🍀 frame 257, 🤯 475, 🤨 866, 🦖 1158, 💀 1436.
  - CTA: like di frame 208, subscribe di frame 224.
- **Belum dites:** jalur naskah baru end-to-end (prompt rewrite → `script.json` → tanda). Ngetesnya butuh kredit ElevenLabs (`--new-voice`).

## Masalah terbuka

1. **Jalur naskah baru belum pernah jalan beneran.** Di video berikutnya, cek `script.json`: tiap beat harus punya `point`/`emoji`, dan minimal ada beberapa yang keisi.
2. **Kalau `deps.marks` error** (bukan karena Gemini gagal), panah balik muncul di semua shot. Kasusnya jarang, misalnya error disk.
3. **Minor 3C-1 yang ditunda** masih ada (lihat daftar di Handoff 3C-1).

## Delivery

- Next: Fase 4 (otomatis + upload).

---

# Handoff — Fase 4 (versi harness AI agent)

- **Updated:** 2026-10-14, Claude Code (Opus 5.5)
- **Goal & scope:** D-025. Project dipakai lewat harness AI agent (Claude Code, Codex, OpenCode, Antigravity), bukan lewat cron.

## Selesai

- `AGENTS.md`: aturan main buat semua agent, mencakup keamanan, biaya, review Studio, laporan bug visual, git, dan gotcha Windows.
- `CLAUDE.md`: import `AGENTS.md`, plus catatan soal lokasi skill.
- `.agents/skills/bikin-short/SKILL.md`: alur 1 video dari source sampai `upload.md`, dengan checkpoint buat Akmal.
- `README.md`: nambah bagian review di Studio, aset, dan cara pakai bareng AI agent.

## Masalah terbuka

1. Belum dites di Codex, OpenCode, maupun Antigravity. Lokasi file (`AGENTS.md`, `.agents/skills/`) diambil dari dokumentasi masing-masing tool per 2026-10-14.
2. Skill `bikin-short` belum pernah dipakai buat bikin video beneran. Video berikutnya sekalian jadi tes jalur naskah baru (lihat Handoff 3C-2).

## Delivery

- Next: bikin 1 video baru pakai skill `bikin-short`.

---

# Handoff — Brief per shot + video NSua7RPoFJg

- **Updated:** 2026-10-15, Claude Code (Opus 5.5)
- **Goal & scope:** D-026. Dikerjain sebagian lewat harness lain (14 Okt sore–malam), dicatat di sini.

## Selesai

- **Brief:** video source tampil dan bisa di-seek (`f34ef9c`), input link per shot (`340ec66`), Mulai/Selesai detik (`1812d15`, `a650369`), UI baru gaya bento + layout HP (`3d15904`, `ea854a2`, `e20c6ec`, `9bc3cf2`), kebuka ke LAN (`21937fe`, `9bc3cf2`), fallback copy di HP non-HTTPS (`8655d35`).
- **Plan:** frame source per kelompok dicari urut card countdown (`a6a3b52`). Sebelumnya teaser "Number one…" bikin kelompok lain nggak dapat frame.
- **Fetch:** shot berurutan dengan link sama videonya nyambung (`c471b0d`).
- **Naskah:** minimal 2 beat penjelasan per item countdown (`ecf54d5`).
- **Windows:** log `hook_queries` tanpa karakter non-ASCII (`c68af19`).
- **Video NSua7RPoFJg:** jalur naskah baru jalan beneran (tanda `point`/`emoji` dari prompt rewrite kebaca). Udah sampai `final.mp4` (render 14 Okt 21:36).
- 378 test lolos.

## Masalah terbuka

1. NSua7RPoFJg belum punya `upload.md` (langkah 6 skill `bikin-short`), dan belum jelas Akmal udah oke final-nya atau belum.
2. Brief kebuka ke LAN tanpa login (lihat D-026 #3).

## Delivery

- Next: cek final NSua7RPoFJg sama Akmal, terus bikin `upload.md`.

---

# Handoff — Upload terjadwal ke YouTube

- **Updated:** 2026-10-15, Claude Code (Opus 5.5)
- **Goal & scope:** D-027, [spec](superpowers/specs/2026-10-15-youtube-upload-design.md), [plan](superpowers/plans/2026-10-15-youtube-upload.md).

## Selesai

- `mayzfact/youtube.py`: login OAuth (token ke `.env`), validasi `upload.json`, hitung slot 04.00/21.00 WIB, upload resumable sebagai private + `publishAt`, `youtube.json` sebagai penanda udah ke-upload.
- CLI: `mayzfact login youtube`, `mayzfact next-slot`, `mayzfact upload <id> --at "YYYY-MM-DD HH:MM"`.
- Skill `bikin-short` langkah 6–8: metadata → konfirmasi jam ke Akmal → upload. `AGENTS.md` sama README ikut diupdate.
- Test pakai fake service, tanpa API beneran.
- Review Opus + security: 4 temuan di-fix (`7cbaef8`). 409 test lolos.
- **Workspace:** `master` (merge `e95dea9`). Belum di-push.

## Masalah terbuka

1. Belum dites beneran: login Google dan upload ke YouTube. Upload pertama Akmal jadi tesnya, cek di YouTube Studio videonya *Scheduled* di jam yang bener.
2. Slot yang dianggap kepake cuma dari `runs/*/youtube.json`. Video yang dijadwalin manual di YouTube Studio nggak keitung.

## Delivery

- Next: `mayzfact login youtube`, terus upload NSua7RPoFJg lewat skill `bikin-short` langkah 6–8.

---

# Handoff — Naskah ditulis agent, Gemini dicabut

- **Updated:** 2026-10-15, Claude Code (Fable 5.1)
- **Goal & scope:** D-028, [spec](superpowers/specs/2026-10-15-agent-script-design.md), [plan](superpowers/plans/2026-10-15-agent-script.md).

## Selesai

- Step `script` dihapus. `run` berhenti exit 3 "Naskah belum ada" sampai agent nulis `runs/<id>/script.json`; sebelum TTS naskahnya dicek (ada, valid, lolos aturan).
- `mayzfact check-script <id>`: aturan lama (kata, foto, countdown, overlap, emoji) + cek CTA (kata like/subscribe/comment dari source harus ada) + cek `bgm`.
- `script.json` nambah `bgm`, `hook_queries`, `queries_zh`. Step `plan` dan `audio` baca dari situ. Naskah lama tanpa field itu tetap jalan (tanpa BGM, keyword hook fallback transcript).
- Step `source` sekalian download `source.mp4` + frame hook ke `plan/`, biar agent bisa lihat pas nulis.
- Gemini dicabut: provider, 5 prompt, `hook_queries.py`, `annotations.json`, `google-genai`, env `GEMINI_*`. Mode auto keyword hook pakai transcript.
- Skill `bikin-short` langkah 1–4: source → tulis naskah (aturan lengkap + contoh) → review Akmal → suara.
- 399 test lolos, 1 skip (POSIX).

## Masalah terbuka

1. Belum dites beneran: agent nulis naskah end-to-end buat 1 video. Kandidat pertama: `4735ZE89GXQ` (naskah lama Gemini masih ada, suaranya udah dibikin; kalau mau ulang, hapus `script.json` + `voice.mp3`, dan itu makan kredit ElevenLabs lagi).
2. *(Udah dikerjain, lihat Handoff D-029.)*
3. Ada stash `wip ngrok allowlist from other harness` (perubahan `brief/server.py` dari harness lain) yang belum di-review.

## Delivery

- Next: plan + kerjain spec brief, terus tes 1 video baru dari awal pakai skill `bikin-short`.

---

# Handoff — Revisi brief (D-029)

- **Updated:** 2026-10-15, Claude Code (Fable 5.1)
- **Goal & scope:** D-029, [spec](superpowers/specs/2026-10-15-brief-revisi-design.md), [plan](superpowers/plans/2026-10-15-brief-revisi.md).

## Selesai

- Tombol waktu per shot muter `voice.mp3` (play/stop, berhenti di `end_s`). Disabled kalau suara belum ada.
- `mayzfact/brief/prefetch.py`: worker download di server brief, `prefetch.json`, badge status per shot yang di-poll bareng `/api/progress`. Pas server start, link yang belum `siap` di-enqueue ulang.
- `steps/plan.py`: `ref_frames` per shot (`plan/shot_NN_K.jpg`), fallback posisi proporsional. `group.ref_frames` dihapus.
- `mayzfact brief` nolak jalan kalau ada shot tanpa frame, pesannya nyebut shot + `--from plan --no-render`.
- Review akhir (Opus): frame referensi cuma jadi target match buat shot hook (shot lain pakai keywords), autosave nggak ngulang link `siap`/`gagal` (Simpan = coba lagi), badge prefetch nempel ke link baru tanpa reload, worker nggak mati gara-gara log/`prefetch.json` error.
- 414 test lolos.

## Masalah terbuka

1. Belum dites beneran di browser: audio beat dan badge prefetch (dicek lewat HTML + test server aja).
2. Brief kebuka ke LAN tanpa login (D-026 #3) dan sekarang sekalian download apa pun yang diisi. Tetap jangan di WiFi publik.

## Delivery

- Next: lanjutin 4735ZE89GXQ (fetch → Studio → render → upload).

---

# Handoff — Hapus mode auto (D-031)

- **Updated:** 2026-10-17, Claude Code
- **Goal & scope:** D-031, [spec](superpowers/specs/2026-10-17-hapus-mode-auto-design.md), [plan](superpowers/plans/2026-10-17-hapus-mode-auto.md).

## Selesai

- Step `hook`/`clips`, Pexels/Pixabay, Playwright, `login <platform>`, `CLIP_SOURCE`, dan `fallback_query` dihapus. Bagian Fase 2 di atas sekarang cuma riwayat.
- Fungsi yang dipakai manual dipindah: `mayzfact/source_frames.py` (frame hook), `mayzfact/shots.py` (`split_shots`, `beat_subjects`), `normalize_local` ke `steps/fetch.py`.
- `.env` tinggal 4 rahasia; setting lain jadi default di `mayzfact/config.py` (`min_duration_seconds` 32, voice ID `TX3LPaxmHKxFdv7VOQHJ`).

## Masalah terbuka

1. Sisa auto di disk tinggal `runs/i2xag_1OJfM/hook/` (11 MB) + `hook.json`; nggak dibaca kode lagi. `browser-profiles/` dan `cache/search|thumbs|media` udah nggak ada. Akmal yang mutusin hapus.
2. Sebelum 2026-12-31 voice Liam dimatiin ElevenLabs (D-009): ganti `elevenlabs_voice_id` di `mayzfact/config.py`, bukan di `.env`.

---

# Handoff — Polish edit (D-038)

- **Updated:** 2026-10-23, Claude Code
- **Goal & scope:** D-038. Di-review Akmal lewat salinan run `NSua7RPoFJg` (Studio + preview), branch `fase-polish`.

## Selesai

- SFX transisi per jenis klip, 2 BGM + riser, blur teks RapidOCR, render 1,2x, box subjek ngikutin source, whip di hook, api biru di kartu angka + box foto.
- Remotion 4.0.538, `@remotion/media`.
- `assets/sfx/whoosh-clean.mp3` dihapus (nggak dipakai `sfx.json` lagi).

## Masalah terbuka

1. Run lama belum dicoba di-render ulang pakai komponen baru. Kalau perlu, jalanin `--from timeline` dulu biar SFX/BGM/blur-nya ikut aturan baru.
2. Ujung api di box foto agak terang di 2–3 frame terakhir (klip VFX-nya jadi putih), barengan efek keluar box. Akmal udah oke.
3. Sisa minor dari hapus-auto: default `retry_step` "hook", label error "[hook]", help `--port`, HANDOFF baris 140.

---

# Handoff — Revisi hook + kartu angka (D-039)

- **Updated:** 2026-10-23, Claude Code
- **Goal & scope:** D-039, dari review run `NkixGkCxOg8`. Branch `fase-revisi-hook`.

## Selesai

- Flash hook lebih tipis, +1 SFX hook acak, box foto +0,5 detik, "Number" barengan api + angka, render 1,1x.
- SFX transisi lebih pelan (klik 0,4, tambahan 0,3, punch 0,15, camera flash 0,4) dan SFX tumpukan disejajarin ke bunyi klik/flash. `dry-fart.mp3` dihapus.
- Fix render: output Remotion dulu sama kayak file sementara speed-up (`final.tmp.mp4`), ffmpeg nolak. Sekarang `final.raw.mp4`.

## Masalah terbuka

1. Run lama yang mau di-render ulang: `--from plan`, bukan `--from timeline` (D-039 no. 4).

---

# Handoff — Brief preview klip + SFX kustom (D-040)

- **Updated:** 2026-10-24, Claude Code
- **Goal & scope:** D-040. Branch `fase-brief-sfx`.

## Selesai

- SFX tambahan setelah hook 0,45 (punch 0,22).
- Brief: preview bagian klip yang dipakai, tombol "Pakai detik ini", pill SFX kustom per shot + detik-nya.
- SFX kustom masuk timeline dari `links.json` (volume 0,5).
- Fix fetch: shot setelah hook 1 video nyambung dengan link sama lanjut dari ujung hook.
- Dari final review: upload nggak ngapus SFX kustom lagi, SFX di detik 0 bunyi di preview, lanjutan yang lewat ujung video ditandain otomatis.
- Dicek di browser (server brief lokal, salinan run NSua): preview ngulang bagian yang dipakai, SFX bunyi di detiknya, Mulai + SFX kesimpen, keyboard (panah + fokus) jalan, lebar 390 px tanpa scroll samping. Timeline salinan NSua dapat 2 SFX kustom di frame yang bener.

## Masalah terbuka

1. Video Douyin yang codec-nya HEVC bisa nggak keputer di Chrome. Preview-nya nampilin pesan, fetch tetap jalan.
2. Suara SFX tambahan 0,45 belum didengar di render beneran.

---

# Handoff — Opsi VoiceStudio TTS (D-043)

- **Updated:** 2026-10-30.
- **Branch:** `fase-voicestudio-tts`; default repo ElevenLabs, override PC Akmal VoiceStudio/CosyVoice/Gen.
- **Desain:** `docs/superpowers/specs/2026-10-30-voicestudio-tts-design.md`.
- **Implementasi:** Pilihan provider + setting lokal tervalidasi; tidak ada fallback berbayar. Profil di-resolve unik; API MP3 + ASR word timestamps, mapping exact script, cache audio sebelum ASR, pending provider lain tidak ditimpa.
- **Pengaturan lokal:** `settings.local.json` gitignored; contoh tracked `settings.local.example.json`. Backend VoiceStudio harus hidup. Mengubah provider tidak mengubah voice run lama.
- **Uji nyata:** `Gen` ID `49a69f8b`, `run_tts` menghasilkan MP3 8,088 detik, 24 kata, 4 beat. Bukti + sampel: `cache/voicestudio-verification/`. ASR menulis `5` untuk `five`; regression test + mapping angka ekuivalen 0–10 ditambahkan, audio asli dipakai ulang.
- **Batasan:** English; timestamp karakter berbagi batas kata, bukan fonem. ASR yang mengganti/menghilangkan kata ditolak. Estimasi words/s ElevenLabs belum berlaku untuk CosyVoice. Kualitas narasi belum direview Akmal; tidak membuat/render/upload video baru.
- **Verifikasi kode:** parent menjalankan ulang 461 test (1 skipped, 3 deselected); Ruff F/I bersih. Edge case tanda baca terpisah dan transkripsi non-object dari HTTP/cache punya regression test.

# Handoff — Gen ekspresif + WAV native (D-044)

- **Scope disetujui:** hanya lima saran kualitas/intonasi; tidak mengganti model/reference, naskah, voice/video lama, atau upload.
- **Lokal aktif:** Gen/CosyVoice, arahan delivery ekspresif lewat `voicestudio_instruct`, `voicestudio_audio_format=wav`; default repo tetap ElevenLabs dan kompatibilitas MP3.
- **Native:** `voice.wav` byte asli dipertahankan untuk alignment, plan onset, timeline master. `voice.mp3` hanya brief/marker sukses. Metadata lama tetap MP3; native yang dipilih tapi hilang gagal keras. Pending beda format/provider/naskah tidak ditimpa; kegagalan ffmpeg bisa dilanjutkan tanpa sintesis ulang.
- **Uji nyata:** A/B 35 kata identik, Gen/seed 0/speed 1.0 sama; A kosong 12,427 detik, B arahan 16,165 detik. WAV PCM16 24 kHz mono; profil/reference Gen dan run lama hash-nya sama. File + provenance di `cache/quality-ab/Gen-v1/`.
- **Jalur renderer:** `run_tts` dari audio B cache menghasilkan WAV byte-identik + MP3 kompatibilitas; `run_timeline.audio=voice.wav`; Remotion benar-benar merender smoke 1,003 detik dengan audio AAC. Bukti `cache/quality-ab/Gen-v1/pipeline-check/verification.json`, artefak `out/quality-smoke/native-wav-1s.mp4`. Bukan rerender video penuh.
- **Regression parent:** 510 passed, 1 skipped, 3 deselected; Ruff F/I bersih. Intonasi subjektif belum dianggap lebih baik sampai Akmal menilai A/B.

# Handoff — Top 3 + CTA sebelum nomor satu (D-045)

- **Branch:** `fase-top3-cta`, dari baseline aktif `6cb523f`; commit lokal saja, belum push/merge.
- **Spec / plan:** `docs/superpowers/specs/2026-11-01-top3-cta-design.md`, `docs/superpowers/plans/2026-11-01-top3-cta.md`.
- **Naskah baru:** tulis `narration_mode: top3`; ambil peringkat asli source 3/2/1. CTA tantangan 1–2 beat langsung sebelum Number one, minimal dua beat penjelasan per item di luar CTA. Target final 30–40 detik, sasaran 80 kata, valid 76–84 pada speed 1.1x.
- **Kode:** schema legacy-safe, anggaran bersama CLI/pra-TTS, validasi subjek/ranking/CTA; like kondisional; timeline mengikuti urutan ucapan dan membatasi event sebelum nomor satu; plan tidak mencampur body/CTA ke hook dan tidak mewariskan subject ke CTA.
- **Durasi nyata:** pipeline melaporkan estimasi final dari metadata audio/speed; di luar target memberi peringatan dan mempertahankan audio. Tidak mengganti speed atau membayar TTS ulang otomatis. Anggaran kata belum membuktikan durasi final; ffprobe diperlukan saat render produksi berikutnya.
- **Operator PC:** `D:/akmal/_notes/tools/mayzfact_audit.py` disesuaikan ke mode dan helper repo, dengan regression terisolasi di `D:/akmal/_notes/tools/tests/test_top3_audit.py`; file operator ini berada di luar repo, tidak ikut commit/clone.
- **Batas verifikasi:** test fixture/CLI/pipeline lokal tanpa kredit API; tidak membuat atau meng-upload video produksi baru, tidak mengubah voice/run lama. Default ElevenLabs/voice/stability dan semua checkpoint tetap. Bukti test akhir dicatat pada laporan commit fase ini.
- **Verifikasi parent setelah review:** full suite 562 passed, 1 skipped, 3 deselected; audit operator terisolasi 7 passed; Ruff F/I dan diff-check bersih. CLI fixture valid 80 kata diterima dan CTA awal ditolak; parser source nyata memilih basilisk lizards/immortal jellyfish/tardigrades sebagai 3/2/1. Hash script/voice/tts/final/youtube run `j3uTtxM3vSQ` cocok dengan snapshot sebelum eksperimen suara.
- **Final review:** empat temuan Important direproduksi dan diperbaiki RED→GREEN: delimiter heading source memakai grammar bersama; validasi/timeline CTA memakai batas token per beat; frame isi dipetakan ke rentang peringkat asli, bukan alias subject/proposional source penuh; schema mode dicek saat resume sebelum output lama dihapus. Tidak ada temuan Minor yang ditunda. Helper operator juga diuji dengan source validator/schema Git versi sebelum Top 3 agar checkout branch lama tidak rusak; naskah Top 3 pada kode lama ditolak jelas, bukan diam-diam dianggap legacy.
- **Batas edit:** update opsional `AGENTS.md` tidak dilakukan karena izin tool timeout. Aturan baru lengkap berada di skill bikin-short dan D-045; file protected tetap utuh.

# Handoff — Revisi CTA playful Top 3 (D-046)

- **Branch/base:** `fase-top3-cta`, `ce609fe`; perubahan dibiarkan uncommitted untuk parent review. D-046 menggantikan batas/style CTA dan anggaran total D-045 saja.
- **Hasil:** contoh empat beat persis yang disetujui diterima (21 kata). Satu detektor blok bersama mencakup transisi/pertanyaan tanpa trigger; CTA 1–4 beat, ≤10 kata/beat, subject kosong/point=false, langsung sebelum Number one. Plan tidak mewariskan subject/rank/hook item dua ke pertanyaan. Timeline mengikuti kata like lalu subscribe, bukan pertanyaan; tidak ada fitur/animasi transformasi tombol.
- **Budget:** base `(80,76,84)` pada 1.1x + `max(0, actual CTA words - 10)`, contoh `(91,87,95)`. Baseline body dan source legacy tidak dilonggarkan. Kata CTA aktual tidak ikut diskala ulang. CTA ekstra boleh melewati target baseline final 30–40 detik: parent melaporkan audio nyata / speed setelah TTS yang diizinkan, tanpa mengganti speed/provider.
- **Verifikasi:** RED invitational tapping `1 failed, 9 passed` → `10 passed`; RED shared detector `4 failed` → `14 passed` bersama CTA; RED struktur/marks `9 failed, 10 passed` → `66 passed` bersama script/CTA; RED budget `7 failed, 19 passed` → `73 passed` bersama script/CTA. Integrasi CLI/plan/timeline + audit operator pada root sementara `81 passed`. Full offline suite `600 passed, 1 skipped, 3 deselected in 58.96s`; audit operator terpisah `12 passed in 1.08s`; Ruff F/I dan `git diff --check` lolos (Git hanya memberi notice konversi LF→CRLF). Test render/ML asli sengaja tidak dijalankan; review inline tanpa subagent, parent tetap reviewer independen sebelum commit.
- **Operator di luar Git:** `D:/akmal/_notes/tools/mayzfact_audit.py` tidak perlu diubah karena sudah memakai detector/budget bersama; `D:/akmal/_notes/tools/tests/test_top3_audit.py` ditambah kasus CTA baru/budget/marks/explanation. Fallback pre-Top3 memakai kode Git lama tetap lolos.
- **Batas deteksi:** rentang antar-anchor struktural, bukan penilaian makna. Body ber-annotasi di tengah CTA ditolak lewat subject/point/cap; prose tanpa anotasi di antara anchor dianggap bagian kandidat CTA dan masih perlu review manusia. Gaya transisi/tema/subscribe kondisional ada di skill, tidak dikunci semantic regex.
- **Scope produksi:** tidak generate TTS, render, upload, push, commit, start brief, atau mengubah runs/audio/settings/provider. Parent berikutnya review diff, lalu backup/update script Q0zEnOUT3mM, revoice dengan paid audio lama tetap disimpan, bangun plan dan restart brief. Durasi/audio baru belum diukur; tidak ada klaim fitur platform bekerja nyata.

# Handoff — ElevenLabs calm delivery (D-047)

- **Branch/base:** `fase-top3-cta`, `61ae374`; semua perubahan uncommitted. Scope hanya delivery yang disetujui: default calm + stability 0.5; voice/model/wording/speed tetap.
- **Hasil:** tag disisipkan satu kali pada request, tidak pada script/hash/caption. run_tts menyimpan raw alignment + paid audio sebelum mapping; exact prefix `[calm] ` atau `[calm]` dihapus dengan slicing ketiga array yang sama. Alignment tanpa tag didukung jika persis teks asli. Tidak retiming/interpolasi; mismatch/panjang array invalid gagal setelah save dan dapat diulang tanpa tagihan.
- **Cache/provenance:** identity memasukkan `delivery_tag` hanya saat dipakai, menolak pending legacy/untagged/tag berbeda untuk calm. Metadata sukses mencatat tag/raw alignment; incoming tetap raw agar retry tidak memotong dua kali. Jalur fake/no-tag tetap kompatibel dan audio historis dilindungi.
- **TDD/verifikasi:** default RED 1→32 config passed; provider prefix RED 1→40 focused passed; integrasi alignment RED 1→40 passed; separator RED 1→44 passed; mismatch RED 7→51 passed; identity RED 2→46 passed; legacy pending RED 1→51 passed; override RED 3→35 config passed; validation RED 9→106 focused passed; factory RED 2→**160 focused passed in 7.84s**. Full offline **639 passed, 1 skipped, 3 deselected in 57.94s**; Ruff F/I bersih, diff check lolos. Tidak menjalankan API/render/ML asli.
- **Dokumen:** spec/plan `2026-11-02-elevenlabs-calm*`, D-047 dan skill authoring langkah 4 diperbarui. Review inline; parent tetap reviewer sebelum commit.
- **Produksi belum disentuh:** tidak menulis `settings.local.json`, runs, script/audio, render, brief, commit/push. Parent memegang backup produksi terverifikasi `D:/akmal/_notes/runs/Q0zEnOUT3mM/backups/pre-calm-20261102-173209`, setting lokal dan revoice/plan/brief. Jalankan produksi melalui Settings/real_deps; constructor ElevenLabsTTS langsung tetap default no-tag untuk kompatibilitas pemanggil lama. Durasi/kualitas full audio baru belum diuji.

# Handoff — Scene CTA opt-in (D-048)

- **Branch:** `fase-top3-cta`; tetap uncommitted, tanpa checkout/commit/push. Spec/plan `2026-11-02-cta-scene*`; authoring skill diperbarui untuk naskah Top3 baru. Parent memegang audio Alex dan run produksi, subagent tidak menyentuhnya.
- **Parent:** tambahkan `"cta_scene":{"theme":"volcano","transform_word":"turn","comment_text":"ERUPTED"}` ke root script lalu rebuild plan. Ini metadata visual saja, hash teks tetap. Jangan ubah beat/voice/link non-CTA. AUTO CTA tidak butuh link baru, frame referensi atau upload; brief/API/prefetch/completeness sudah diuji. Buka brief produksi di parent, bukan melalui subagent ini.
- **Hasil:** stage sepanjang blok detector bersama, cue kata nyata, fallback struktur dilabeli, berhenti sebelum satu; caption di bawah, tanpa panah/emoji/CTA legacy ganda. SVG volcano animasi frame-based; tema word+label mendukung video lain. Background hanya video lokal sebelumnya, seed deterministik, offset lanjut dan loop; fallback warna bergerak jika belum ada video. Footage masa depan tidak dipakai. Non-CTA manual tetap jalur lama.
- **TDD:** schema RED KeyError→1 passed; plan RED set kosong→4 passed bersama legacy plan; manual/brief RED 2→43 passed; API/operator RED 2→6 passed; fetch RED 3→31 passed bersama fetch lama; timing RED 3→76 passed bersama timeline; detector/prefetch RED 2→64 passed (termasuk fix regression CLI NameError); operator overlap RED 1→18 CTA tests passed. SSR visual RED missing CtaScene→5 visual cases passed. Review inline, parent reviewer independen.
- **Artefak nyata:** `D:/akmal/mayzfact-automation/out/cta-scene-fixture/cta.mp4`, `contact-sheet.png`, `render-verification.json`, `verification.json`, `timeline.json`. H.264 1080×1920 30fps 5.533333 detik, tanpa audio (fixture synthetic berlabel, tidak memakai run/voice produksi). Sembilan frame diperiksa visual: like/morph/volcano/subscribe/comment/tail/one, caption terpisah dan tidak terpotong; background bergerak (mean pixel delta 0.2316108843537415). Output di-ignore, tidak distage.
- **Final verification:** full offline `657 passed, 1 skipped, 4 deselected in 64.70s`; real render integration `1 passed in 64.26s`; TypeScript `npx tsc --noEmit -p .`, lima node SSR visual cases, Ruff F/I dan `git diff --check` lolos. `git check-ignore out/cta-scene-fixture/cta.mp4` mengonfirmasi output fixture tidak masuk perubahan Git.
- **Helper luar Git:** `D:/akmal/_notes/tools/short_ops.py` memakai completeness plan bersama, menampilkan stage scene, mengecualikan reused dari overlap warning. Diuji via import pada temp root, tanpa memulai/mematikan server. Tidak ikut commit/clone.

## Koreksi preview CTA
- Repro produksi: like stage dari frame740 (awal CTA), padahal try mulai26.035detik; blur58px + brightness0.38 menutup footage. Test baru gagal persis: stage387 !=407 pada fixture dan blur58px melewati batas12px.
- Fix: like mulai kata try/tapping/hit yang benar-benar ada pada alignment, klik tetap kata like; lead-in tetap background/caption. Scene tidak harus memiliki stage selama lead-in. Background blur10px/brightness0.78/saturate0.95/scale1.06 dan vignette lebih ringan. Focused19passed + TypeScript lolos. Voice diperbaiki terpisah, hook harus byte-identik dan link manual tetap terlindungi.

## CTA motion — bounded revision
- Alex terakhir dipilih; tidak ada perubahan audio/timing/klip. RED markup `like must enter from invisible` berhasil mereproduksi kemunculan mendadak. Shared CtaMotion memberi entrance spring/fade/slide, exit shrink/fade, click ripple dan partikel deterministik. Subscribe punya huruf stagger/cursor/click delay visual dan confetti; comment diketik. Semua efek dibatasi durasi stage, tanpa SFX tambahan.
- Node markup memeriksa empat stage awal transparan/hold terbaca/akhir transparan, typewriter completion, ripple/confetti dan glass limits; TypeScript lolos. Spec+plan `docs/superpowers/specs/2026-11-02-cta-motion-design.md`. Full suite dan hasil render dilaporkan pada eksekusi parent.

# Handoff — Top3-only (D-050)

- **Updated:** 2026-11-10.
- **Branch:** `fase-top3-only`.
- **Goal & scope:** Spec `docs/superpowers/specs/2026-11-10-top3-only-design.md`, plan `docs/superpowers/plans/2026-11-10-top3-only.md`, keputusan D-050. Pipeline hanya mendukung format Top 3 (`narration_mode: "top3"`) dengan `cta_scene` wajib; mode source legacy dan varian CTA legacy dihapus.
- **Selesai:**
  - `Script`: `narration_mode` wajib literal `"top3"`, `cta_scene` wajib dengan tema ilustrasi (`volcano`, `unicorn`, `honey`, `puppy`, `lion`, `shark`). Tema `word` dan field `label` dihapus dari model.
  - Guard run lama: `load_script` menolak script format lama (`narration_mode` tidak ada/bukan `"top3"`, atau tanpa `cta_scene`) sebelum output resume dihapus. Lima run lama di disk (`4735ZE89GXQ`, `NSua7RPoFJg`, `i2xag_1OJfM`, `piD9Fjp-mG8`, `ydA5gOdKvfc`) aman dibiarkan.
  - Budget kata: `WORDS_PER_SECOND`, `WORD_TOLERANCE`, `target_duration`, `word_range`, serta config `target_duration_ratio`/`min_duration_seconds` dihapus. Budget selalu berbasis formula top3 (`narration_word_range`).
  - Plan: `run_plan` selalu ranked, `source_rank` selalu diisi, kelompok CTA otomatis diisi `cta_scene`.
  - Timeline & Remotion: overlay legacy `Cta` dan `timeline.cta` dihapus. `ShortVideo` hanya merender `CtaScene`. `Cta.tsx` hanya mengekspor `Thumb` dan `Cursor` untuk kebutuhan `CtaScene`. Click SFX dan sinkronisasi tabrakan emoji tetap aman dihitung via `_top3_cta`.
  - Node markup test di Remotion: 10 CTA visual cases passed tanpa tema `word`.
  - Review follow-up: scene CTA yang gagal terbentuk mematikan click SFX; run lama tanpa voice ditolak sebelum output dihapus; `cta_scene: null` dan root JSON non-object mendapat pesan error yang tepat.
- **Verifikasi:**
  - `uv run pytest -q`: 689 passed, 3 skipped, 4 deselected (termasuk 10 node SSR visual markup cases).
  - Ruff `uvx ruff check --select F,I`: bersih.
  - TypeScript `cd remotion && npx tsc --noEmit -p .`: bersih.
  - 10 CTA visual cases passed di Node (`node tests/cta-scene.cjs`).
  - Belum dites: render video penuh (`uv run pytest -m render` belum dijalanin karena berat, 5–8 menit).
- **Masalah terbuka:**
  - Spec R6: Jika ada `script.json` Top 3 di luar `runs/` (misalnya backup/mesin lain) yang masih memiliki field `"label": ""`, file tersebut akan ditolak oleh `extra="forbid"`. Solusinya cukup hapus key `label` dari file JSON tersebut (tidak mengubah hash suara).
